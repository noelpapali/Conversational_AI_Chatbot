import os
import json
import logging
from configparser import ConfigParser
from typing import Dict, Any

# Configure logging using your custom function
# configure_logging(log_file="scraping.log", log_level=logging.INFO)

# Load configuration from config.ini if needed
config = ConfigParser()
config.read('config.ini')


def clean_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively clean JSON data by removing empty strings from arrays.

    Args:
        data: The JSON data to clean (as a dictionary)

    Returns:
        The cleaned JSON data
    """
    if isinstance(data, dict):
        for key, value in list(data.items()):
            if isinstance(value, list):
                # Remove empty strings from arrays
                cleaned_list = [item for item in value if item != ""]
                if len(cleaned_list) > 0:
                    data[key] = cleaned_list
                else:
                    del data[key]
            else:
                data[key] = clean_json_data(value)
    elif isinstance(data, list):
        data = [clean_json_data(item) for item in data if item != ""]
    return data


def clean_json_file(input_filename: str, output_filename: str) -> None:
    """
    Clean a JSON file by removing empty strings from arrays.

    Args:
        input_filename: Path to the input JSON file
        output_filename: Path to save the cleaned JSON file
    """
    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cleaned_data = clean_json_data(data)

        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

        logging.info(f"Successfully cleaned JSON file. Output saved to {output_filename}")
    except Exception as e:
        logging.error(f"Error cleaning JSON file: {str(e)}")
        raise


if __name__ == "__main__":
    input_filename = "../scraped_data/utd_programs_data.json"  # Change to your input JSON file
    output_filename = "../processed_data/cleaned_programs_data.json"  # Change to your output file

    if os.path.exists(input_filename):
        logging.info(f"Starting cleaning process for {input_filename}.")
        clean_json_file(input_filename, output_filename)
    else:
        logging.error(f"Input file {input_filename} does not exist.")