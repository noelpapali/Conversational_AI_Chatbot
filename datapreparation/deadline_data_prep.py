import pandas as pd
import os
from pathlib import Path
import logging


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
    logging.info(f"Starting deadlines data prep in {'GitHub Actions' if is_github else 'local'} environment")


    # Set up environment-aware paths
    BASE_DIR = Path(__file__).parent.parent

    # Input/output configuration
    INPUT_FOLDER = BASE_DIR / "tables"
    OUTPUT_DIR = BASE_DIR / ("processed_data_git" if is_github else "processed_data")
    OUTPUT_FILE = OUTPUT_DIR / "Financial_aid_deadlines_table.csv"

    # List of CSV files to process
    CSV_FILES = [
        "fall_2024_and_spring_2025financial_aid_priority_deadline_1.csv",
        "fall_2025_and_spring_2026financial_aid_priority_deadline_2.csv",
        "summer_2025_financial_aid_prioritydeadline_3.csv",
        "summer_2026_financial_aid_prioritydeadline_4.csv"
    ]

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Read and preprocess each table
        dfs = []
        for csv_file in CSV_FILES:
            file_path = INPUT_FOLDER / csv_file
            if not file_path.exists():
                logging.error(f"Input file not found: {file_path}")
                continue

            df = pd.read_csv(file_path)
            df["DETAILS"] = csv_file.replace(".csv", "")  # Remove .csv
            dfs.append(df)
            logging.info(f"Processed: {csv_file}")

        if not dfs:
            logging.error("No valid CSV files found to process")
            exit(1)

        # Combine all DataFrames
        deadlines_df = pd.concat(dfs, ignore_index=True)

        # Convert date columns to consistent format
        if "Date" in deadlines_df.columns:
            deadlines_df["Date"] = pd.to_datetime(
                deadlines_df["Date"],
                errors='coerce'
            ).dt.strftime('%m/%d/%Y')

        # Save the combined DataFrame
        deadlines_df.to_csv(OUTPUT_FILE, index=False)
        logging.info(f"Successfully saved processed data to {OUTPUT_FILE}")
        logging.info(f"Total records processed: {len(deadlines_df)}")


    except Exception as e:
        logging.error(f"Error processing files: {str(e)}")
        exit(1)


def preprocess_table(file_path: Path) -> pd.DataFrame:
    """
    Read and preprocess a single CSV file

    Args:
        file_path: Path to the CSV file

    Returns:
        Processed DataFrame with added DETAILS column
    """
    df = pd.read_csv(file_path)
    df["DETAILS"] = file_path.name.replace(".csv", "")
    return df


if __name__ == "__main__":
    main()