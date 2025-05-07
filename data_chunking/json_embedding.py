import os
import json
import logging
from typing import List, Dict, Optional
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
from configparser import ConfigParser
from pinecone import Pinecone, ServerlessSpec
from transformers import AutoTokenizer
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


class JSONProcessor:
    def __init__(self, max_tokens: int = 2000):
        self.max_tokens = max_tokens
        self.tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")

    def count_tokens(self, text: str) -> int:
        """Count tokens using proper tokenizer"""
        return len(self.tokenizer.tokenize(text))

    def process_simple_format(self, data: List[Dict], file_path: str) -> List[Dict]:
        """Process simple format with name/url structure"""
        chunks = []
        current_chunk = []
        current_token_count = 0

        for item in data:
            text = f"Program: {item['name']}\nURL: {item['url']}"
            tokens = self.count_tokens(text)

            if current_token_count + tokens > self.max_tokens and current_chunk:
                chunks.append({
                    "text": "\n".join(current_chunk),
                    "metadata": {
                        "source": file_path,
                        "type": "program_link"
                    }
                })
                current_chunk = []
                current_token_count = 0

            current_chunk.append(text)
            current_token_count += tokens

        if current_chunk:
            chunks.append({
                "text": "\n".join(current_chunk),
                "metadata": {
                    "source": file_path,
                    "type": "program_link"
                }
            })

        return chunks

    def process_complex_format(self, data: List[Dict], file_path: str, metadata_fields: Optional[List[str]]) -> List[
        Dict]:
        """Process complex program description format"""
        chunks = []

        for item in data:
            metadata = {
                "source": file_path,
                "type": "program_description"
            }

            if metadata_fields:
                for field in metadata_fields:
                    if field in item:
                        metadata[field] = item[field]

            for field in ['degreelevel', 'program_name']:
                if field in item and field not in metadata:
                    metadata[field] = item[field]

            sections = []
            for key, value in item.items():
                if key in metadata:
                    continue

                if isinstance(value, list):
                    section_text = f"{key}:\n" + "\n".join([str(v) for v in value if v])
                    sections.append(section_text)
                elif value:
                    sections.append(f"{key}: {value}")

            full_text = "\n\n".join(sections)
            tokens = self.count_tokens(full_text)

            if tokens > self.max_tokens:
                for section in sections:
                    section_tokens = self.count_tokens(section)
                    if section_tokens > self.max_tokens:
                        sentences = section.split('. ')
                        current_section = []
                        current_section_tokens = 0

                        for sentence in sentences:
                            sentence = sentence.strip()
                            if not sentence:
                                continue

                            sentence_tokens = self.count_tokens(sentence)

                            if current_section_tokens + sentence_tokens > self.max_tokens and current_section:
                                chunks.append({
                                    "text": ". ".join(current_section) + ".",
                                    "metadata": metadata
                                })
                                current_section = []
                                current_section_tokens = 0

                            current_section.append(sentence)
                            current_section_tokens += sentence_tokens

                        if current_section:
                            chunks.append({
                                "text": ". ".join(current_section) + ".",
                                "metadata": metadata
                            })
                    else:
                        chunks.append({
                            "text": section,
                            "metadata": metadata
                        })
            else:
                chunks.append({
                    "text": full_text,
                    "metadata": metadata
                })

        return chunks

    def process_file(self, file_path: str, metadata_fields: Optional[List[str]] = None) -> List[Dict]:
        """Process a JSON file and return chunks"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = [data]

            return self.process_complex_format(data, file_path, metadata_fields)

        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
            return []


def embed_and_upsert(
        chunks: List[Dict],
        batch_size: int = 100
) -> None:
    """Embed chunks and upsert to Pinecone in batches"""
    for i in tqdm(range(0, len(chunks), batch_size), desc="Processing batches"):
        batch = chunks[i:i + batch_size]

        texts = [chunk["text"] for chunk in batch]
        embeddings = embedding_model.encode(texts, show_progress_bar=False)

        vectors = []
        for j, (chunk, embedding) in enumerate(zip(batch, embeddings)):
            content_hash = hash(chunk["text"])
            vectors.append({
                "id": f"{chunk['metadata']['source']}_{content_hash}_{i + j}",
                "values": embedding.tolist(),
                "metadata": chunk["metadata"]
            })

        try:
            index.upsert(vectors=vectors)
            logger.info(f"Upserted batch {i // batch_size + 1}")
        except Exception as e:
            logger.error(f"Error upserting batch: {str(e)}")


def get_input_path(filename: str) -> str:
    """Resolve input file path for both local and GitHub environments"""
    local_path = Path("../scraped_data") / filename
    github_path = Path(__file__).parent.parent / "scraped_data" / filename

    if local_path.exists():
        return str(local_path)
    elif github_path.exists():
        return str(github_path)
    else:
        logger.error(f"Could not find input file: {filename} in either location:")
        logger.error(f"Local path: {local_path}")
        logger.error(f"GitHub path: {github_path}")
        exit(1)

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


def process_all_jsons(metadata_fields: Optional[List[str]] = None) -> None:
    """Process all JSON files and upsert to Pinecone"""
    processor = JSONProcessor(max_tokens=2000)
    all_chunks = []

    json_files = [
        "utd_programs_links.json",
        "cleaned_programs_data.json"
    ]

    for filename in tqdm(json_files, desc="Processing JSON files"):
        if "links" in filename:
            file_path = get_input_path(filename)
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    data = [data]
                chunks = processor.process_simple_format(data, file_path)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")
        elif "data" in filename:
            file_path = get_processed_path(filename)
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                continue
            chunks = processor.process_file(file_path, metadata_fields)
            all_chunks.extend(chunks)
        else:
            logger.warning(f"Skipping unknown file: {filename}")

    if not all_chunks:
        logger.warning("No valid chunks found to process")
        return

    logger.info(f"Processed {len(all_chunks)} chunks")
    embed_and_upsert(all_chunks)


if __name__ == "__main__":
    # Metadata fields to preserve
    metadata_fields = ["name", "url", "degreelevel", "program_name"]

    process_all_jsons(metadata_fields)
    logger.info("JSON processing and embedding complete")