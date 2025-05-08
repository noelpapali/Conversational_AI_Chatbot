import os
from configparser import ConfigParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
import pinecone
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional


# ====================== Configuration ======================
def get_config():
    """Get configuration from either config.ini or environment variables."""
    config = ConfigParser()

    # Try to read from config.ini first (local development)
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.ini'))
    if os.path.exists(config_path):
        config.read(config_path)
        return config

    # If config.ini doesn't exist, use environment variables (deployment)
    config['pinecone'] = {
        'api_key': os.environ.get('PINECONE_API_KEY', ''),
        'env': os.environ.get('PINECONE_ENV', ''),
        'index': os.environ.get('PINECONE_INDEX', '')
    }

    config['embeddings'] = {
        'model_name': os.environ.get('EMBEDDING_MODEL', 'sentence-transformers/all-mpnet-base-v2')
    }

    config['openai'] = {
        'api_key': os.environ.get('OPENAI_API_KEY', ''),
        'model_name': os.environ.get('OPENAI_MODEL_NAME', 'gpt-3.5-turbo'),
        'temperature': os.environ.get('TEMPERATURE', '0.1')
    }

    return config


config = get_config()

# Pinecone
PINECONE_API_KEY = config["pinecone"]["api_key"]
PINECONE_ENV = config["pinecone"]["env"]
PINECONE_INDEX_NAME = config["pinecone"]["index"]

# OpenAI
OPENAI_API_KEY = config["openai"]["api_key"]
LLM_MODEL_NAME = config["openai"]["model_name"]
TEMPERATURE = float(config["openai"]["temperature"])

# Embeddings
EMBEDDINGS_MODEL_NAME = config["embeddings"]["model_name"]


# ====================== Core Classes ======================
class ChatbotGuidelines:
    """Centralized rules for chatbot behavior."""

    def __init__(self):
        self.rules = """
        You are a friendly and knowledgeable assistant for the Jindal School of Management at UT Dallas.
        With a strong background of over 20 years' experience in customer service, you specialize in helping
        students, parents, and prospective applicants find accurate and relevant information. Your primary goal
        is to provide clear, helpful, and well-structured answers based only on the retrieved Knowledge Base.
        You understand prior conversation context and format responses in an engaging and helpful tone.

        Guidelines:

        1. Answer Only From the Retrieved Knowledge Base
            • Use only the information retrieved from the Knowledge Base.
            • Never invent or hallucinate facts.
            • If there is no direct match, generate two follow-up questions related to UTD or JSOM.

        2. Structure the Answer for Clarity
            • Use bullet points for grouped facts or options.
            • Use numbered lists for sequential steps or processes.
            • Use short paragraphs for summaries or general explanations.

            3.1. For Factual Questions ('Where', 'When', 'How much', etc.):
                • Start with the exact answer (location, deadline, fee, etc.).
                • Do not lead with general background unless the user explicitly asks.

        3. Use a Friendly and Professional Tone
            • Start with a friendly phrase like "Happy to help!" or "Great question!" (especially for first responses).
            • Keep follow-up responses polite, respectful, and to the point.

        4. Include a Relevant URL
            • End with the most relevant single link from the Knowledge Base.
            • The URL must come from the part of the knowledge base where the answer was derived.
            • Do not guess or fabricate URLs.

        5. Handle Misspellings or Grammar Errors Gracefully
            • If the user's question is unclear due to grammar or typos, politely confirm:
                Example: "Just to clarify, did you mean: 'How do I apply for the BA program?'"
            • Wait for confirmation before answering.

        6. End With a Helpful Wrap-Up (Simple Questions Only)
            • If the user's question is straightforward (e.g., fact-based or procedural), end with:
                "Let me know if you have any other questions. I'm happy to help!"
            • Do not use this wrap-up if follow-up questions are provided (see next).

        7. Suggest Two Follow-Up Questions (Only when no direct answer is found)
            • Use this if there is no direct match in the retrieved Knowledge Base.
            • Provide two fully worded follow-up questions the user may logically ask next, related to UTD or JSOM.
            • The answer to each follow-up question must be potentially available within a broader UTD/JSOM context.
            Example:
                User: "What are the events in TEXAS?"
                You might also be wondering:
                    1. "What are the events at UTD?"
                    2. "What are the upcoming events at JSOM?"
            Example:
                User: "what are scholarships available in US for masters?"
                You might also be wondering:
                    1. "what are scholarships available at UTD?"
                    2. "what are scholarships are offered at JSOM?"
        """

    def get_rules(self) -> str:
        return self.rules


class JSOMChatbot:
    def __init__(self):
        # Initialize components
        self.guidelines = ChatbotGuidelines()
        self._setup_models()
        self.history = []

    def _setup_models(self):
        """Initialize Pinecone, embeddings, and LLM."""
        # Pinecone
        self.pc = Pinecone(api_key=PINECONE_API_KEY)
        self.index = self.pc.Index(PINECONE_INDEX_NAME)

        # Embeddings
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL_NAME)

        # LLM
        self.llm = ChatOpenAI(
            temperature=TEMPERATURE,
            model=LLM_MODEL_NAME,
            openai_api_key=OPENAI_API_KEY
        )
        print(f"Using {LLM_MODEL_NAME} (Temperature: {TEMPERATURE})")

        # Retriever
        self.vector_store = PineconeVectorStore(
            index=self.index,
            embedding=self.embeddings
        )
        self.retriever = self.vector_store.as_retriever(search_kwargs={'k': 10})

    def _retrieve_knowledge(self, query: str) -> List:
        """Fetch relevant documents from Pinecone."""
        docs = self.retriever.invoke(query)
        print("\n=== Retrieved Documents ===")  # Debug preview
        for i, doc in enumerate(docs):
            print(f"[Doc {i + 1}]: {doc.page_content[:200]}...")
        return docs  # Return the actual documents

    def generate_follow_up_questions(self, message: str) -> List[str]:
        """Generate follow-up questions related to UTD or JSOM."""
        prompt = f"""
        The user asked a question that does not have a direct answer in the retrieved knowledge base.
        The user's question was: '{message}'

        Generate two follow-up questions that the user might be interested in that are specifically related to UT Dallas or the Jindal School of Management. These questions should explore related topics that a prospective or current student might ask. Ensure the questions are fully worded.
        """
        try:
            response = self.llm.invoke(prompt)
            follow_up_questions = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
            return follow_up_questions[:2]  # Return only the first two
        except Exception as e:
            print(f"Error generating follow-up questions: {str(e)}")
            return []

    def get_answer(self, message: str) -> str:
        """Generate response following guidelines."""
        # Retrieve knowledge FIRST
        docs = self._retrieve_knowledge(message)

        # Check if no relevant documents were retrieved
        if not docs:
            # Only generate follow-up questions if the initial greeting wasn't the sole input
            if not any(word in message.lower() for word in ["hello", "hi", "hey"]):
                follow_up_questions = self.generate_follow_up_questions(message)
                if follow_up_questions:
                    response = "I specialize in providing information about the Jindal School of Management at UT Dallas. Here are two follow-up questions you might be interested in:\n"
                    for i, question in enumerate(follow_up_questions, 1):
                        response += f"{i}. {question}\n"
                    return {"response": response, "follow_ups": follow_up_questions, "needs_clarification": False}
                else:
                    return {"response": "I'm sorry, but I couldn't find any specific information related to your query within my knowledge base. Is there anything else about UT Dallas or JSOM I can help you with?", "follow_ups": [], "needs_clarification": False}
            else:
                return {"response": "Hello! I'm your JSOM advisor. How can I assist you today?", "follow_ups": [], "needs_clarification": False}

        # If relevant documents were found, respond with those details
        prompt = f"""
        {self.guidelines.get_rules()}

        **Conversation History**:
        {self.history[-3:] if self.history else "None"}

        **User Question**:
        {message}

        **Knowledge Base**:
        {''.join(doc.page_content for doc in docs)}
        """

        try:
            response = self.llm.invoke(prompt)
            self.history.append(f"User: {message}\nBot: {response.content}")
            return {"response": response.content, "follow_ups": [], "needs_clarification": False}
        except Exception as e:
            return {"response": f"Error: {str(e)}", "follow_ups": [], "needs_clarification": False}


# ====================== Main Execution ======================
if __name__ == "__main__":
    bot = JSOMChatbot()
    print("JSOM Chatbot ready. Type 'exit' to quit.\n")
    print(PINECONE_INDEX_NAME)

    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        response = bot.get_answer(user_input)
        print("\nAssistant:", response, "\n")