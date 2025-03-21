import os
import csv
import json

# Directory and file paths
output_dir = "../scraped_data"  # Update this path if necessary
text_output_file = os.path.join(output_dir, "tuition_rates_content.txt")
csv_output_file = os.path.join(output_dir, "tuition_rates_table.csv")
merged_output_file = os.path.join(output_dir, "tuition_rates.txt")  # New merged output file


def csv_to_json(csv_file):
    """Convert a CSV file to JSON format."""
    try:
        with open(csv_file, 'r', encoding='utf-8') as csv_file:
            # Read the CSV file
            csv_reader = csv.DictReader(csv_file)
            # Convert to a list of dictionaries
            json_data = [row for row in csv_reader]
            return json_data
    except Exception as e:
        print(f"Error converting CSV to JSON: {e}")
        return None


def merge_files(txt_file, json_data, merged_file):
    """Merge the contents of a text file and JSON data into a single file."""
    try:
        # Read the text file
        with open(txt_file, 'r', encoding='utf-8') as txt:
            text_content = txt.read()

        # Convert JSON data to a formatted string
        json_content = json.dumps(json_data, indent=4)

        # Combine the contents
        merged_content = f"Text Content:\n{text_content}\n\nTable Content (JSON):\n{json_content}"

        # Write the merged content to a new file
        with open(merged_file, 'w', encoding='utf-8') as merged:
            merged.write(merged_content)

        print(f"Merged content saved to '{merged_file}'.")
    except Exception as e:
        print(f"Error merging files: {e}")


if __name__ == "__main__":
    # Convert CSV to JSON
    json_data = csv_to_json(csv_output_file)
    if json_data:
        # Merge the text file and JSON data
        merge_files(text_output_file, json_data, merged_output_file)