import os
import logging
from pathlib import Path
from configparser import ConfigParser
from sentence_transformers import SentenceTransformer
from langchain.docstore.document import Document

# Configure logging using your custom function
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Detect environment
IS_GITHUB = os.getenv('GITHUB_ACTIONS') == 'true'

config = ConfigParser()

# For GitHub, use the created config.ini in data_chunking folder
if IS_GITHUB:
    config.read('config.ini')
else:
    # Load configuration - keeps your local path handling
    config.read('../config.ini')
# Fetch embedding model name from config
EMBEDDINGS_MODEL_NAME = config["embeddings"]["model_name"]

# Initialize the SentenceTransformer model
embedding_model = SentenceTransformer(EMBEDDINGS_MODEL_NAME)
logging.info(f"Loaded embedding model: {EMBEDDINGS_MODEL_NAME}")

# Fetch Pinecone settings from config
PINECONE_API_KEY = config["pinecone"]["api_key"]
PINECONE_ENV = config["pinecone"]["env"]
INDEX_NAME = config["pinecone"]["index"]

# Initialize Pinecone using the new interface
from pinecone import Pinecone, ServerlessSpec

pc = Pinecone(api_key=PINECONE_API_KEY, spec=ServerlessSpec(cloud='aws', region=PINECONE_ENV))

if INDEX_NAME not in pc.list_indexes().names():
    logging.error(f"Index '{INDEX_NAME}' not found in Pinecone.")
    exit(1)

index = pc.Index(INDEX_NAME)
logging.info(f"Connected to Pinecone index: {INDEX_NAME}")


def get_input_path():
    """Resolve input file path for both local and GitHub environments"""
    local_path = Path("../processed_data/cleaned_merged_text.txt")
    github_path = Path(__file__).parent.parent / "processed_data" / "cleaned_merged_text.txt"

    if local_path.exists():
        return str(local_path)
    elif github_path.exists():
        return str(github_path)
    else:
        logging.error("Could not find input file in either location:")
        logging.error(f"Local path: {local_path}")
        logging.error(f"GitHub path: {github_path}")
        exit(1)

def split_text_into_overlapping_chunks(file_path, max_chunk_chars=2000, overlap_chars=400):
    """
    Splits the file content into overlapping chunks.
    - Splitting is performed on paragraph boundaries.
    - When a chunk reaches max_chunk_chars, it is saved and the next chunk is
      started with the last `overlap_chars` of the previous chunk.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read().strip()

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = ""
    i = 0

    while i < len(paragraphs):
        para = paragraphs[i]
        tentative = current_chunk + "\n\n" + para if current_chunk else para

        if len(tentative) <= max_chunk_chars:
            current_chunk = tentative
            i += 1
        else:
            if not current_chunk:
                for j in range(0, len(para), max_chunk_chars):
                    chunk_piece = para[j:j+max_chunk_chars]
                    chunks.append(chunk_piece.strip())
                i += 1
            else:
                chunks.append(current_chunk.strip())
                current_chunk = current_chunk[-overlap_chars:] if len(current_chunk) > overlap_chars else ""
    if current_chunk:
        chunks.append(current_chunk.strip())

    logging.info(f"Split text into {len(chunks)} overlapping chunks.")
    return chunks

def create_documents(chunks):
    """
    Creates Document objects from text chunks with minimal metadata.
    """
    documents = []
    for i, chunk in enumerate(chunks):
        doc = Document(page_content=chunk, metadata={"chunk_index": i})
        documents.append(doc)
    return documents


def embed_and_upsert_documents(documents, batch_size=100):
    """
    Generates embeddings and upserts them in batches to avoid exceeding Pinecone's size limits.
    """
    texts = [doc.page_content for doc in documents]
    embeddings = embedding_model.encode(texts, show_progress_bar=True)
    logging.info("Generated embeddings for all documents.")

    # Process in batches
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_embeddings = embeddings[i:i + batch_size]

        vectors = []
        for doc, embedding in zip(batch_docs, batch_embeddings):
            vector = {
                "id": f"chunk_{doc.metadata['chunk_index']}",
                "values": embedding.tolist(),
                "metadata": {
                    "text": doc.page_content,
                    "chunk_index": doc.metadata["chunk_index"]
                }
            }
            vectors.append(vector)

        try:
            upsert_response = index.upsert(vectors=vectors)
            logging.info(f"Upserted batch {i // batch_size + 1} with {len(vectors)} vectors")
        except Exception as e:
            logging.error(f"Failed to upsert batch {i // batch_size + 1}: {str(e)}")
            # Optionally: retry with smaller batch size or implement backoff

    return {"status": "completed", "total_vectors": len(documents)}

if __name__ == "__main__":
    cleaned_file = get_input_path()  # Only changed this line
    if not os.path.exists(cleaned_file):
        logging.error(f"File {cleaned_file} does not exist.")
        exit(1)

    chunks = split_text_into_overlapping_chunks(cleaned_file, max_chunk_chars=2000, overlap_chars=400)
    documents = create_documents(chunks)
    response = embed_and_upsert_documents(documents)
    logging.info(f"Pinecone upsert response: {response}")