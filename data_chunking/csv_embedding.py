import os
import logging
import pandas as pd
from tqdm import tqdm
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from configparser import ConfigParser
from pinecone import Pinecone, ServerlessSpec
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Detect environment
IS_GITHUB = os.getenv('GITHUB_ACTIONS') == 'true'

# Load configuration
config = ConfigParser()
if IS_GITHUB:
    config.read('config.ini')  # Assuming config.ini is in the same directory in GitHub
else:
    config.read('../config.ini')

# Initialize models and Pinecone
EMBEDDINGS_MODEL_NAME = config["embeddings"]["model_name"]
embedding_model = SentenceTransformer(EMBEDDINGS_MODEL_NAME)

pc = Pinecone(
    api_key=config["pinecone"]["api_key"],
    spec=ServerlessSpec(cloud='aws', region=config["pinecone"]["env"])
)
index_name = config["pinecone"]["index"]

if index_name not in pc.list_indexes().names():
    logger.error(f"Index '{index_name}' not found")
    exit(1)

index = pc.Index(index_name)

def find_csv_files(base_dir: str) -> List[str]:
    """Recursively find all CSV files in directory"""
    csv_files = []
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.csv'):
                csv_files.append(os.path.join(root, file))
    return csv_files

def dataframe_to_text(df: pd.DataFrame) -> str:
    """Convert DataFrame to formatted text without tabulate dependency"""
    try:
        # Try using markdown if tabulate is available
        return df.to_markdown(index=False)
    except ImportError:
        # Fallback to basic string representation
        return df.to_string(index=False)

def csv_to_text_chunks(
    csv_path: str,
    max_tokens: int = 2000,
    header_rows: int = 4
) -> List[Dict]:
    """
    Convert CSV to text chunks with:
    - First 4 rows included in every chunk
    - Subsequent rows chunked by token count
    """
    try:
        df = pd.read_csv(csv_path)
        chunks = []

        # Get header info (first 4 rows)
        header_text = dataframe_to_text(df.head(header_rows))

        # Process remaining rows in chunks
        remaining_rows = df.iloc[header_rows:]
        current_chunk = header_text
        chunk_id = 0

        for _, row in remaining_rows.iterrows():
            row_df = pd.DataFrame([row])
            row_text = dataframe_to_text(row_df)

            # Check if adding this row would exceed token limit
            if len(current_chunk.split()) + len(row_text.split()) > max_tokens:
                chunks.append({
                    "text": current_chunk,
                    "source": os.path.basename(csv_path),
                    "chunk_id": chunk_id
                })
                chunk_id += 1
                current_chunk = header_text  # Reset with header

            current_chunk += "\n" + row_text

        # Add the last chunk
        if current_chunk != header_text:
            chunks.append({
                "text": current_chunk,
                "source": os.path.basename(csv_path),
                "chunk_id": chunk_id
            })

        return chunks

    except Exception as e:
        logger.error(f"Error processing {csv_path}: {str(e)}")
        return []

def get_processed_path(filename: str) -> str:
    """Resolve processed file path for both local and GitHub environments"""
    local_path = Path("../processed_data") / filename
    github_path = Path(__file__).parent.parent / "processed_data" / filename

    if local_path.exists():
        return str(local_path)
    elif github_path.exists():
        return str(github_path)
    else:
        logger.error(f"Could not find processed file: {filename} in either location:")
        logger.error(f"Local path: {local_path}")
        logger.error(f"GitHub path: {github_path}")
        exit(1)

def process_all_csvs(batch_size: int = 100) -> None:
    """Process all CSVs in the processed_data directory"""
    all_chunks = []
    processed_dir = get_processed_path("")  # Get the processed_data directory path

    if not os.path.exists(processed_dir):
        logger.warning(f"Processed data directory not found: {processed_dir}")
        return

    csv_files = find_csv_files(processed_dir)

    if not csv_files:
        logger.warning(f"No CSV files found in: {processed_dir}")
        return

    logger.info(f"Found {len(csv_files)} CSV files to process in: {processed_dir}")

    # Process files and collect chunks
    for csv_file in tqdm(csv_files, desc="Processing CSVs"):
        chunks = csv_to_text_chunks(csv_file)
        all_chunks.extend(chunks)

    # Batch process embeddings and upsert
    for i in tqdm(range(0, len(all_chunks), batch_size), desc="Embedding and upserting"):
        batch = all_chunks[i:i + batch_size]
        texts = [item["text"] for item in batch]

        # Generate embeddings
        embeddings = embedding_model.encode(texts, show_progress_bar=False)

        # Prepare vectors
        vectors = []
        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            vectors.append({
                "id": f"{chunk['source']}_chunk_{chunk['chunk_id']}",
                "values": embedding.tolist(),
                "metadata": {
                    "text": chunk["text"],
                    "source": chunk["source"],
                    "chunk_id": chunk["chunk_id"],
                    "batch_index": i + j
                }
            })

        # Upsert to Pinecone
        try:
            index.upsert(vectors=vectors)
            logger.info(f"Upserted batch {i // batch_size + 1}")
        except Exception as e:
            logger.error(f"Error upserting batch: {str(e)}")

if __name__ == "__main__":
    # Install tabulate if not available
    try:
        import tabulate
    except ImportError:
        logger.info("Installing tabulate package for better table formatting...")
        import subprocess
        subprocess.check_call(["pip", "install", "tabulate"])
        import tabulate

    process_all_csvs()
    logger.info("CSV processing and embedding complete")