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
        dest_dir: Path,
        overwrite: bool = False
) -> int:
    """
    Copy specific CSV file(s) to destination directory

    Args:
        source_files: Single file path or list of file paths to copy
        dest_dir: Destination directory path (as Path object)
        overwrite: Whether to overwrite existing files (default: False)

    Returns:
        Number of files successfully copied
    """
    # Convert single file to list for uniform processing
    if isinstance(source_files, str):
        source_files = [source_files]

    dest_dir.mkdir(parents=True, exist_ok=True)
    copied_count = 0

    for source_file in source_files:
        source_path = Path(source_file)

        if not source_path.exists():
            logging.error(f"Source file not found: {source_file}")
            continue

        if source_path.suffix.lower() != '.csv':
            logging.warning(f"Skipping non-CSV file: {source_file}")
            continue

        dest_file = dest_dir / source_path.name

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
    is_github = os.getenv('GITHUB_ACTIONS') == 'true'
    logging.info(f"Starting csv copy etl in {'GitHub Actions' if is_github else 'local'} environment")

    # Base configuration
    BASE_DIR = Path(__file__).parent.parent
    INPUT_DIR = BASE_DIR / "scraped_data"

    # Environment-aware output directory
    OUTPUT_DIR = BASE_DIR / ("processed_data_git" if is_github else "processed_data")

    # Files to process (using relative paths from input directory)
    CSV_FILES_TO_COPY = [
        INPUT_DIR / "Scholarship_Listings.csv"
        # Add more files as needed
    ]

    OVERWRITE_EXISTING = False

    # Verify input files exist
    missing_files = [str(f) for f in CSV_FILES_TO_COPY if not f.exists()]
    if missing_files:
        logging.error(f"Missing input files: {', '.join(missing_files)}")
        exit(1)

    # Process files
    num_copied = copy_specific_csvs(CSV_FILES_TO_COPY, OUTPUT_DIR, OVERWRITE_EXISTING)

    if num_copied == len(CSV_FILES_TO_COPY):
        logging.info(f"Success! All {num_copied} files copied to {OUTPUT_DIR}")
    else:
        logging.warning(f"Partial success. Copied {num_copied}/{len(CSV_FILES_TO_COPY)} files to {OUTPUT_DIR}")
        exit(1)