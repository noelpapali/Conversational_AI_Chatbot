import importlib.util
import time
import sys
import shutil
import subprocess
import logging
import os
from datetime import datetime

# Configure environment detection
IS_GITHUB_ACTIONS = os.environ.get('GITHUB_ACTIONS') == 'true'
OUTPUT_BASE_DIR = "chatbot/scraped_data_git" if IS_GITHUB_ACTIONS else "../scraped_data"

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
logger.info(f"Scraper started in {'GitHub Actions' if IS_GITHUB_ACTIONS else 'local'} environment")


def ensure_output_directories():
    """Ensure all required output directories exist."""
    try:
        # Create main output directory
        os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
        logger.info(f"Output directory ready: {OUTPUT_BASE_DIR}")

        # Create subdirectories if needed
        subdirs = ["tables", "logs"]  # Add any other required subdirectories
        for subdir in subdirs:
            path = os.path.join(OUTPUT_BASE_DIR, subdir)
            os.makedirs(path, exist_ok=True)
            logger.info(f"Created subdirectory: {path}")

        return True
    except Exception as e:
        logger.error(f"Failed to create output directories: {str(e)}", exc_info=True)
        return False


def ensure_chromedriver():
    """Ensure ChromeDriver is available in the expected location."""
    try:
        # Get the root directory of the repository
        root_dir = os.path.dirname(os.path.abspath(__file__))

        # Create chrome directory if it doesn't exist
        chrome_dir = os.path.join(root_dir, "chrome")
        os.makedirs(chrome_dir, exist_ok=True)
        logger.info(f"Chrome directory ready: {chrome_dir}")

        # Path where the chromedriver should be
        chrome_driver_path = os.path.join(chrome_dir, "chromedriver.exe")

        # In GitHub Actions, we expect chromedriver to be installed system-wide
        if IS_GITHUB_ACTIONS:
            logger.info("Running in GitHub Actions - using system ChromeDriver")
            return "/usr/bin/chromedriver"  # Standard GitHub Actions location

        # For local development, check if chromedriver exists
        if os.path.exists(chrome_driver_path):
            logger.info(f"Using existing ChromeDriver at: {chrome_driver_path}")
            return chrome_driver_path

        logger.warning(f"ChromeDriver not found at: {chrome_driver_path}")
        return None
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
            # Set environment variables for Selenium scrapers
            env = os.environ.copy()
            if IS_GITHUB_ACTIONS:
                env["CHROME_PATH"] = "/usr/bin/chromium-browser"
                env["OUTPUT_DIR"] = OUTPUT_BASE_DIR

            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(file_path),
                env=env
            )

            if result.stdout:
                logger.info(f"Output from {file_name}:\n{result.stdout}")
            if result.stderr:
                logger.error(f"Errors from {file_name}:\n{result.stderr}")

            if result.returncode != 0:
                logger.error(f"Scraper {file_name} failed with return code {result.returncode}")
                return False
        else:
            # For non-selenium scrapers
            module = import_module_from_file(file_path)
            if hasattr(module, 'main'):
                # Pass environment info to scrapers
                if hasattr(module, 'IS_GITHUB_ACTIONS'):
                    module.IS_GITHUB_ACTIONS = IS_GITHUB_ACTIONS
                if hasattr(module, 'OUTPUT_DIR'):
                    module.OUTPUT_DIR = OUTPUT_BASE_DIR

                module.main()

        execution_time = time.time() - start_time
        logger.info(f"Completed scraper: {file_name} in {execution_time:.2f} seconds")
        return True
    except Exception as e:
        logger.error(f"Error in scraper {file_name}: {str(e)}", exc_info=True)
        return False


def run_all_scrapers():
    """Run all scrapers in the 'scraper' directory."""
    # Ensure environment is properly set up
    if not ensure_output_directories():
        logger.error("Failed to setup output directories - aborting")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_scrapers': []
        }

    chrome_driver_path = ensure_chromedriver()
    if chrome_driver_path:
        os.environ["CHROME_DRIVER_PATH"] = chrome_driver_path

    # Get the path to the scraper directory
    root_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_dir = os.path.join(root_dir, 'scraper')

    if not os.path.exists(scraper_dir):
        logger.error(f"Scraper directory not found: {scraper_dir}")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_scrapers': []
        }

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