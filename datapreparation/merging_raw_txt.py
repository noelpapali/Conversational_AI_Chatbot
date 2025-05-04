import os
import subprocess
import logging
from configparser import ConfigParser

# Configure console-only logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

config = ConfigParser()
config.read('config.ini')


def clone_repo(repo_url, clone_dir):
    """GitHub-only clone function"""
    logging.info(f"Cloning {repo_url}...")
    result = subprocess.run(["git", "clone", repo_url], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Clone failed: {result.stderr}")
        return False
    logging.info(f"Repository cloned to {clone_dir}")
    return True


def merge_text_files(input_dir, output_file):
    """Merge all .txt files with console progress"""
    logging.info(f"Merging files from {os.path.abspath(input_dir)}")
    file_count = 0

    try:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.endswith('.txt'):
                        file_path = os.path.join(root, file)
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                outfile.write(infile.read() + "\n")
                                file_count += 1
                                logging.debug(f"Added: {file}")  # Only shows with DEBUG level
                        except Exception as e:
                            logging.warning(f"Skipped {file}: {str(e)}")

        logging.info(f"Success! Merged {file_count} files into {output_file}")
        return True
    except Exception as e:
        logging.error(f"Merge failed: {str(e)}")
        return False


if __name__ == "__main__":
    # Configuration
    PATHS = {
        'local_data': "../scraped_data",
        'repo_url': "https://github.com/PavanChandan29/chatbot.git",
        'clone_dir': "chatbot",
        'output': "../processed_data/merged_text.txt"
    }

    # Execution flow
    if os.path.exists(PATHS['local_data']):
        logging.info("LOCAL MODE: Using existing data")
        merge_text_files(PATHS['local_data'], PATHS['output'])
    else:
        logging.info("GITHUB MODE: Requires clone")
        if clone_repo(PATHS['repo_url'], PATHS['clone_dir']):
            repo_data = os.path.join(PATHS['clone_dir'], "scraped_data")
            if os.path.exists(repo_data):
                merge_text_files(repo_data, PATHS['output'])
            else:
                logging.error(f"Missing directory in repo: {repo_data}")
                exit(1)

    logging.info("Process completed")