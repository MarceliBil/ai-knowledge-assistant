# 🤖 AI Knowledge Agent

An intelligent company knowledge assistant built with **Streamlit**, **Claude (Anthropic)**, and **Supabase**.  
It indexes internal documents stored in **Dropbox**, converts them into embeddings for semantic search, and answers user questions based strictly on company knowledge.

---
<img width="1857" height="1198" alt="Zrzut ekranu (10)" src="https://github.com/user-attachments/assets/d878fba5-3ec9-4e52-845a-9d86e6b593a1" />



## 🧠 Overview

This project demonstrates a lightweight **Retrieval-Augmented Generation (RAG)** pipeline:

1. **Document ingestion:**  
   Text, PDF, and DOCX files are automatically fetched from a connected Dropbox folder.

2. **Embedding & storage:**  
   Each document is split into overlapping chunks, embedded locally using `all-MiniLM-L6-v2`, and stored in a Supabase table with the `pgvector` extension.

3. **Context-aware responses:**  
   When a user asks a question, the agent retrieves the most semantically relevant chunks from Supabase and passes them as context to **Claude Haiku 3.5** via the Anthropic API.

4. **Chat interface.**

---

## ⚙️ Features

- 🧩 **RAG engine:** combines local embeddings with Claude’s reasoning  
- ☁️ **Dropbox sync:** automatically reads all `.txt`, `.pdf`, and `.docx` files  
- 🧮 **Supabase vector store:** handles embeddings and semantic search  
- 🧠 **Claude-powered answers:** context-aware, strictly based on internal data  
- 🧱 **Deduplication:** file hashes prevent redundant reindexing  
- 🕒 **Auto-refresh:** Dropbox access token refreshed via OAuth flow  

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|-------------|
| Frontend | Streamlit |
| LLM | Claude Haiku 3.5 (Anthropic API) |
| Vector Store | Supabase + pgvector |
| Embeddings | SentenceTransformers (`all-MiniLM-L6-v2`) |
| File Source | Dropbox API |
| Language | Python 3.13.2 |


<br>

## 🚀 How to Run with Your Own API Keys

Follow these steps to set up and run the **AI Knowledge Agent** locally with full Dropbox, Supabase, and Claude integration.
<br><br>

### 1️⃣ Clone the repository

```bash
git clone https://github.com/MarceliBil/ai-knowledge-assistant.git
```
<br>

### 2️⃣ Create and activate a virtual environment

```bash
python -m venv venv
```
<br>

**mac/linux**
```bash
source venv/bin/activate
```

**windows**
```bash
venv\Scripts\activate
```
<br>

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```
<br>

### 4️⃣ Create your .env file

In the project root, create a file named `.env`.
We will add the corresponding API keys to these variables later.

```bash
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_publishable_key
DROPBOX_ACCESS_TOKEN=your_access_token
ANTHROPIC_API_KEY=your_anthropic_api_key
```
<br>

### 5️⃣ Create a Supabase project

1. Go to https://supabase.com → New Project

2. Copy your Project URL (`SUPABASE_URL`) and Publishable key (`SUPABASE_KEY`) - from the tab **API Keys**, not *Legacy API Keys*! - and paste them into the previously created `.env` file.
<br>

<br>

### 6️⃣ Initialize the Supabase table


Open the *SQL Editor* in Supabase and run:

```bash
create extension if not exists vector;

create table documents (
  id bigserial primary key,
  content text,
  embedding vector(384),
  source text,
  hash text unique,
  file_hash text,
  modified timestamp default now()
);

create function match_documents(
  query_embedding vector(384),
  match_count int
)
returns table(id bigint, content text, source text, similarity float)
language sql stable as $$
  select id, content, source,
         1 - (documents.embedding <=> query_embedding) as similarity
  from documents
  order by documents.embedding <=> query_embedding
  limit match_count;
$$;
```
<br>

### 7️⃣ Set up a Dropbox App

1. Go to [Dropbox Developers](https://www.dropbox.com/developers) → Create App

2. Choose `Scoped access` and next `Full Dropbox`
   
<br>

### 8️⃣ Set up the App Console

1. In the **Permissions** tab, enable the following options:

<img width="1038" height="315" alt="image" src="https://github.com/user-attachments/assets/690d6cc7-70da-4498-b11b-97034a9ebeb1" />

<br>
<br>

2. In the **Settings** tab, generate the access token:
   
<img width="308" height="113" alt="image" src="https://github.com/user-attachments/assets/44748592-b119-4f29-b31a-decffd9a749a" />

<br>
<br>

3. Copy the generated token and paste it into the `.env` file as `DROPBOX_ACCESS_TOKEN`.

> ⚠️ **Note:**  
> This access token is valid for approximately **4 hours**.  
> For production use, it's recommended to switch to a **refresh token** for automatic renewal and longer validity.

<br>

### 9️⃣ Upload your documents to Dropbox

Place some documents into main the folder in Dropbox.  
You can use the provided examples from the `sample_documents` folder (included in this repository),  
or upload your `.txt`, `.pdf`, or `.docx` files. 
<br>
<br>

### 🔟 Get your Claude API key
1. Go to [Anthropic Console](https://console.anthropic.com)
2. Create an API key, copy it and paste it into the `.env` file as `ANTHROPIC_API_KEY`.
<br>

### 1️⃣1️⃣ Run the app

```bash
streamlit run app.py
```

The agent will:

- Connect to Dropbox and index all files (.txt, .pdf, .docx)
- Store embeddings in Supabase
- Launch a Streamlit chat interface powered by Claude Haiku







