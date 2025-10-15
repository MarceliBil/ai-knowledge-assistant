import streamlit as st
from anthropic import Anthropic
from rag_engine import index_documents, search_similar
import os

st.set_page_config(page_title="AI Knowledge Agent", layout="centered")
st.title("AI Knowledge Agent")

hide_ui = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_ui, unsafe_allow_html=True)

custom_chat_css = """
<style>
.st-emotion-cache-khw9fs {
    background-color: #f2f2f2;
}

.st-emotion-cache-z68l0b {
    background-color: rgb(0 207 255);
}

[data-testid="stChatInput"] > div {
    border: 1px solid rgba(255, 255, 255, 0.6) !important;
    box-shadow: none !important;
    border-radius: 9999px !important;
}

[data-testid="stChatInput"] > div:focus-within {
    border: 1px solid #ffffff !important;
    box-shadow: 0 0 6px rgba(255, 255, 255, 0.4) !important;
}
</style>
"""
st.markdown(custom_chat_css, unsafe_allow_html=True)


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
    You are a corporate knowledge assistant with access to internal company documents.
    Your purpose is to answer only questions related to company policies, procedures, and internal knowledge.
    If the user's question is unrelated to company knowledge, say very briefly you can only answer work-related or internal questions — without apologizing or mentioning missing materials.

    Answer using only the information from the provided context below. 
    If the context doesn't contain the answer, say very briefly that you can only respond to company-related questions.

    Context:
    {context}

    Chat history:
    {conversation}

    Respond in the same language as the user and keep answers concise and professional.
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
