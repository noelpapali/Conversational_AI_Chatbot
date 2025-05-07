import os
import json
import logging
from pathlib import Path
from configparser import ConfigParser
from typing import Dict, Any


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
    logging.info(f"Starting utd_programs json cleaning in {'GitHub Actions' if is_github else 'local'} environment")


    # Load configuration if needed
    config = ConfigParser()
    config.read('config.ini')

    # Set up environment-aware paths
    BASE_DIR = Path(__file__).parent.parent

    # Input/output configuration
    INPUT_FILE = BASE_DIR / "scraped_data/utd_programs_data.json"
    OUTPUT_DIR = BASE_DIR / ("processed_data_git" if is_github else "processed_data")
    OUTPUT_FILE = OUTPUT_DIR / "cleaned_programs_data.json"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not INPUT_FILE.exists():
        logging.error(f"Input file not found: {INPUT_FILE}")
        exit(1)

    logging.info(f"Starting JSON cleaning from {INPUT_FILE} to {OUTPUT_FILE}")
    clean_json_file(INPUT_FILE, OUTPUT_FILE)
    logging.info(f"Successfully cleaned JSON saved to {OUTPUT_FILE}")


def clean_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively clean JSON data by:
    - Removing empty strings from arrays
    - Removing empty dictionaries
    - Preserving all other data structures

    Args:
        data: The JSON data to clean (as a dictionary)
    Returns:
        The cleaned JSON data
    """
    if isinstance(data, dict):
        for key, value in list(data.items()):
            cleaned_value = clean_json_data(value)
            if cleaned_value or cleaned_value is False or cleaned_value == 0:
                data[key] = cleaned_value
            else:
                del data[key]
        return data if data else None

    elif isinstance(data, list):
        cleaned_list = [clean_json_data(item) for item in data
                        if item != "" and item is not None]
        cleaned_list = [item for item in cleaned_list
                        if item or item is False or item == 0]
        return cleaned_list

    return data


def clean_json_file(input_file: Path, output_file: Path) -> None:
    """
    Clean a JSON file and save the cleaned version

    Args:
        input_file: Path to the input JSON file
        output_file: Path to save the cleaned JSON file
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        cleaned_data = clean_json_data(data)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(cleaned_data, f, indent=2, ensure_ascii=False)

    except Exception as e:
        logging.error(f"Error cleaning JSON file: {str(e)}")
        raise


if __name__ == "__main__":
    main()