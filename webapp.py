import streamlit as st
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
import pinecone
from pinecone import Pinecone, ServerlessSpec


import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# === Configuration (update keys and parameters as needed) ===
PINECONE_API_KEY = "pcsk_6SHZxP_MazDP4PaSNokSMfNZvxeo37u4Y1j6KWYLPqj2jQysvLuLm7CbBuHnajYDaTanFA"
PINECONE_ENV = "us-east-1"           # For example: "us-west1-gcp" if applicable
PINECONE_INDEX_NAME = "chatbotv1"
OPENAI_API_KEY = "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"

# === Initialize Pinecone and the necessary models ===
# Set up Pinecone (with the new API)
pc = Pinecone(
    api_key=PINECONE_API_KEY,
    spec=ServerlessSpec(cloud='aws', region=PINECONE_ENV)
)
index = pc.Index(PINECONE_INDEX_NAME)

# Initialize embeddings (make sure the model's output dimension matches your Pinecone index)
embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize the LLM (using GPT-4o-mini here)
llm = ChatOpenAI(temperature=0.2, model='gpt-4o-mini', openai_api_key=OPENAI_API_KEY)
print("Using gpt-4o-mini for the LLM.")

# Create the Pinecone vector store and a retriever
vector_store = PineconeVectorStore(index=index, embedding=embeddings_model)
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})

# === Define the function that gets the answer ===
def get_answer(message, history):
    # Simple greeting check – responds differently if a greeting is detected
    greeting_keywords = ["hello", "hi", "good morning", "good afternoon", "good evening", "how are you", "what's up"]
    if any(keyword in message.lower() for keyword in greeting_keywords):
        greeting_prompt = f"Respond to this greeting in a friendly manner: {message}"
        return llm(greeting_prompt)
    else:
        # Retrieve relevant documents from the Pinecone DB
        docs = retriever.invoke(message)

        # (Optional) Debug output: print first 300 characters of each document.
        print("\nRetrieved Documents:")
        for i, doc in enumerate(docs):
            print(f"Document {i + 1}: {doc.page_content[:300]}...\n")

        # Concatenate retrieved document contents
        knowledge = "\n\n".join(doc.page_content for doc in docs)

        # Build the Retrieval-Augmented Generation prompt.
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
            response_text = response['content'] if isinstance(response, dict) else response.content
            return response_text
        except Exception as e:
            print(f"Error during LLM call: {e}")
            return "Sorry, I encountered an error while generating the response."

# === Initialize conversation history in Streamlit session state ===
if "messages" not in st.session_state:
    st.session_state.messages = []

st.title("Comet Bot 1.0")

st.markdown("This is a chatbot that responds to your queries regarding the UT Dallas (JSOM).")

# === Input Form ===
with st.form(key='chat_form', clear_on_submit=True):
    user_input = st.text_input("Your Message:")
    submit_button = st.form_submit_button(label="Send")

if submit_button and user_input:
    conversation_history = "\n".join(
        f"{msg['role']}: {msg['content']}" for msg in st.session_state.messages
    )
    answer = get_answer(user_input, conversation_history)

    # If the answer is already a string, just use it as is.
    if isinstance(answer, str):
        response_text = answer
    # (Optional) If you're not sure about the type, you can add extra checks:
    elif isinstance(answer, dict):
        response_text = answer.get('content', '')
    elif hasattr(answer, 'content'):
        response_text = answer.content
    else:
        response_text = str(answer)  # Fallback conversion

    st.session_state.messages.append({"role": "User", "content": user_input})
    st.session_state.messages.append({"role": "Assistant", "content": response_text})

# === Display the conversation ===
for msg in st.session_state.messages:
    if msg["role"] == "User":
        st.markdown(f"**You:** {msg['content']}")
    else:
        st.markdown(f"**Assistant:** {msg['content']}")
