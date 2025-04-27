import os
import shutil
from pathlib import Path
import logging
from typing import List, Union


def configure_logging():
    """Set up basic logging configuration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def copy_specific_csvs(
        source_files: Union[str, List[str]],
        dest_dir: str,
        overwrite: bool = False
) -> int:
    """
    Copy specific CSV file(s) to destination directory

    Args:
        source_files: Single file path or list of file paths to copy
        dest_dir: Destination directory path
        overwrite: Whether to overwrite existing files (default: False)

    Returns:
        Number of files successfully copied
    """
    # Convert single file to list for uniform processing
    if isinstance(source_files, str):
        source_files = [source_files]

    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)

    copied_count = 0

    for source_file in source_files:
        source_path = Path(source_file)

        if not source_path.exists():
            logging.error(f"Source file not found: {source_file}")
            continue

        if source_path.suffix.lower() != '.csv':
            logging.warning(f"Skipping non-CSV file: {source_file}")
            continue

        dest_file = dest_path / source_path.name

        if dest_file.exists() and not overwrite:
            logging.warning(f"Skipping {source_path.name} - already exists in destination")
            continue

        try:
            shutil.copy2(str(source_path), str(dest_file))
            copied_count += 1
            logging.info(f"Copied {source_path.name} to {dest_dir}")
        except Exception as e:
            logging.error(f"Failed to copy {source_path.name}: {str(e)}")

    return copied_count


if __name__ == "__main__":
    configure_logging()

    # Example usage - specify your exact files here:
    CSV_FILES_TO_COPY = [
        "../scraped_data/Scholarship_Listings.csv"
        # Add more files as needed
    ]

    DESTINATION_DIR = "../processed_data"
    OVERWRITE_EXISTING = False

    num_copied = copy_specific_csvs(CSV_FILES_TO_COPY, DESTINATION_DIR, OVERWRITE_EXISTING)
    logging.info(f"Operation complete. {num_copied}/{len(CSV_FILES_TO_COPY)} files copied successfully.")