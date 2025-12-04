import os
import io
import hashlib
import tempfile
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

_supabase = None
_model = None

_indexing_in_progress = False


def get_supabase():
    global _supabase
    if _supabase is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in environment")
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase


def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_dropbox_client():
    token = os.getenv("DROPBOX_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("DROPBOX_ACCESS_TOKEN must be set in environment")
    return dropbox.Dropbox(token)


def extract_text(file_bytes, filename):
    if filename.endswith(".pdf"):
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            return "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())
    elif filename.endswith(".docx"):
        try:
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmpf:
                tmp_path = tmpf.name
                tmpf.write(file_bytes)
            text = docx2txt.process(tmp_path)
            try:
                os.remove(tmp_path)
            except Exception:
                pass
            return text
        except Exception:
            return ""
    elif filename.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="ignore")
    return ""


def fetch_dropbox_files(folder_path=""):
    dbx = get_dropbox_client()
    files = []
    try:
        result = dbx.files_list_folder(folder_path)
    except Exception:
        return files

    while True:
        for entry in result.entries:
            if isinstance(entry, dropbox.files.FileMetadata):
                try:
                    _, res = dbx.files_download(entry.path_lower)
                    files.append((entry.path_lower, res.content))
                except Exception:
                    continue
        if result.has_more:
            result = dbx.files_list_folder_continue(result.cursor)
        else:
            break
    return files


def index_documents():
    global _indexing_in_progress
    _indexing_in_progress = True
    try:
        files = fetch_dropbox_files()
        current_time = datetime.now().isoformat()

        if not files:
            print(f"[{current_time}] No files found in Dropbox.")
            return

        dropbox_sources = [path for path, _ in files]

        db = get_supabase()
        db_sources_resp = db.table("documents").select("source").execute()
        db_sources = [r["source"] for r in (db_sources_resp.data or [])]

        removed = set(db_sources) - set(dropbox_sources)

        for path in removed:
            db.table("documents").delete().eq("source", path).execute()
            print(f"[{current_time}] Removed deleted file: {path}")

        for path, data in files:
            text = extract_text(data, path)
            if not text:
                continue

            hash_value = hashlib.sha256(text.encode()).hexdigest()
            existing = db.table("documents").select(
                "id").eq("file_hash", hash_value).execute()

            if existing.data and len(existing.data) > 0:
                print(f"[{current_time}] Skipping unchanged file: {path}")
                continue

            print(f"[{current_time}] Indexing new or changed file: {path}")
            db.table("documents").delete().eq("source", path).execute()

            chunk_size = 512
            overlap = 200
            chunks = [text[i:i + chunk_size]
                      for i in range(0, len(text), chunk_size - overlap)]

            model = get_model()
            for i, chunk in enumerate(chunks):
                chunk_hash = hashlib.sha256(
                    f"{hash_value}_{i}".encode()).hexdigest()
                embedding = model.encode(chunk).tolist()

                db.table("documents").upsert({
                    "content": chunk,
                    "embedding": embedding,
                    "source": path,
                    "chunk_hash": chunk_hash,
                    "file_hash": hash_value,
                    "modified": current_time
                }).execute()

            print(
                f"[{datetime.now().isoformat()}] Indexed file: {path} ({len(chunks)} chunks, hash={hash_value[:8]})")
    finally:
        _indexing_in_progress = False


def search_similar(query, top_k=5):
    if _indexing_in_progress:
        return []

    try:
        model = get_model()
        query_vec = model.encode(query).tolist()

        db = get_supabase()
        response = db.rpc("match_documents", {
            "query_embedding": query_vec,
            "match_count": top_k
        }).execute()

        return response.data or []
    except Exception:
        return []
