import streamlit as st
from anthropic import Anthropic
from rag_engine import index_documents, search_similar
import os

st.set_page_config(page_title="AI Knowledge Agent", layout="centered")
st.title("AI Knowledge Agent")

if "indexed" not in st.session_state:
    index_documents()
    st.session_state["indexed"] = True
    st.success("Dropbox documents are up to date.")

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

client = Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

st.markdown("---")

for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask a question...")

if user_input:
    st.chat_message("user").markdown(user_input)
    st.session_state["chat_history"].append({"role": "user", "content": user_input})

    results = search_similar(user_input)
    context = "\n\n".join(r["content"] for r in results or [])

    conversation = ""
    for msg in st.session_state["chat_history"]:
        conversation += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""
You are a helpful AI knowledge assistant for a company.
Use the following context from internal documents if relevant:
{context}

Chat history:
{conversation}

Now continue the conversation naturally, in the same language as the user.
"""

    with st.spinner("Thinking..."):
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

    answer = response.content[0].text.strip()
    st.chat_message("assistant").markdown(answer)
    st.session_state["chat_history"].append({"role": "assistant", "content": answer})
