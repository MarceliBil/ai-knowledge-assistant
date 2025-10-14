import streamlit as st
from anthropic import Anthropic
from rag_engine import search_similar, index_documents
import os
from dotenv import load_dotenv

load_dotenv()

st.title("AI Knowledge Agent")

with st.spinner("Indexing Dropbox documents..."):
    index_documents()
st.success("Dropbox documents are up to date.")

query = st.text_input("Ask a question:")

if query:
    context_docs = search_similar(query)
    if not context_docs:
        st.warning("No relevant documents found in the knowledge base.")
    else:
        context = "\n\n".join(d["content"] for d in context_docs)
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        prompt = f"""Use the following context to answer the question.
If you cannot find the answer, say you don't know.

### CONTEXT:
{context}

### QUESTION:
{query}
"""
        response = client.messages.create(
            model="claude-3-5-haiku-latest",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )
        st.write(response.content[0].text)
