import os
import io
import hashlib
from datetime import datetime
import pdfplumber
import docx2txt
import dropbox
from supabase import create_client
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")

def get_dropbox_client():
    return dropbox.Dropbox(os.getenv("DROPBOX_ACCESS_TOKEN"));

def extract_text(file_bytes, filename):
    if filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif filename.endswith(".docx"):
        tmp = "/tmp/temp.docx"
        with open(tmp, "wb") as f:
            f.write(file_bytes)
        return docx2txt.process(tmp)
    elif filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    return ""


def fetch_dropbox_files(folder_path=""):
    dbx = get_dropbox_client()
    result = dbx.files_list_folder(folder_path)
    files = []

    for entry in result.entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            _, res = dbx.files_download(entry.path_lower)
            files.append((entry.name, res.content))
    return files


def index_documents():
    files = fetch_dropbox_files()
    current_time = datetime.now().isoformat()

    if not files:
        print(f"[{current_time}] No files found in Dropbox.")
        return

    dropbox_sources = [name for name, _ in files]

    db_sources_resp = supabase.table("documents").select("source").execute()
    db_sources = [r["source"] for r in db_sources_resp.data]

    removed = set(db_sources) - set(dropbox_sources)

    for name in removed:
        supabase.table("documents").delete().eq("source", name).execute()
        print(f"[{current_time}] Removed deleted file: {name}")

    for name, data in files:
        text = extract_text(data, name)
        if not text:
            continue

        hash_value = hashlib.sha256(text.encode()).hexdigest()
        existing = supabase.table("documents").select("id").eq("file_hash", hash_value).execute()

        if existing.data and len(existing.data) > 0:
            print(f"[{current_time}] Skipping unchanged file: {name}")
            continue

        print(f"[{current_time}] Indexing new or changed file: {name}")
        supabase.table("documents").delete().eq("source", name).execute()

        chunk_size = 1000
        overlap = 200
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]

        for i, chunk in enumerate(chunks):
            chunk_hash = hashlib.sha256(f"{hash_value}_{i}".encode()).hexdigest()
            embedding = model.encode(chunk).tolist()

            supabase.table("documents").upsert({
                "content": chunk,
                "embedding": embedding,
                "source": name,
                "hash": chunk_hash,
                "file_hash": hash_value,
                "modified": current_time
            }).execute()

        print(f"[{datetime.now().isoformat()}] Indexed file: {name} ({len(chunks)} chunks, hash={hash_value[:8]})")



def search_similar(query, top_k=5):
    query_vec = model.encode(query).tolist()

    response = supabase.rpc("match_documents", {
        "query_embedding": query_vec,
        "match_count": top_k
    }).execute()
    
    return response.data