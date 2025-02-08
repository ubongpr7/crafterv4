import subprocess
import os
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile


def validate_video_file(file: UploadedFile):
    """Validate if the uploaded video is not corrupt by checking with FFmpeg."""
    temp_file_path = os.path.join("/tmp", file.name)

    try:
        # Save the uploaded file temporarily for validation
        with open(temp_file_path, "wb+") as temp_file:
            for chunk in file.chunks():
                temp_file.write(chunk)

        # Run the FFmpeg probe command to check if the video is valid
        result = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", temp_file_path, "-f", "null", "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        if result.returncode != 0:
            # If FFmpeg returns an error, raise a validation error
            raise ValidationError(
                f'This video file is corrupt: {result.stderr.decode("utf-8")}'
            )

    except Exception as e:
        raise ValidationError(f"Error validating video file: {str(e)}")

    finally:
        # Clean up by removing the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
