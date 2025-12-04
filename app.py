import streamlit as st
from anthropic import Anthropic
import threading
import rag_engine
from rag_engine import index_documents, search_similar
import os
import time


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
    st.session_state["indexed"] = False
    st.session_state["indexing"] = False


def _start_indexing_background():
    if rag_engine._indexing_in_progress:
        return

    def _target():

        try:
            index_documents()
        except Exception as e:
            print("Indexing failed:", e)

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    st.session_state["indexing"] = True


if not rag_engine._indexing_in_progress and not st.session_state.get("indexed") and not st.session_state.get("indexing"):
    _start_indexing_background()

if rag_engine._indexing_in_progress or st.session_state.get("indexing"):
    st.info("Indexing in background — refresh or wait for completion.")
elif st.session_state.get("indexed"):
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
    st.session_state["chat_history"].append(
        {"role": "user", "content": user_input})

    results = search_similar(user_input)
    context = "\n\n".join(r["content"] for r in results or [])
    context_note = ""
    if not context:
        context_note = "No internal documents are available at the moment; answer based on general knowledge."

    conversation = ""
    for msg in st.session_state["chat_history"]:
        conversation += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""
    You are a corporate AI assistant with access to internal company documents.
    You answer only questions related to company policies, internal procedures, HR rules, and organizational knowledge.

    If a question is completely unrelated to work or internal knowledge,
    reply very briefly that you only provide information about internal company matters.

    If a question is somewhat related but the context does not clearly answer it,
    ask one short clarifying question instead of speculating.

    When answering:
    - Be concise and factual.
    - Use a professional tone, without apologizing or overexplaining.
    - Your final answer **must not exceed two short sentences.**
    - If you find yourself writing more than that, **summarize or truncate** the text.

    Base your answers strictly on the context below.

    Context:
    {context}

    {context_note}

    Chat history:
    {conversation}

    Respond in the same language as the user.
    """

    with st.spinner("Thinking..."):
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}],
        )

    answer = response.content[0].text.strip()
    st.chat_message("assistant").markdown(answer)
    st.session_state["chat_history"].append(
        {"role": "assistant", "content": answer})
