import os
import logging
import numpy as np
from transformers import AutoTokenizer, AutoModel
from configparser import ConfigParser
from logging_config import configure_logging  # Ensure this module is available

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = ConfigParser()
config.read('config.ini')

# Function to chunk text
def chunk_text(text, chunk_size=512):
    """
    Splits the text into chunks of a specified size.
    """
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size)]
    return chunks

# Function to get embeddings
def get_embeddings(text_chunks, tokenizer, model):
    """
    Generates embeddings for a list of text chunks using a pre-trained model.
    """
    embeddings = []
    for chunk in text_chunks:
        inputs = tokenizer(chunk, return_tensors='pt', max_length=512, truncation=True)
        outputs = model(**inputs)
        embeddings.append(outputs.last_hidden_state.mean(dim=1).detach().numpy()[0])
    return np.array(embeddings)

# Load and process the merged text data
def load_and_process_data(file_path):
    """
    Loads the merged text data from a file and processes it.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
        all_text = [line.strip() for line in lines if line.strip()]
        return ' '.join(all_text)
    except Exception as e:
        logger.error(f"Error loading and processing data: {e}")
        raise

# Main function to handle text chunking and embedding
def main():
    try:
        # Load file paths from configuration
        merged_file = config.get('Paths', 'merged_file', fallback='../processed_data/cerprgs_execed_merged.txt')
        output_directory = config.get('Paths', 'output_directory', fallback='../chunked_data')

        # Ensure output directory exists
        os.makedirs(output_directory, exist_ok=True)

        # Load and process the merged text data
        merged_text = load_and_process_data(merged_file)

        # Text chunking
        text_chunks = chunk_text(merged_text, chunk_size=512)
        logger.info(f"Number of text chunks: {len(text_chunks)}")

        # Load model and tokenizer
        tokenizer = AutoTokenizer.from_pretrained('bert-base-uncased')
        model = AutoModel.from_pretrained('bert-base-uncased')

        # Text embedding
        embeddings = get_embeddings(text_chunks, tokenizer, model)
        logger.info(f"Embeddings shape: {embeddings.shape}")

        # Save embeddings to a file
        embeddings_file = os.path.join(output_directory, 'cerprgs_execed_embeddings.npy')
        np.save(embeddings_file, embeddings)
        logger.info(f"Embeddings saved to {embeddings_file}")

    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()