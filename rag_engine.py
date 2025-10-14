import os
import io
import pdfplumber
import docx2txt
from supabase import create_client
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import dropbox

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
DROPBOX_TOKEN = os.getenv("DROPBOX_ACCESS_TOKEN")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
dbx = dropbox.Dropbox(DROPBOX_TOKEN)
model = SentenceTransformer("all-MiniLM-L6-v2")

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
        return file_bytes.decode("utf-8")
    return ""

def fetch_dropbox_files(folder_path=""):
    result = dbx.files_list_folder(folder_path)
    files = []
    for entry in result.entries:
        if isinstance(entry, dropbox.files.FileMetadata):
            _, res = dbx.files_download(entry.path_lower)
            files.append((entry.name, res.content))
    return files

def index_documents():
    files = fetch_dropbox_files()
    for name, data in files:
        text = extract_text(data, name)
        if not text:
            continue
        chunks = [text[i:i+1000] for i in range(0, len(text), 1000)]
        for chunk in chunks:
            embedding = model.encode(chunk).tolist()
            supabase.table("documents").insert({
                "content": chunk,
                "embedding": embedding,
                "source": name
            }).execute()

def search_similar(query, top_k=5):
    query_vec = model.encode(query).tolist()
    response = supabase.rpc("match_documents", {
        "query_embedding": query_vec,
        "match_count": top_k
    }).execute()
    return response.data
