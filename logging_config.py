import logging


def configure_logging(log_file="scraping.log", log_level=logging.INFO):

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),  # Save logs to a file
            logging.StreamHandler()  # Print logs to the console
        ]
    )
    logging.info("Logging configured successfully.")