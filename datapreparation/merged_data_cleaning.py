import os
import re
import logging
from pathlib import Path
from configparser import ConfigParser
from logging_config import configure_logging

def configure_logging():
    """Set up basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def main():
    """Main execution function with environment-aware paths"""
    # Configure logging
    configure_logging()
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'
    logging.info(f"Starting cleaning merged text files in {'GitHub Actions' if is_github else 'local'} environment")

    # Load configuration if needed
    config = ConfigParser()
    config.read('config.ini')

    # Set up environment-aware paths
    BASE_DIR = Path(__file__).parent.parent
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'

    # Input/output configuration
    INPUT_FILE = BASE_DIR / "processed_data/merged_text.txt"
    OUTPUT_DIR = BASE_DIR / ("processed_data_git" if is_github else "processed_data")
    OUTPUT_FILE = OUTPUT_DIR / "cleaned_merged_text.txt"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        logging.error(f"Input file not found: {INPUT_FILE}")
        exit(1)

    logging.info(f"Starting cleaning process from {INPUT_FILE} to {OUTPUT_FILE}")
    clean_text_file(INPUT_FILE, OUTPUT_FILE)
    logging.info(f"Successfully cleaned text saved to {OUTPUT_FILE}")


def clean_text_line(line):
    """
    Clean a single line of text by:
      - Removing occurrences of "[NBSP]".
      - Removing specified tokens: wideblocks:, href:, smallblocks:, list:, paragraph:, Tabs:
      - Stripping extra whitespace.
    """
    if "Elements with class" in line:
        return ""

    # Replace non-breaking spaces (\u00A0) with a regular space
    cleaned_line = line.replace("\u00A0", " ")

    # Define a regex pattern for the tokens (case-insensitive)
    pattern = r"(wideblocks:|href:|smallblocks:|list:|paragraph:|Tabs:)"
    cleaned_line = re.sub(pattern, "", cleaned_line, flags=re.IGNORECASE)

    # Strip leading/trailing whitespace
    cleaned_line = cleaned_line.strip()

    return cleaned_line


def clean_text_file(input_file, output_file):
    """
    Reads the input file, cleans each line, and writes non-empty cleaned lines to the output file.
    Logs any empty lines or errors encountered.
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as infile, \
                open(output_file, 'w', encoding='utf-8') as outfile:

            empty_lines = 0
            total_lines = 0

            for line in infile:
                total_lines += 1
                cleaned_line = clean_text_line(line)
                if cleaned_line:
                    outfile.write(cleaned_line + "\n")
                else:
                    empty_lines += 1

            logging.info(f"Processed {total_lines} lines, removed {empty_lines} empty lines")

    except Exception as e:
        logging.error(f"Error cleaning file {input_file}: {e}")
        raise


if __name__ == "__main__":
    main()