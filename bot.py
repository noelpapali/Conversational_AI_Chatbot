from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
import pinecone
from pinecone import Pinecone, ServerlessSpec

# Configuration
PINECONE_API_KEY = "pcsk_6R2ucq_J4vEtoSvYHs21aTArmsRzqRpE6SSgYvV6DKtm3kDZCe6Bei8nVK8jUZoJmbL9f4"  # Replace with your Pinecone API key
PINECONE_ENV = "us-east-1"           # e.g., "us-west1-gcp"
PINECONE_INDEX_NAME = "chatbotv1"
OPENAI_API_KEY = "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"  # Replace with your OpenAI API key"

# Initialize Pinecone connection using the new API
pc = Pinecone(
    api_key=PINECONE_API_KEY,
    spec=ServerlessSpec(cloud='aws', region=PINECONE_ENV)
)
index = pc.Index(PINECONE_INDEX_NAME)

# Use a Hugging Face embedding model that produces vectors matching your Pinecone index dimension (e.g., 384)
embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize the ChatOpenAI model (the GPT model) for response generation
llm = ChatOpenAI(temperature=0.2, model='gpt-4o-mini', openai_api_key=OPENAI_API_KEY)
print("Using gpt-4o-mini for the LLM.")

# Create the Pinecone vector store and set up a retriever
vector_store = PineconeVectorStore(index=index, embedding=embeddings_model)
num_results = 5
retriever = vector_store.as_retriever(search_kwargs={'k': num_results})


def get_answer(message, history):
    # Check for generic greetings
    greeting_keywords = ["hello", "hi", "good morning", "good afternoon", "good evening", "how are you", "what's up"]
    if any(keyword in message.lower() for keyword in greeting_keywords):
        greeting_prompt = f"Respond to this greeting in a friendly manner: {message}"
        return llm(greeting_prompt)
    else:
        # Retrieve relevant chunks from the Pinecone DB
        docs = retriever.invoke(message)

        # Display (optional) a preview of retrieved documents for debugging purposes
        print("\nRetrieved Documents:")
        for i, doc in enumerate(docs):
            print(f"Document {i + 1}: {doc.page_content[:300]}...\n")

        # Concatenate all retrieved content as the knowledge base
        knowledge = "\n\n".join(doc.page_content for doc in docs)

        # Build the Retrieval-Augmented Generation prompt.
        # The assistant must answer using only the provided knowledge.
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
            return response
        except Exception as e:
            print(f"Error during LLM call: {e}")
            return "Sorry, I encountered an error while generating the response."


# Maintain conversation history (if needed)
history = ""

# Continuous chat loop
while True:
    query = input("You: ")
    if query.lower() == "exit":
        print("Exiting the chat...")
        break

    answer = get_answer(query, history)
    print("Assistant:", answer)

    # Update conversation history
    history += f"User: {query}\nAssistant: {answer}\n\n"
