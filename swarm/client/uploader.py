import httpx
from loguru import logger


def upload_results(server_url: str, task_id: str, allure_zip: bytes) -> bool:
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{server_url}/api/tasks/{task_id}/upload",
                files={"file": ("allure-results.zip", allure_zip, "application/zip")},
            )
        
        if response.status_code == 200:
            logger.info(f"Allure results uploaded for task {task_id}")
            return True
        else:
            logger.error(f"Failed to upload results: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"Error uploading results: {e}")
        return False