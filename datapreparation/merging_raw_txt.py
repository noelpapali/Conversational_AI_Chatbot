import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)


def merge_text_files(input_dir, output_file):
    """Merge all .txt files with progress logging"""
    logging.info(f"Merging files from {input_dir.resolve()}")
    file_count = 0

    try:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as outfile:
            for root, _, files in os.walk(input_dir):
                for file in files:
                    if file.endswith('.txt'):
                        file_path = Path(root) / file
                        try:
                            with open(file_path, 'r', encoding='utf-8') as infile:
                                outfile.write(infile.read() + "\n")
                                file_count += 1
                                logging.debug(f"Added: {file}")
                        except Exception as e:
                            logging.warning(f"Skipped {file}: {str(e)}")

        logging.info(f"Success! Merged {file_count} files into {output_file}")
        return True
    except Exception as e:
        logging.error(f"Merge failed: {str(e)}")
        return False


if __name__ == "__main__":
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'
    logging.info(f"Starting merging text files in {'GitHub Actions' if is_github else 'local'} environment")
    # Base configuration
    BASE_DIR = Path(__file__).parent.parent
    INPUT_DIR = BASE_DIR / "scraped_data"

    # Environment detection
    OUTPUT_DIR = BASE_DIR / ("processed_data_git" if is_github else "processed_data")
    OUTPUT_FILE = OUTPUT_DIR / "merged_text.txt"

    # Ensure directories exist
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Process files
    if not INPUT_DIR.exists():
        logging.error(f"Input directory not found: {INPUT_DIR}")
        exit(1)

    if merge_text_files(INPUT_DIR, OUTPUT_FILE):
        logging.info(f"Processing complete. Output at: {OUTPUT_FILE}")
    else:
        exit(1)