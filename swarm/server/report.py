import shutil
import subprocess
from pathlib import Path

from loguru import logger

from swarm.server.config import get_allure_dir, get_report_dir, settings


def generate_report(task_id: str) -> bool:
    allure_dir = get_allure_dir(task_id)
    report_dir = get_report_dir(task_id)
    
    if not allure_dir.exists():
        logger.error(f"Allure directory not found: {allure_dir}")
        return False
    
    try:
        report_dir.mkdir(parents=True, exist_ok=True)
        
        result = subprocess.run(
            ["allure", "generate", str(allure_dir), "-o", str(report_dir)],
            capture_output=True,
            text=True,
        )
        
        if result.returncode == 0:
            logger.info(f"Report generated for task {task_id}")
            return True
        else:
            logger.error(f"Failed to generate report: {result.stderr}")
            return False
    except FileNotFoundError:
        logger.error("Allure command not found. Please install allure.")
        return False
    except Exception as e:
        logger.error(f"Error generating report: {e}")
        return False


def save_allure_results(task_id: str, zip_data: bytes) -> bool:
    import tempfile
    import zipfile
    
    allure_dir = get_allure_dir(task_id)
    try:
        allure_dir.mkdir(parents=True, exist_ok=True)
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_file.write(zip_data)
            tmp_path = tmp_file.name
        
        with zipfile.ZipFile(tmp_path, "r") as zip_ref:
            zip_ref.extractall(allure_dir)
        
        Path(tmp_path).unlink()
        
        logger.info(f"Allure results saved for task {task_id}")
        return True
    except Exception as e:
        logger.error(f"Error saving allure results: {e}")
        return False


def get_report_path(task_id: str) -> Path:
    return get_report_dir(task_id) / "index.html"