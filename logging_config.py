# logging_config.py
import logging


def configure_logging(log_file: str, log_level: int = logging.INFO):
    """Configure logging with file and console handlers."""
    logging.basicConfig(level=log_level)

    # Clear any existing handlers
    logging.getLogger().handlers.clear()

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # File handler with UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Add handlers
    logging.getLogger().addHandler(file_handler)
    logging.getLogger().addHandler(console_handler)