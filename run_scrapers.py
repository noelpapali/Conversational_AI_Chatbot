import os
import importlib.util
import logging

# Set up logging
logging.basicConfig(filename='scraper_job.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s: %(message)s')


def run_scrapers():
    scraper_folder = 'scraper'
    logging.info(f"Starting to run all scrapers in {scraper_folder}")

    for filename in os.listdir(scraper_folder):
        if filename.endswith('.py') and filename != '__init__.py':
            module_name = filename[:-3]  # Remove '.py' from filename
            module_path = os.path.join(scraper_folder, filename)

            logging.info(f"Attempting to run scraper: {module_name}")

            try:
                # Dynamically import the module
                spec = importlib.util.spec_from_file_location(module_name, module_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Assuming each scraper script has a main function
                if hasattr(module, 'main'):
                    module.main()
                    logging.info(f"Successfully executed: {module_name}")
                else:
                    logging.warning(f"No 'main' function found in {module_name}")
            except Exception as e:
                logging.error(f"Error running {module_name}: {e}")

    logging.info("Finished running all scrapers")


if __name__ == "__main__":
    run_scrapers()