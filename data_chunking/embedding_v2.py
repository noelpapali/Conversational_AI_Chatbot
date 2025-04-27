import os
import logging
import re
import pinecone
import spacy
from configparser import ConfigParser
from sentence_transformers import SentenceTransformer
from logging_config import configure_logging  # Assuming you have this file

# Configure logging using your custom function
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration from config.ini if needed
config = ConfigParser()
config.read('config.ini')

# Initialize the SentenceTransformer model
model_name = "all-MiniLM-L6-v2"
embedding_model = SentenceTransformer(model_name)
logging.info(f"Loaded embedding model: {model_name}")

# Pinecone configuration (replace with your actual key, environment, and index name)
PINECONE_API_KEY = "pcsk_6SHZxP_MazDP4PaSNokSMfNZvxeo37u4Y1j6KWYLPqj2jQysvLuLm7CbBuHnajYDaTanFA"  # Replace with your Pinecone API key
PINECONE_ENV = "us-east-1"           # e.g., "us-west1-gcp"
INDEX_NAME = "chatbotv2"               # Replace with your Pinecone index name

# Initialize Pinecone using the new interface
from pinecone import Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
# Check if the index exists
if INDEX_NAME not in pc.list_indexes().names():
    logging.error(f"Index '{INDEX_NAME}' not found in Pinecone.")
    exit(1)
# Connect to the index
index = pc.Index(INDEX_NAME)
logging.info(f"Connected to Pinecone index: {INDEX_NAME}")

# Load spaCy model for keyword extraction
nlp = spacy.load("en_core_web_sm")

def extract_subheading(chunk):
    """
    Extracts a subheading from a chunk if a pattern like "Heading:" exists.
    This function looks for a line starting with "Heading:".
    """
    match = re.search(r"Heading:\s*(.*)", chunk, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None

def extract_keywords(text, top_n=5):
    """
    Uses spaCy to extract keywords (noun chunks) from text.
    This is a simple heuristic; you can replace it with more advanced methods.
    """
    doc = nlp(text)
    noun_chunks = [chunk.text.strip() for chunk in doc.noun_chunks]
    unique_chunks = list(dict.fromkeys(noun_chunks))
    return unique_chunks[:top_n]

def enrich_metadata(chunk, chunk_index, filename=None):
    """
    Enriches metadata by extracting subheadings and keywords from the chunk,
    and optionally includes the filename.
    """
    metadata = {"text": chunk, "chunk_index": chunk_index}
    if filename:
        metadata["filename"] = filename
    subheading = extract_subheading(chunk)
    if subheading:
        metadata["subheading"] = subheading
    keywords = extract_keywords(chunk)
    if keywords:
        metadata["keywords"] = keywords
    return metadata

def split_text_into_chunks(text, max_chunk_chars=1000):
    """
    Splits the text into chunks based on paragraph boundaries.
    Each chunk is at most max_chunk_chars long; if a paragraph is too long,
    it can be further split (this example assumes paragraphs are within the limit).
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 1 > max_chunk_chars:
            chunks.append(current_chunk.strip())
            current_chunk = para
        else:
            current_chunk += " " + para
    if current_chunk:
        chunks.append(current_chunk.strip())
    logging.info(f"Split text into {len(chunks)} chunks.")
    return chunks

def embed_and_upsert_chunks(chunks, filename=None):
    """
    Generates embeddings for each chunk using the SentenceTransformer model,
    then upserts them into the Pinecone index with enriched metadata, including filename.
    """
    embeddings = embedding_model.encode(chunks, show_progress_bar=True)
    logging.info("Generated embeddings for all chunks.")

    vectors = []
    for i, embedding in enumerate(embeddings):
        metadata = enrich_metadata(chunks[i], i, filename=filename)
        vector = {
            "id": f"{filename.replace('.', '_')}_chunk_{i}" if filename else f"chunk_{i}",
            "values": embedding.tolist(),
            "metadata": metadata
        }
        vectors.append(vector)

    upsert_response = index.upsert(vectors=vectors)
    logging.info(f"Upserted {len(vectors)} vectors into Pinecone.")
    return upsert_response

def query_pinecone(query_text, top_k=5, filter=None):
    """
    Generates an embedding for the query text and queries the Pinecone index
    with an optional metadata filter.

    Args:
        query_text (str): The user's query.
        top_k (int): The number of top results to retrieve.
        filter (dict, optional): A dictionary to filter results based on metadata.
                                 Defaults to None (no filter).

    Returns:
        list: A list of Pinecone query matches with metadata.
    """
    query_embedding = embedding_model.encode([query_text])[0].tolist()
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter  # Pass the filter parameter to Pinecone
    )
    return results.matches

def process_user_query(user_query):
    """
    Example function to process a user query and apply potential filters.
    This is a basic example; you'll likely need more sophisticated logic.
    """
    filter = None
    if "heading:" in user_query.lower():
        extracted_heading = re.search(r"heading:\s*(.*)", user_query, re.IGNORECASE)
        if extracted_heading:
            filter = {"subheading": {"$eq": extracted_heading.group(1).strip()}}
            logging.info(f"Applying filter for subheading: {filter['subheading']['$eq']}")
    elif "from file" in user_query.lower():
        extracted_filename = re.search(r"from file\s*(.*)", user_query, re.IGNORECASE)
        if extracted_filename:
            filter = {"filename": {"$eq": extracted_filename.group(1).strip()}}
            logging.info(f"Applying filter for filename: {filter['filename']['$eq']}")
    elif "keyword" in user_query.lower():
        extracted_keyword = re.search(r"keyword\s*(.*)", user_query, re.IGNORECASE)
        if extracted_keyword:
            filter = {"keywords": {"$in": [extracted_keyword.group(1).strip()]}}
            logging.info(f"Applying filter for keyword: {filter['keywords']['$in']}")

    results = query_pinecone(user_query, filter=filter)
    logging.info(f"Query results: {results}")
    return results

if __name__ == "__main__":
    # --- Upserting Data (Example with a single merged file) ---
    cleaned_file = "../scraped_data/cleaned_merged_text.txt"
    if os.path.exists(cleaned_file):
        with open(cleaned_file, 'r', encoding='utf-8') as f:
            merged_text = f.read()
        chunks = split_text_into_chunks(merged_text, max_chunk_chars=1000)
        response = embed_and_upsert_chunks(chunks)
        logging.info(f"Pinecone upsert response (merged file): {response}")
    else:
        logging.warning(f"Cleaned merged file not found at {cleaned_file}. Skipping upsert example.")

    # --- Example Querying ---
    user_query1 = "What are the main concepts?"
    results1 = query_pinecone(user_query1)
    print(f"\nQuery 1 results: {results1}")

    user_query2 = "Tell me more about a specific heading: Introduction"
    results2 = process_user_query(user_query2)
    print(f"\nQuery 2 results (filtered by heading): {results2}")

    user_query3 = "What are some keywords related to this?"
    results3 = process_user_query(user_query3)
    print(f"\nQuery 3 results (potential keyword filter): {results3}")

    user_query4 = "Focus on information from file document1.txt"
    # To make this work, you would need to modify the upsert part to include the filename
    # and adjust the process_user_query function accordingly.
    # Assuming you've done that:
    results4 = process_user_query(user_query4)
    print(f"\nQuery 4 results (filtered by filename): {results4}")