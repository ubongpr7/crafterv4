import logging
import os
import cloudconvert
from django.conf import settings
import requests
from django.utils.crypto import get_random_string as generate_random_string

cloudconvert.configure(api_key=settings.CLOUDCONVERT_API_KEY, sandbox=False)


# Configure logging
logger = logging.getLogger(__name__)

def convert_mov_to_mp4(file):
    """
    Converts a .mov file to .mp4 using CloudConvert API and returns the converted file path.
    """
    logger.info("Starting .mov to .mp4 conversion for file: %s", file.name)

    try:
        # Create a job for import, conversion, and export
        logger.debug("Creating CloudConvert job...")
        job = cloudconvert.Job.create(payload={
            "tasks": {
                "import-my-file": {
                    "operation": "import/upload"
                },
                "convert-my-file": {
                    "operation": "convert",
                    "input": "import-my-file",
                    "output_format": "mp4"
                },
                "export-my-file": {
                    "operation": "export/url",
                    "input": "convert-my-file"
                }
            }
        })
        logger.info("CloudConvert job created successfully. Job ID: %s", job["id"])

        # Get the upload URL
        logger.debug("Fetching upload URL from job tasks...")
        upload_task = next(task for task in job["tasks"] if task["name"] == "import-my-file")
        upload_url = upload_task["result"]["form"]["url"]
        upload_params = upload_task["result"]["form"]["parameters"]
        logger.info("Upload URL retrieved successfully.")

        # Upload the file
        logger.debug("Uploading file to CloudConvert...")
        files = {"file": (file.name, file.read())}
        response = requests.post(upload_url, data=upload_params, files=files)
        response.raise_for_status()
        logger.info("File uploaded successfully.")

        # Wait for the job to complete
        logger.debug("Waiting for job completion. Job ID: %s", job["id"])
        job = cloudconvert.Job.wait(id=job["id"])
        logger.info("Job completed successfully. Export task ID: %s", job["id"])

        # Get the download URL
        logger.debug("Fetching download URL from export task...")
        export_task = next(task for task in job["tasks"] if task["name"] == "export-my-file")
        download_url = export_task["result"]["files"][0]["url"]
        logger.info("Download URL retrieved successfully.")

        # Download the converted file
        # converted_file_path = f"media/{generate_random_string(12)}/{file.name.replace('.mov', '.mp4')}"
        # Normalize the file extension to lowercase before replacing
        converted_file_path = f"media/{generate_random_string(12)}/{os.path.splitext(file.name)[0]}.mp4"

        os.makedirs(os.path.dirname(converted_file_path), exist_ok=True)
        logger.debug("Downloading converted file to: %s", converted_file_path)
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(converted_file_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        logger.info("Converted file downloaded successfully: %s", converted_file_path)

        return converted_file_path

    except Exception as e:
        logger.error("Error during file conversion: %s", str(e), exc_info=True)
        raise
