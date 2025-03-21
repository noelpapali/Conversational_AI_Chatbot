import re
import os
import logging
from configparser import ConfigParser
from logging_config import configure_logging

# Configure logging
configure_logging(log_file="scraping.log", log_level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = ConfigParser()
config.read('config.ini')


# Function to remove unwanted tags and clean descriptions **AFTER** extraction
def clean_text(text):
    """
    Cleans text by removing unwanted prefixes like 'Paragraph:', 'List:', etc.
    """
    original_text = text  # Keep track of original text for debugging

    # Remove leading dashes or bullet points
    text = re.sub(r'^\s*-\s*', '', text, flags=re.MULTILINE)

    # Ensure clean spacing and remove redundant line breaks
    #text = re.sub(r'\s+', ' ', text).strip()

    # Debugging
    if text != original_text:
        logger.info(f"Cleaned text: {original_text} -> {text}")
        print(f"Before: {original_text}\nAfter: {text}\n{'-' * 50}")

    return text if text else None  # Return None if empty after cleaning


# Function to process scraped data
def preprocess_data(file_path):
    """
    Processes and extracts structured data from a text file with URLs and descriptions.

    Args:
        file_path (str): Path to the input file.

    Returns:
        list: Processed data containing name, description, and URL.
    """
    if not os.path.exists(file_path):
        logger.error(f"Error: File '{file_path}' not found!")
        return []

    logger.info(f"Processing file: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()

    sections = content.split('URL: ')[1:]  # Skip the first empty split
    processed_data = []

    for section in sections:
        lines = section.strip().split('\n')
        if not lines:
            continue

        url = lines[0].strip()  # First line is the URL
        section_content = '\n'.join(lines[1:])  # The rest is content

        paragraphs = list(set(section_content.split('\n\n')))
        logger.info(f"Found {len(paragraphs)} paragraphs in section: {url}")

        # Collect raw paragraphs first (DO NOT clean yet)
        raw_paragraphs = [para.strip() for para in paragraphs if para.strip()]

        items = []
        for para in raw_paragraphs:
            if para and ':' in para and not para.startswith('http'):
                name, description = map(str.strip, para.split(':', 1))

                if name.lower() in ['wideblocks', 'tabs', 'smallblocks']:
                    logger.info(f"Skipping section: {name}")
                    continue

                if description:
                    items.append({
                        'name': name,
                        'description': description,
                        'url': url
                    })

        processed_data.extend(items)

    # **Apply cleaning at the very end**
    for item in processed_data:
        # Clean the name
        item['name'] = re.sub(
            r'\b(?: Paragraph:| List:|Wideblocks:|Tabs:|Smallblocks:)\b\s*',
            '',
            item['name'],
            flags=re.IGNORECASE
        ).strip()

        # Clean the description
        item['description'] = re.sub(
            r'\b(?: Paragraph:| List:|Wideblocks:|Tabs:|Smallblocks:)\b\s*',
            '',
            item['description'],
            flags=re.IGNORECASE
        ).strip()

    logger.info(f"Finished processing file: {file_path}. Total records: {len(processed_data)}")
    return processed_data


# Wrapper functions
def preprocess_certificates(file_path):
    return preprocess_data(file_path)


def preprocess_exec_ed(file_path):
    return preprocess_data(file_path)


# Function to save structured data to a text file
def save_to_txt(data, output_path):
    """
    Saves structured data to a text file.

    Args:
        data (list or dict): The data to be saved.
        output_path (str): Path of the output file.
    """
    logger.info(f"Saving data to {output_path}")

    with open(output_path, 'w', encoding='utf-8') as file:
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    if not item.get('description'):
                        continue
                    for key, value in item.items():
                        file.write(f"{key}: {value}\n")
                    file.write("\n")
        elif isinstance(data, dict):
            for key, value in data.items():
                file.write(f"{key}:\n")
                for item in value:
                    if isinstance(item, dict):
                        if not item.get('description'):
                            continue
                        for subkey, subvalue in item.items():
                            file.write(f"  {subkey}: {subvalue}\n")
                    file.write("\n")

    logger.info(f"Data successfully saved to {output_path}")


# File paths
certificates_file = '../scraped_data/certificate_programs_data.txt'
exec_ed_file = '../scraped_data/exec_ed_data.txt'

# Preprocess the files
certificates_data = preprocess_certificates(certificates_file)
exec_ed_data = preprocess_exec_ed(exec_ed_file)

# Merge the data
merged_data = {
    'Certificate Programs at the Jindal School of Management (JSOM) ': certificates_data,
    'Executive Education at UT Dallas': exec_ed_data
}

# Save cleaned data
output_directory = '../processed_data'
os.makedirs(output_directory, exist_ok=True)

save_to_txt(certificates_data, os.path.join(output_directory, 'certificate_prgs_cleaned.txt'))
save_to_txt(exec_ed_data, os.path.join(output_directory, 'exec_ed_cleaned.txt'))
save_to_txt(merged_data, os.path.join(output_directory, 'cerprgs_execed_merged.txt'))

logger.info("Data preprocessing and saving completed successfully!")
