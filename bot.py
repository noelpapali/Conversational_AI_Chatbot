import pinecone
import os
from transformers import AutoTokenizer, AutoModel
import torch
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class UTDallasAssistant:
    def __init__(self, pinecone_api_key, pinecone_index_name, aiml_api_key):
        """
        Initialize the UTDallas assistant with Pinecone vector database

        Args:
            pinecone_api_key (str): Your Pinecone API key
            pinecone_index_name (str): Name of your Pinecone index
            aiml_api_key (str): Your API key for aimlapi.com
        """
        self.aiml_api_key = aiml_api_key
        self.api_url = "https://api.aimlapi.com/v1/chat/completions"
        self.off_topic_response = "I'm here to assist you with UTDallas related queries. Try asking about UTD programs, scholarships, admissions, or campus information."

        # Initialize Pinecone
        self.pinecone = pinecone.Pinecone(api_key=pinecone_api_key)
        self.index = self.pinecone.Index(pinecone_index_name)

        # Initialize embedding model
        self.tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        self.model = AutoModel.from_pretrained('bert-base-uncased')

        # Basic conversation handlers
        self.greetings = {
            'hi': "Hello! How can I help you with UTDallas today?",
            'hello': "Hi there! What UTDallas information are you looking for?",
            'hey': "Hey! Ready to help with UTDallas questions.",
            'how are you': "I'm doing well, thanks! How can I assist you with UTDallas?",
            "how's your day": "It's good! I'm here to help with UTDallas information.",
            'bye': "Goodbye! Go Comets!",
            'goodbye': "Have a great day! Go Comets!",
            'exit': "Goodbye! Feel free to come back with UTDallas questions.",
            'quit': "See you later! Don't hesitate to ask about UTDallas."
        }

    def _get_embedding(self, text):
        """Generate embedding for text using BERT"""
        inputs = self.tokenizer(text, return_tensors='pt', truncation=True, padding=True)
        with torch.no_grad():
            outputs = self.model(**inputs)
        return outputs.last_hidden_state.mean(dim=1).squeeze().tolist()

    def _is_greeting(self, question):
        """Check if the input is a basic greeting/conversation"""
        input_lower = question.lower().strip()
        for pattern, response in self.greetings.items():
            if input_lower.startswith(pattern):
                return response
        return None

    def _get_relevant_context(self, question, top_k=3):
        """Retrieve relevant context from Pinecone"""
        try:
            # Generate embedding for the question
            query_embedding = self._get_embedding(question)

            # Query Pinecone for similar vectors
            results = self.index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )

            # Extract and combine the relevant text from metadata
            context = ""
            for match in results['matches']:
                if 'metadata' in match and 'text' in match['metadata']:
                    context += match['metadata']['text'] + "\n\n"

            return context.strip() if context else None

        except Exception as e:
            logger.error(f"Error retrieving context from Pinecone: {e}")
            return None

    def _call_aiml_api(self, prompt, context):
        """Make API call with Pinecone-retrieved context"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.aiml_api_key}"
        }

        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "system",
                    "content": f"Answer strictly based on this UTDallas information: {context}\n"
                               "If you cannot answer from this information, say: "
                               f"'{self.off_topic_response}'"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(self.api_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            return f"Error: {str(e)}"

    def chat(self):
        """Start the UTDallas assistant"""
        print("UTDallas Assistant initialized. Type 'quit' or 'exit' to end the conversation.")

        while True:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            # Check for greetings first
            greeting_response = self._is_greeting(user_input)
            if greeting_response:
                print(f"UTD Assistant: {greeting_response}")
                if user_input.lower() in ['bye', 'goodbye', 'exit', 'quit']:
                    break
                continue

            # Get relevant context from Pinecone
            context = self._get_relevant_context(user_input)

            if not context:
                print(f"UTD Assistant: {self.off_topic_response}")
                continue

            # Get response using the context
            response = self._call_aiml_api(user_input, context)
            print(f"UTD Assistant: {response}")


if __name__ == "__main__":
    # Configuration
    PINECONE_API_KEY = os.getenv("pinecone_api_key") or "pcsk_6BW7Ww_R69RwsRFVt1TvXMqv5H7MqK7Ue13dtAdDTQapS4Gxh9hnGVGg477gnaj8hoDmKU"
    PINECONE_INDEX_NAME = "chat-bot"  # Your Pinecone index name
    AIML_API_KEY = os.getenv("AIML_API_KEY") or "51dc162e854347a18e57aca1f56c6827"

    try:
        assistant = UTDallasAssistant(
            pinecone_api_key=PINECONE_API_KEY,
            pinecone_index_name=PINECONE_INDEX_NAME,
            aiml_api_key=AIML_API_KEY
        )
        assistant.chat()
    except Exception as e:
        print(f"Failed to initialize assistant: {str(e)}")
