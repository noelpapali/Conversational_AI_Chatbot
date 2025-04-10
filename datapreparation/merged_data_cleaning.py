import os
import re
import logging
from configparser import ConfigParser
from logging_config import configure_logging

# Configure logging using your custom function
configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration from config.ini if needed
config = ConfigParser()
config.read('config.ini')


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
            for line_number, line in enumerate(infile, start=1):
                cleaned_line = clean_text_line(line)
                if cleaned_line:
                    outfile.write(cleaned_line + "\n")
                else:
                    logging.info(f"Line {line_number} is empty after cleaning and was skipped.")
        logging.info(f"Cleaned text has been written to {output_file}.")
    except Exception as e:
        logging.error(f"Error cleaning file {input_file}: {e}")


if __name__ == "__main__":
    input_filename = "../processed_data/merged_text.txt"
    output_filename = "../processed_data/cleaned_merged_text.txt"

    if os.path.exists(input_filename):
        logging.info(f"Starting cleaning process for {input_filename}.")
        clean_text_file(input_filename, output_filename)
    else:
        logging.error(f"Input file {input_filename} does not exist.")
