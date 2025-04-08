import os
import subprocess
import logging
from configparser import ConfigParser

# Import the logging configuration function from your logging_config module
from logging_config import configure_logging

# Configure logging with a specified log file and log level
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration from config.ini (if needed for further configuration)
config = ConfigParser()
config.read('config.ini')


def clone_repo(repo_url, clone_dir):
    """
    Clones the repository if the directory does not already exist.
    """
    if not os.path.exists(clone_dir):
        logging.info(f"Cloning repository from {repo_url}...")
        result = subprocess.run(["git", "clone", repo_url], capture_output=True, text=True)
        if result.returncode != 0:
            logging.error("Error cloning repository:")
            logging.error(result.stderr)
            return False
        logging.info("Repository cloned successfully.")
    else:
        logging.info("Repository already cloned.")
    return True


def merge_text_files(input_dir, output_file):
    """
    Reads all .txt files in input_dir (including subdirectories) and writes their contents
    to output_file.
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as outfile:
            # Walk through all subdirectories of input_dir
            for root, dirs, files in os.walk(input_dir):
                for file in files:
                    if file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        logging.info(f"Reading {file_path}...")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                outfile.write(infile.read())
                                outfile.write("\n")  # Optional: add a newline between files
                        except Exception as e:
                            logging.error(f"Error reading file {file_path}: {e}")
        logging.info(f"All text files have been merged into {output_file}.")
    except Exception as e:
        logging.error(f"Error writing to output file {output_file}: {e}")


if __name__ == "__main__":
    # Repository information
    repo_url = "https://github.com/PavanChandan29/chatbot.git"
    clone_dir = "chatbot"
    scraped_data_dir = os.path.join(clone_dir, "scraped_data")
    output_file = "../processed_data/merged_text.txt"

    # Clone the repository if not already cloned
    if clone_repo(repo_url, clone_dir):
        # Check if the scraped_data directory exists
        if os.path.exists(scraped_data_dir):
            merge_text_files(scraped_data_dir, output_file)
        else:
            logging.error(f"The directory {scraped_data_dir} does not exist.")
