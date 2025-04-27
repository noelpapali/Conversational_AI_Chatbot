import os
import logging
import pandas as pd
from typing import Optional


def configure_logging(log_level: int = logging.INFO) -> None:
    """Configure logging to console."""
    logger = logging.getLogger()
    logger.setLevel(log_level)
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)


def read_csv_with_flexible_columns(file_path: str) -> Optional[pd.DataFrame]:
    """
    Reads CSV file while handling inconsistent column counts.
    """
    try:
        return pd.read_csv(file_path, skip_blank_lines=False)
    except pd.errors.ParserError:
        try:
            logging.warning("Inconsistent columns detected. Using flexible parser.")
            with open(file_path, 'r') as f:
                lines = f.readlines()

            max_columns = max(len(line.split(',')) for line in lines if line.strip())

            return pd.read_csv(
                file_path,
                skip_blank_lines=False,
                header=None,
                names=[f"col_{i}" for i in range(max_columns)],
                on_bad_lines='skip'
            )
        except Exception as e:
            logging.error(f"Failed to read {file_path}. Error: {e}")
            return None


def clean_table(table: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the table by:
    1. Removing numbered columns (col_0, col_1, etc.)
    2. Keeping only columns with actual data
    3. Removing completely empty rows
    """
    # Remove columns with names like col_0, col_1, etc.
    data_columns = [col for col in table.columns if not str(col).startswith('col_')]

    # If no named columns found, keep only columns with data
    if not data_columns:
        data_columns = [col for col in table.columns if not table[col].isnull().all()]

    return table[data_columns].dropna(how='all')


def split_csv_by_tables(
        input_filename: str,
        output_directory: str,
        max_tables: int = 8
) -> None:
    """
    Processes CSV file to:
    1. Split into tables separated by empty rows
    2. Extract only first 8 tables
    3. Clean each table
    4. Save without headers
    """
    if not os.path.exists(input_filename):
        logging.error(f"Input file not found: {input_filename}")
        return

    os.makedirs(output_directory, exist_ok=True)

    df = read_csv_with_flexible_columns(input_filename)
    if df is None:
        return

    empty_rows = df.isnull().all(axis=1)
    table_start_indices = []
    prev_empty = True

    # Find where tables start (after empty rows)
    for idx, is_empty in enumerate(empty_rows):
        if is_empty:
            prev_empty = True
        else:
            if prev_empty:
                table_start_indices.append(idx)
            prev_empty = False

    # Process only first 8 tables
    for i, start_idx in enumerate(table_start_indices[:max_tables], 1):
        end_idx = None
        for j in range(start_idx, len(df)):
            if empty_rows[j]:
                end_idx = j
                break
        end_idx = end_idx if end_idx is not None else len(df)

        table = df.iloc[start_idx:end_idx]
        table = clean_table(table)

        if not table.empty:
            output_path = os.path.join(output_directory, f"table_{i}.csv")
            # Save without headers or index
            table.to_csv(output_path, index=False, header=False)
            logging.info(f"Saved Table {i} (rows {start_idx + 1}-{end_idx}) to {output_path}")
        else:
            logging.warning(f"Skipping empty table starting at row {start_idx + 1}")

    if len(table_start_indices) > max_tables:
        logging.info(f"Stopped after extracting first {max_tables} tables. "
                     f"{len(table_start_indices) - max_tables} additional tables remain.")


if __name__ == "__main__":
    configure_logging()

    # Use absolute paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_path = os.path.join(project_root, "scraped_data", "tuition_rates_table.csv")
    output_dir = os.path.join(project_root, "processed_data", "tuition_tables")

    split_csv_by_tables(
        input_path,
        output_dir,
        max_tables=8
    )