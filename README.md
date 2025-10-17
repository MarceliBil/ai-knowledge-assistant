# 🤖 AI Knowledge Agent

An intelligent company knowledge assistant built with **Streamlit**, **Claude (Anthropic)**, and **Supabase**.  
It indexes internal documents stored in **Dropbox**, converts them into embeddings for semantic search, and answers user questions based strictly on company knowledge.

---

## 🧠 Overview

This project demonstrates a lightweight **Retrieval-Augmented Generation (RAG)** pipeline:

1. **Document ingestion:**  
   Text, PDF, and DOCX files are automatically fetched from a connected Dropbox folder.

2. **Embedding & storage:**  
   Each document is split into overlapping chunks, embedded locally using `all-MiniLM-L6-v2`, and stored in a Supabase table with the `pgvector` extension.

3. **Context-aware responses:**  
   When a user asks a question, the agent retrieves the most semantically relevant chunks from Supabase and passes them as context to **Claude Haiku 3.5** via the Anthropic API.

4. **Chat interface:**  
   The Streamlit UI provides a ChatGPT-like experience, including:
   - Persistent chat history  
   - Typing indicator / spinner (“Thinking...”)  
   - Clean dark theme with custom icons  
   - Automatic Dropbox reindexing on startup  
   - Precise, company-specific answers only  

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
