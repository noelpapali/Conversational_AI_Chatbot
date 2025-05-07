import logging
import os
import csv
import json
import logging
from pathlib import Path


def configure_logging():
    """Set up basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def main():
    """Main execution function with environment-aware paths"""
    # Set up environment-aware paths
    configure_logging()
    BASE_DIR = Path(__file__).parent.parent
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'

    logging.info(f"Running in {'GitHub Actions' if is_github else 'local'} environment")

    # Input/output configuration
    OUTPUT_DIR = BASE_DIR / ("scraped_data_git" if is_github else "scraped_data")
    TEXT_OUTPUT_FILE = OUTPUT_DIR / "tuition_rates_content.txt"
    CSV_OUTPUT_FILE = OUTPUT_DIR / "tuition_rates_table.csv"
    MERGED_OUTPUT_FILE = OUTPUT_DIR / "tuition_rates.txt"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Convert CSV to JSON
    json_data = csv_to_json(CSV_OUTPUT_FILE)
    if json_data:
        # Merge the text file and JSON data
        merge_files(TEXT_OUTPUT_FILE, json_data, MERGED_OUTPUT_FILE)


def csv_to_json(csv_file: Path):
    """Convert a CSV file to JSON format.

    Args:
        csv_file: Path to the CSV file

    Returns:
        List of dictionaries representing the CSV data, or None if conversion fails
    """
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            csv_reader = csv.DictReader(f)
            return [row for row in csv_reader]
    except Exception as e:
        print(f"Error converting CSV to JSON: {e}")
        return None


def merge_files(txt_file: Path, json_data: list, merged_file: Path) -> None:
    """Merge the contents of a text file and JSON data into a single file.

    Args:
        txt_file: Path to the text file
        json_data: JSON data to merge
        merged_file: Path for the merged output file
    """
    try:
        # Read the text file
        with open(txt_file, 'r', encoding='utf-8') as f:
            text_content = f.read()

        # Convert JSON data to a formatted string
        json_content = json.dumps(json_data, indent=4)

        # Combine the contents
        merged_content = f"Text Content:\n{text_content}\n\nTable Content (JSON):\n{json_content}"

        # Write the merged content
        with open(merged_file, 'w', encoding='utf-8') as f:
            f.write(merged_content)

        print(f"Successfully merged files to: {merged_file}")
    except Exception as e:
        print(f"Error merging files: {e}")


if __name__ == "__main__":
    main()