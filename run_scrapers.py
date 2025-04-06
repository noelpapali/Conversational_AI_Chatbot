import importlib.util
import time
import sys
import shutil
import subprocess
import logging
import os
from datetime import datetime

# Set up logging
os.makedirs('scraper_logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'scraper_logs/run_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)
logger.info("Scraper started")


def ensure_chromedriver():
    """Ensure ChromeDriver is available in the expected location."""
    try:
        # Get the root directory of the repository
        root_dir = os.path.dirname(os.path.abspath(__file__))

        # Create chrome directory if it doesn't exist
        chrome_dir = os.path.join(root_dir, "chrome")
        if not os.path.exists(chrome_dir):
            os.makedirs(chrome_dir)
            logger.info(f"Created chrome directory at: {chrome_dir}")

        # Path where the chromedriver should be
        chrome_driver_path = os.path.join(chrome_dir, "chromedriver.exe")

        # Check if chromedriver already exists
        if os.path.exists(chrome_driver_path):
            logger.info(f"ChromeDriver already exists at: {chrome_driver_path}")
            return chrome_driver_path

        return chrome_driver_path
    except Exception as e:
        logger.error(f"Failed to setup ChromeDriver: {str(e)}", exc_info=True)
        return None


def import_module_from_file(file_path):
    """Import a module from file path."""
    module_name = os.path.basename(file_path).replace('.py', '')
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)

    # Add the directory containing the module to sys.path temporarily
    module_dir = os.path.dirname(file_path)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)

    spec.loader.exec_module(module)
    return module


def run_scraper(file_path, is_selenium_scraper=False):
    """Run a single scraper and handle exceptions."""
    file_name = os.path.basename(file_path)
    logger.info(f"Starting scraper: {file_name}")

    try:
        start_time = time.time()

        if is_selenium_scraper:
            # Run selenium scrapers in a separate process
            logger.info(f"Running Selenium scraper {file_name} in separate process")
            # Run the script in a separate process to isolate any WebDriver issues
            result = subprocess.run([sys.executable, file_path],
                                    capture_output=True,
                                    text=True,
                                    cwd=os.path.dirname(file_path))

            # Log the output from the subprocess
            if result.stdout:
                logger.info(f"Output from {file_name}:\n{result.stdout}")
            if result.stderr:
                logger.error(f"Errors from {file_name}:\n{result.stderr}")

            # Check if the subprocess was successful
            if result.returncode != 0:
                logger.error(f"Scraper {file_name} failed with return code {result.returncode}")
                return False
        else:
            # For non-selenium scrapers, import and run directly
            module = import_module_from_file(file_path)

            # Try to execute the main function if it exists
            if hasattr(module, 'main'):
                module.main()

        execution_time = time.time() - start_time
        logger.info(f"Completed scraper: {file_name} in {execution_time:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"Error in scraper {file_name}: {str(e)}", exc_info=True)
        return False


def run_all_scrapers():
    """Run all scrapers in the 'scraper' directory."""
    # Ensure ChromeDriver is available where the scrapers expect it
    ensure_chromedriver()

    # Get the path to the scraper directory from the root of the repo
    root_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_dir = os.path.join(root_dir, 'scraper')

    if not os.path.exists(scraper_dir):
        logger.error(f"Scraper directory not found: {scraper_dir}")
        return

    logger.info(f"Starting execution of all scrapers in: {scraper_dir}")

    # Get all Python files in the scraper directory
    py_files = [os.path.join(scraper_dir, f) for f in os.listdir(scraper_dir)
                if f.endswith('.py') and f != '__init__.py' and os.path.isfile(os.path.join(scraper_dir, f))]

    logger.info(f"Found {len(py_files)} scraper files")

    # Known selenium scrapers that need special handling
    selenium_scrapers = [
        "program_links_utd_s.py",
        "scholarship_data_s.py",
        "tuition_rates_content.py",
        "utd_programs_data_s.py"
    ]

    # Track success/failure
    results = {
        'total': len(py_files),
        'success': 0,
        'failed': 0,
        'failed_scrapers': []
    }

    # Run each scraper
    for file_path in py_files:
        file_name = os.path.basename(file_path)
        is_selenium_scraper = file_name in selenium_scrapers

        if is_selenium_scraper:
            logger.info(f"Identified {file_name} as a Selenium scraper")

        if run_scraper(file_path, is_selenium_scraper):
            results['success'] += 1
        else:
            results['failed'] += 1
            results['failed_scrapers'].append(file_name)

    # Log summary
    logger.info(f"Execution complete. Summary: {results['success']} succeeded, {results['failed']} failed")
    if results['failed'] > 0:
        logger.info(f"Failed scrapers: {', '.join(results['failed_scrapers'])}")

    return results


if __name__ == "__main__":
    run_all_scrapers()