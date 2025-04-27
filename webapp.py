import streamlit as st
from configparser import ConfigParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
import pinecone
from pinecone import Pinecone, ServerlessSpec

import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# === Load configuration from config.ini ===
config = ConfigParser()
config.read("config.ini")

PINECONE_API_KEY     = config["pinecone"]["api_key"]
PINECONE_ENV         = config["pinecone"]["env"]
PINECONE_INDEX_NAME  = config["pinecone"]["index"]

OPENAI_API_KEY       = config["openai"]["api_key"]
# Optional: fetch model names if you have them in config
# LLM_MODEL_NAME       = config["openai"].get("model_name", "gpt-4o-mini")
# EMBEDDINGS_MODEL_NAME = config["embeddings"].get("model_name", "all-MiniLM-L6-v2")

# === Initialize Pinecone and the necessary models ===
pc = Pinecone(
    api_key=PINECONE_API_KEY,
    spec=ServerlessSpec(cloud='aws', region=PINECONE_ENV)
)
index = pc.Index(PINECONE_INDEX_NAME)

# Initialize embeddings
embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize the LLM
llm = ChatOpenAI(
    temperature=0.2,
    model='gpt-4o-mini',
    openai_api_key=OPENAI_API_KEY
)
print("Using gpt-4o-mini for the LLM.")

# Create the Pinecone vector store and a retriever
vector_store = PineconeVectorStore(index=index, embedding=embeddings_model)
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})

def get_answer(message, history):
    greeting_keywords = ["hello", "hi", "good morning", "good afternoon",
                         "good evening", "how are you", "what's up"]
    if any(keyword in message.lower() for keyword in greeting_keywords):
        greeting_prompt = f"Respond to this greeting in a friendly manner: {message}"
        return llm(greeting_prompt)
    else:
        docs = retriever.invoke(message)
        print("\nRetrieved Documents:")
        for i, doc in enumerate(docs):
            print(f"Document {i + 1}: {doc.page_content[:300]}...\n")
        knowledge = "\n\n".join(doc.page_content for doc in docs)
        rag_prompt = f"""
You are a UT Dallas assistant that answers questions solely based on the provided knowledge.
You should answer questions related to JSOM, admissions, programs (freshman, masters, PhD, executive education),
deadlines, tuition rates (bursar), scholarships, events, certificate programs, student resources, faculty, news,
and centers of excellence at UT Dallas.
If the provided knowledge is insufficient, politely indicate that you do not have enough information.

Conversation History:
{history}

User Question:
{message}

Knowledge Base:
{knowledge}

Provide a concise answer based only on the above knowledge.
"""
        try:
            response = llm(rag_prompt)
            if isinstance(response, dict):
                return response.get('content', '')
            return response.content
        except Exception as e:
            print(f"Error during LLM call: {e}")
            return "Sorry, I encountered an error while generating the response."

if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Comet Bot 1.0")
st.markdown("This is a chatbot that responds to your queries regarding the UT Dallas (JSOM).")

with st.form(key='chat_form', clear_on_submit=True):
    user_input = st.text_input("Your Message:")
    submit_button = st.form_submit_button(label="Send")

if submit_button and user_input:
    conversation_history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages
    )
    answer = get_answer(user_input, conversation_history)
    st.session_state.messages.append({"role": "User", "content": user_input})
    st.session_state.messages.append({"role": "Assistant", "content": answer})

for msg in st.session_state.messages:
    if msg["role"] == "User":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")