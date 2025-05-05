import importlib.util
import time
import sys
import subprocess
import logging
import os
from datetime import datetime

# Enhanced environment detection
IS_GITHUB_ACTIONS = os.getenv('GITHUB_ACTIONS') == 'true'
OUTPUT_BASE_DIR = os.path.join("chatbot", "scraped_data_git") if IS_GITHUB_ACTIONS else os.path.join("..",
                                                                                                     "scraped_data")

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
logger.info(f"Is it Git: {IS_GITHUB_ACTIONS}")
logger.info(f"Output directory set to: {OUTPUT_BASE_DIR}")


def ensure_output_directories():
    """Ensure output directories exist with proper permissions."""
    try:
        os.makedirs(OUTPUT_BASE_DIR, exist_ok=True)
        logger.info(f"Verified output directory: {OUTPUT_BASE_DIR}")
        # Only try to change permissions if not in Windows
        if not sys.platform.startswith('win'):
            os.chmod(OUTPUT_BASE_DIR, 0o777)
        return True
    except Exception as e:
        logger.error(f"Failed to create output directory: {str(e)}", exc_info=True)
        return False


def ensure_chromedriver():
    """Ensure ChromeDriver is properly set up."""
    try:
        if IS_GITHUB_ACTIONS:
            # In GitHub Actions, use system-installed ChromeDriver
            chrome_path = "/usr/bin/chromedriver"
            if os.path.exists(chrome_path):
                logger.info(f"Using system ChromeDriver at: {chrome_path}")
                return chrome_path
            logger.error("System ChromeDriver not found in GitHub Actions")
            return None

        # Local development setup
        chrome_dir = os.path.join(os.path.dirname(__file__), "chrome")
        os.makedirs(chrome_dir, exist_ok=True)
        chrome_path = os.path.join(chrome_dir, "chromedriver.exe" if sys.platform.startswith('win') else "chromedriver")
        logger.info(f"Local ChromeDriver path: {chrome_path}")
        return chrome_path
    except Exception as e:
        logger.error(f"ChromeDriver setup failed: {str(e)}", exc_info=True)
        return None


def import_module_from_file(file_path):
    """Import a Python module from a file path."""
    try:
        spec = importlib.util.spec_from_file_location("scraper_module", file_path)
        if spec is None:
            logger.error(f"Failed to create spec for {file_path}")
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules["scraper_module"] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Failed to import module {file_path}: {str(e)}", exc_info=True)
        return None


def run_scraper(file_path, is_selenium_scraper=False):
    """Execute a single scraper script."""
    file_name = os.path.basename(file_path)
    logger.info(f"Starting scraper: {file_name}")

    try:
        start_time = time.time()
        env = os.environ.copy()
        env["IS_GITHUB_ACTIONS"] = str(IS_GITHUB_ACTIONS)
        env["OUTPUT_DIR"] = OUTPUT_BASE_DIR

        if is_selenium_scraper:
            result = subprocess.run(
                [sys.executable, file_path],
                capture_output=True,
                text=True,
                env=env,
                cwd=os.path.dirname(file_path))

            if result.stdout:
                logger.info(f"Output from {file_name}:\n{result.stdout}")
            if result.stderr:
                logger.error(f"Errors from {file_name}:\n{result.stderr}")

            return result.returncode == 0
        else:
            module = import_module_from_file(file_path)
            if module is None:
                logger.error(f"Failed to import module {file_name}")
                return False

            if hasattr(module, 'main'):
                # Set environment variables if the module expects them
                if hasattr(module, 'IS_GITHUB_ACTIONS'):
                    module.IS_GITHUB_ACTIONS = IS_GITHUB_ACTIONS
                if hasattr(module, 'OUTPUT_DIR'):
                    module.OUTPUT_DIR = OUTPUT_BASE_DIR

                module.main()
                return True
            else:
                logger.error(f"Module {file_name} has no main() function")
                return False

    except Exception as e:
        logger.error(f"Error in scraper {file_name}: {str(e)}", exc_info=True)
        return False
    finally:
        execution_time = time.time() - start_time
        logger.info(f"Completed scraper: {file_name} in {execution_time:.2f} seconds")


def run_all_scrapers():
    """Execute all scraper scripts in the scraper directory."""
    if not ensure_output_directories():
        logger.error("Critical: Failed to setup output directories!")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_scrapers': []
        }

    chrome_path = ensure_chromedriver()
    if chrome_path:
        os.environ["CHROME_DRIVER_PATH"] = chrome_path

    # Get the correct path to the scraper directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_dir = os.path.join(current_dir, 'scraper')

    if not os.path.exists(scraper_dir):
        logger.error(f"Scraper directory not found: {scraper_dir}")
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_scrapers': []
        }

    try:
        py_files = [
            os.path.join(scraper_dir, f)
            for f in os.listdir(scraper_dir)
            if f.endswith('.py') and f != '__init__.py' and os.path.isfile(os.path.join(scraper_dir, f))
        ]
    except Exception as e:
        logger.error(f"Failed to list scraper files: {str(e)}", exc_info=True)
        return {
            'total': 0,
            'success': 0,
            'failed': 0,
            'failed_scrapers': []
        }

    selenium_scrapers = {
        "program_links_utd_s.py",
        "scholarship_data_s.py",
        "tuition_rates_content.py",
        "utd_programs_data_s.py"
    }

    results = {
        'total': len(py_files),
        'success': 0,
        'failed': 0,
        'failed_scrapers': []
    }

    for file_path in py_files:
        file_name = os.path.basename(file_path)
        is_selenium = file_name in selenium_scrapers

        success = run_scraper(file_path, is_selenium)
        if success:
            results['success'] += 1
        else:
            results['failed'] += 1
            results['failed_scrapers'].append(file_name)

    logger.info(f"Execution complete. Success: {results['success']}, Failed: {results['failed']}")
    if results['failed'] > 0:
        logger.warning(f"Failed scrapers: {', '.join(results['failed_scrapers'])}")

    return results


if __name__ == "__main__":
    sys.exit(0 if run_all_scrapers()['failed'] == 0 else 1)