import os
import logging
import time

import numpy as np
from transformers import AutoTokenizer, AutoModel
import pinecone
import torch

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variable for NumExpr
os.environ['NUMEXPR_MAX_THREADS'] = '12'


class TextEmbedder:
    def __init__(self, model_name='bert-base-uncased'):
        self.model_name = model_name
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModel.from_pretrained(model_name)
            logger.info(f"Successfully loaded model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def chunk_text(self, text, chunk_size=512):
        """Splits the text into chunks of a specified size."""
        words = text.split()
        chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
        return chunks

    def get_embeddings(self, text_chunks):
        """Generates embeddings for a list of text chunks."""
        embeddings = []
        for chunk in text_chunks:
            try:
                inputs = self.tokenizer(chunk, return_tensors='pt', max_length=512, truncation=True, padding=True)
                with torch.no_grad():
                    outputs = self.model(**inputs)
                # Use mean pooling to get sentence embedding
                chunk_embedding = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
                embeddings.append(chunk_embedding.tolist())  # Convert to list for Pinecone
            except Exception as e:
                logger.error(f"Error processing chunk: {e}")
                continue

        return embeddings


class PineconeManager:
    def __init__(self, api_key, index_name="quickstart", dimension=768, metric="cosine"):
        self.api_key = api_key
        self.index_name = index_name
        self.dimension = dimension
        self.metric = metric
        self.pc = pinecone.Pinecone(api_key=api_key)

        # Initialize or connect to index
        if index_name not in self.pc.list_indexes().names():
            logger.info(f"Creating new Pinecone index: {index_name}")
            self.pc.create_index(
                name=index_name,
                dimension=dimension,
                metric=metric
            )
            # Wait for index to be ready
            while not self.pc.describe_index(index_name).status['ready']:
                time.sleep(1)

        self.index = self.pc.Index(index_name)
        logger.info(f"Connected to Pinecone index: {index_name}")

    def upsert_embeddings(self, embeddings, documents, ids):
        """Upserts embeddings and documents to Pinecone index."""
        try:
            # Prepare data for Pinecone (list of tuples: (id, embedding, {"text": document}))
            vectors = [
                (str(id_), embedding, {"text": document})
                for id_, embedding, document in zip(ids, embeddings, documents)
            ]

            # Upsert in batches (Pinecone recommends batches of 100 or less)
            batch_size = 100
            for i in range(0, len(vectors), batch_size):
                batch = vectors[i:i + batch_size]
                self.index.upsert(vectors=batch)

            logger.info(f"Successfully upserted {len(vectors)} vectors to Pinecone")
            return True
        except Exception as e:
            logger.error(f"Failed to upsert embeddings: {e}")
            return False


def load_and_process_data(file_path):
    """Loads and processes text data from a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        return text
    except Exception as e:
        logger.error(f"Error loading file {file_path}: {e}")
        raise


def main():
    # Configuration
    config = {
        "input_file": "processed_data/cerprgs_execed_merged.txt",
        "pinecone_api_key": "pcsk_5j5943_Sc7B63x4vFjwtX7X4b5PoF7sDUiwG3uPHqjQMKNphUdhPm6VpGcMTzayYS7S5Km",  # Replace with your actual API key
        "index_name": "utd-bot",  # Can customize this
        "chunk_size": 512,
        "embedding_dimension": 768  # BERT-base produces 768-dim embeddings
    }

    # Initialize components
    embedder = TextEmbedder()
    pinecone_manager = PineconeManager(
        api_key=config["pinecone_api_key"],
        index_name=config["index_name"],
        dimension=config["embedding_dimension"]
    )

    # Load and process data
    try:
        text = load_and_process_data(config["input_file"])
        chunks = embedder.chunk_text(text, chunk_size=config["chunk_size"])
        logger.info(f"Created {len(chunks)} text chunks")

        # Generate embeddings
        embeddings = embedder.get_embeddings(chunks)
        logger.info(f"Generated {len(embeddings)} embeddings")

        # Prepare data for Pinecone
        ids = [f"chunk_{i}" for i in range(len(chunks))]

        # Save to Pinecone
        success = pinecone_manager.upsert_embeddings(
            embeddings=embeddings,
            documents=chunks,
            ids=ids
        )

        if success:
            logger.info("Pipeline completed successfully")
        else:
            logger.error("Pipeline completed with errors")

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")


if __name__ == "__main__":
    main()