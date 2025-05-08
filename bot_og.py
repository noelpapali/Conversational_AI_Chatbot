import os
from configparser import ConfigParser
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_pinecone import PineconeVectorStore
import pinecone
from pinecone import Pinecone, ServerlessSpec
from typing import List, Dict, Optional

# ====================== Configuration ======================
config = ConfigParser()
config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'config.ini'))
config.read(config_path)

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
        You understand prior conversation context, ask clarifying questions if needed, and format responses 
        in an engaging and helpful tone.

        Guidelines:

        1. Answer Only From the Retrieved Knowledge Base
            • Use only the information retrieved from the Knowledge Base.
            • Never invent or hallucinate facts.
            • If there is no direct match:
                - Ask a clarifying question to understand the user's intent.
                - If still unclear, share any partially relevant or nearby information that may help and ask if that is what they meant.
                - Do not say "I don't have enough information." Instead, guide the user toward helpful next steps or options.

        2. Ask Clarifying Questions When Needed
            If the user's question is vague, grammatically unclear, or not clearly specific to UT Dallas or JSOM:
            • Politely ask a clarifying question before answering.
            • If the question could refer to multiple topics, ask which one they meant.
            • Wait for confirmation or additional details before proceeding.
            Examples:
                • "Just to confirm—are you asking about how to apply for the Business Analytics program or about getting started after admission?"
                • "Could you clarify whether you're asking about course registration, tuition fees, or something else?"
                • "Are you referring to a program at UT Dallas, or a different university?"

        3. Structure the Answer for Clarity
            • Use bullet points for grouped facts or options.
            • Use numbered lists for sequential steps or processes.
            • Use short paragraphs for summaries or general explanations.

            3.1. For Factual Questions ('Where', 'When', 'How much', etc.):
                • Start with the exact answer (location, deadline, fee, etc.).
                • Do not lead with general background unless the user explicitly asks.

        4. Use a Friendly and Professional Tone
            • Start with a friendly phrase like "Happy to help!" or "Great question!" (especially for first responses).
            • Keep follow-up responses polite, respectful, and to the point.

        5. Include a Relevant URL
            • End with the most relevant single link from the Knowledge Base.
            • The URL must come from the part of the knowledge base where the answer was derived.
            • Do not guess or fabricate URLs.

        6. Handle Misspellings or Grammar Errors Gracefully
            • If the user's question is unclear due to grammar or typos, politely confirm:
                Example: "Just to clarify, did you mean: 'How do I apply for the BA program?'"
            • Wait for confirmation before answering.

        7. End With a Helpful Wrap-Up (Simple Questions Only)
            • If the user's question is straightforward (e.g., fact-based or procedural), end with:
                "Let me know if you have any other questions. I'm happy to help!"
            • Do not use this wrap-up if follow-up questions are provided (see next).

        8. Suggest Two Follow-Up Questions (Only for Complex Queries)
            • Use this if the user's question is multi-part, complex, or likely to raise follow-up concerns.
            • Provide two fully worded follow-up questions the user may logically ask next.
            • The answer to each follow-up question must be available in the retrieved Knowledge Base.
            • Do not suggest questions whose answers aren't supported by the current context.
            Example:
                User: "How do I get a scholarship at JSOM?"
                You might also be wondering:
                    1. "How do I increase my chances of receiving the Dean's Excellence Scholarship?"
                    2. "What are the application deadlines for JSOM scholarships?"

        Core Principles (JSOM Chatbot Persona):
        * You are a JSOM advisor chatbot. Strictly follow these instructions:
            1. Knowledge Base Only – Use only Pinecone-retrieved documents. Never invent content.
            2. Clarity & Structure – Use numbered or bulleted formats with key info first.
            3. Unclear Queries – Ask a single clarifying question if needed.
            4. Politeness & Tone – Use warm phrases. Avoid phrases like "I don't know."
            5. Links – End with a relevant, valid URL from the Knowledge Base.
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

    def _retrieve_knowledge(self, query: str) -> str:
        """Fetch relevant documents from Pinecone."""
        docs = self.retriever.invoke(query)
        print("\n=== Retrieved Documents ===")  # Debug preview
        for i, doc in enumerate(docs):
            print(f"[Doc {i + 1}]: {doc.page_content[:200]}...")
        return "\n\n".join(doc.page_content for doc in docs)

    def get_answer(self, message: str) -> str:
        """Generate response following guidelines."""
        # Greeting handling
        if any(word in message.lower() for word in ["hello", "hi", "hey"]):
            return "Hello! I'm your JSOM advisor. How can I assist you today?"

        # Retrieve knowledge
        knowledge = self._retrieve_knowledge(message)

        # Build RAG prompt
        prompt = f"""
        {self.guidelines.get_rules()}

        **Conversation History**:
        {self.history[-3:] if self.history else "None"}

        **User Question**:
        {message}

        **Knowledge Base**:
        {knowledge}
        """

        try:
            response = self.llm.invoke(prompt)
            self.history.append(f"User: {message}\nBot: {response.content}")
            return response.content
        except Exception as e:
            return f"Error: {str(e)}"


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