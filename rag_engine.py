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

    if not files:
        print(f"[{datetime.now().isoformat()}] No files found in Dropbox.")
        return
    
    for name, data in files:
        text = extract_text(data, name)
        if not text:
            continue
        hash_value = hashlib.sha256(text.encode()).hexdigest()
        existing = supabase.table("documents").select("id").eq("hash", hash_value).execute()

        if existing.data:
            print(f"[{datetime.now().isoformat()}] Skipping unchanged file: {name}")
            continue

        chunk_size = 1000
        overlap = 200
        chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size - overlap)]

        for chunk in chunks:
            embedding = model.encode(chunk).tolist()

            supabase.table("documents").insert({
                "content": chunk,
                "embedding": embedding,
                "source": name,
                "hash": hash_value,
                "modified": datetime.now().isoformat()
            }).execute()

        print(f"[{datetime.now().isoformat()}] Indexed file: {name} (hash={hash_value[:8]})")


def search_similar(query, top_k=5):
    query_vec = model.encode(query).tolist()

    response = supabase.rpc("match_documents", {
        "query_embedding": query_vec,
        "match_count": top_k
    }).execute()
    
    return response.data