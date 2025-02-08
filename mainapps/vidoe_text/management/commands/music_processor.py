from mainapps.vidoe_text.models import LogoModel, TextFile
from moviepy.editor import (
    VideoFileClip,
    AudioFileClip,
    concatenate_audioclips,
    CompositeAudioClip,
    CompositeVideoClip,
)
import os
import sys
import json
import moviepy.video.fx.all as vfx
from moviepy.config import change_settings
from django.core.management.base import BaseCommand
from moviepy.editor import TextClip
import os
import tempfile
import logging
from moviepy.editor import AudioFileClip

import logging

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)

from moviepy.editor import VideoFileClip, ImageClip
import numpy as np


import tempfile
from django.core.files.base import ContentFile

import time
from django.utils import timezone
from django.conf import settings
import boto3

base_path = settings.MEDIA_ROOT


# Set the path to ImageMagick executable
imagemagick_path = "convert"
os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path
change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
bucket_name = settings.AWS_STORAGE_BUCKET_NAME
aws_secret = settings.AWS_SECRET_ACCESS_KEY
s3 = boto3.client(
    "s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=aws_secret
)


def download_from_s3(file_key, local_file_path):
    """
    Download a file from S3 and save it to a local path.

    Args:
        file_key (str): The S3 object key (file path in the bucket).
        local_file_path (str): The local file path where the file will be saved.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        # Download the file from the bucket using its S3 object key
        response = s3.get_object(Bucket=bucket_name, Key=file_key)
        object_content = response["Body"].read()
        logging.info(f"Downloaded {file_key} from S3 to {local_file_path}")
        return object_content
    except Exception as e:
        logging.error(f"Failed to download {file_key} from S3: {e}")
        return False


def update_progress(progress, dir_s):
    with open(dir_s, "w") as f:
        f.write(str(progress))


class Command(BaseCommand):
    help = "Process video files based on TextFile model"

    def add_arguments(self, parser):
        parser.add_argument("text_file_id", type=int)

    def handle(self, *args, **kwargs):
        text_file_id = kwargs["text_file_id"]
        self.text_file_instance = TextFile.objects.get(id=text_file_id)
        with self.text_file_instance.bg_music_text.open("r") as f:
            music_info = f.readlines()
            self.text_file_instance.track_progress(2)
        video_clip = self.load_video_from_instance(
            self.text_file_instance, "generated_final_video"
        )
        video_duration = video_clip.duration

        # Load the original audio from the video
        original_audio = video_clip.audio
        background_clips = []
        self.text_file_instance.track_progress(8)
        for line in music_info:
            music_path, start_time, end_time, bg_level = line.strip().split(" ")
            start_time_seconds = float(start_time)
            end_time_seconds = float(end_time)
            duration = end_time_seconds - start_time_seconds

            if duration < 0:
                raise ValueError("End time must be greater than start time.")

            # Load and process the background music file
            # music_path=os.path.join('app',music_path)
            music_path = music_path.strip()

            background_clip = self.load_audio_from_file_field(music_path).subclip(
                0, duration
            )
            background_clip = background_clip.set_start(start_time_seconds)
            background_clip = background_clip.volumex(float(bg_level))

            # Append the processed background clip to the list
            background_clips.append(background_clip)
        self.text_file_instance.track_progress(40)

        background_audio = CompositeAudioClip(background_clips)
        self.text_file_instance.track_progress(45)

        logging.info("Done loading music")

        if original_audio is not None:
            # final_audio = CompositeAudioClip([original_audio.volumex(1.0), background_audio.volumex(float(self.text_file_instance.bg_level))])
            final_audio = CompositeAudioClip(
                [original_audio.volumex(1.0), background_audio]
            )
        else:
            final_audio = background_audio
        self.text_file_instance.track_progress(56)

        if final_audio.duration < video_duration:
            # Loop the audio if it's shorter than the video duration
            num_loops = int(video_duration / final_audio.duration) + 1
            final_audio = concatenate_audioclips([final_audio] * num_loops).subclip(
                0, video_duration
            )

        else:
            # Trim the audio if it's longer than the video duration
            final_audio = final_audio.subclip(0, video_duration)
        self.text_file_instance.track_progress(68)

        # Set the final audio to the video clip
        video_clip = video_clip.set_audio(final_audio)

        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False
        ) as temp_output_video:
            # generated_srt=text_file_instance.generated_srt.name

            self.text_file_instance.track_progress(70)

            video_clip.write_videofile(
                temp_output_video.name,
                codec="libx264",
                preset="ultrafast",
                fps=30,
                audio_codec="aac",
                # ffmpeg_params=["-movflags", "+faststart"],
            )

            # Save the watermarked video to the generated_watermarked_video field
            if self.text_file_instance.generated_final_bgm_video:
                self.text_file_instance.generated_final_bgm_video.delete(save=False)

            self.text_file_instance.generated_final_bgm_video.save(
                f"final_{self.text_file_instance.id}_.mp4",
                ContentFile(open(temp_output_video.name, "rb").read()),
            )
            self.text_file_instance.track_progress(80)

        self.add_static_watermark_to_instance()

        self.stdout.write(
            self.style.SUCCESS(f"Processing complete for {text_file_id}.")
        )

    def add_animated_watermark_to_instance(self, video):
        """
        Add an animated watermark to the video from text_file_instance and save the result.
        """
        text_file_instance = self.text_file_instance

        # Define the path where the logo will be temporarily stored

        watermark_s3_path = LogoModel.objects.first().logo.name

        text_file_instance = self.text_file_instance

        # Define the path where the logo will be temporarily stored
        # logo_path = os.path.join(os.getcwd(),'media','vlc','logo.png')
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as watermark_temp_path:
            content = download_from_s3(watermark_s3_path, watermark_temp_path.name)

            with open(watermark_temp_path.name, "wb") as png_file:
                png_file.write(content)
        try:
            watermark = (
                ImageClip(watermark_temp_path.name)
                .resize(width=video.w * 1)
                .set_opacity(0.7)
            )

        except Exception as e:
            logging.error(f"Error loading watermark image: {e}")
            return False

        # Function to calculate the new position of the watermark
        self.text_file_instance.track_progress(82)

        def moving_watermark(t):
            speed_x, speed_y = 250, 200
            pos_x = np.abs((speed_x * t) % (2 * video.w) - video.w)
            pos_y = np.abs((speed_y * t) % (2 * video.h) - video.h)
            return (pos_x, pos_y)

        # Animate the watermark
        watermark = watermark.set_position(
            moving_watermark, relative=False
        ).set_duration(video.duration)

        # Overlay the animated watermark on the video
        watermarked = CompositeVideoClip([video, watermark], size=video.size)
        watermarked.set_duration(video.duration)
        self.text_file_instance.track_progress(88)

        # Save the output to a temporary file
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            ) as temp_output_video:
                watermarked.write_videofile(
                    temp_output_video.name,
                    codec="libx264",
                    preset="ultrafast",
                    audio_codec="aac",
                    fps=30,
                )
                self.text_file_instance.track_progress(95)

                # Save the watermarked video to the model field
                if text_file_instance.generated_final_bgmw_video:
                    text_file_instance.generated_final_bgmw_video.delete(save=False)

                with open(temp_output_video.name, "rb") as temp_file:
                    text_file_instance.generated_final_bgmw_video.save(
                        f"watermarked_output_{text_file_instance.id}.mp4",
                        ContentFile(temp_file.read()),
                    )

            logging.info("Watermarked video generated successfully.")
            time.sleep(5)

            self.text_file_instance.track_progress(100)

            return True

        except Exception as e:
            logging.error(f"Error generating watermarked video: {e}")
            return False

    def load_video_from_file_field(self, file_field) -> VideoFileClip:
        """
        Load a video from a file field, downloading it from S3,
        and return it as a MoviePy VideoFileClip.

        Args:
            file_field: The FileField containing the S3 path for the video file.

        Returns:
            VideoFileClip: The loaded video clip.

        Raises:
            ValueError: If the file field is empty or not a valid video file.
        """
        try:
            # Ensure that the file field is valid
            if not file_field or not file_field.name:
                raise ValueError("File field is empty or invalid.")

            # Create a temporary file to store the downloaded video
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                # Download the video file from S3 and save it to the temporary file
                video_content = download_from_s3(file_field.name, temp_video.name)

                if not video_content:
                    raise ValueError("Failed to download the video from S3.")

                # Write the video content to the temp file
                with open(temp_video.name, "wb") as video_file:
                    video_file.write(video_content)

                # Load the video using MoviePy
                video_clip = VideoFileClip(os.path.normpath(temp_video.name))

                # Return the video clip
                return video_clip

        except Exception as e:
            logging.error(f"Error loading video from file field: {e}")
            raise

    def add_static_watermark_to_instance(self):
        """
        Add a static watermark to the video from text_file_instance and save the result.
        """
        text_file_instance = self.text_file_instance
        video = self.load_video_from_file_field(
            text_file_instance.generated_final_bgm_video
        )

        # Get the watermark from the S3 path
        watermark_s3_path = LogoModel.objects.first().logo.name

        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as watermark_temp_path:
            content = download_from_s3(watermark_s3_path, watermark_temp_path.name)
            with open(watermark_temp_path.name, "wb") as png_file:
                png_file.write(content)

        try:
            # Load the watermark image and resize it to 80% of the video width
            watermark = (
                ImageClip(watermark_temp_path.name)
                .resize(width=video.w * 1)
                .set_opacity(0.7)
            )
        except Exception as e:
            logging.error(f"Error loading watermark image: {e}")
            return False

        # Position the watermark in the center of the video
        watermark = watermark.set_position(("center", "center")).set_duration(
            video.duration
        )

        # Overlay the static watermark on the video
        watermarked = CompositeVideoClip([video, watermark], size=video.size)
        watermarked.set_duration(video.duration)
        self.text_file_instance.track_progress(88)

        # Save the output to a temporary file
        try:
            with tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            ) as temp_output_video:
                watermarked.write_videofile(
                    temp_output_video.name,
                    codec="libx264",
                    preset="ultrafast",
                    audio_codec="aac",
                    fps=30,
                )
                self.text_file_instance.track_progress(95)

                # Save the watermarked video to the model field
                if text_file_instance.generated_final_bgmw_video:
                    text_file_instance.generated_final_bgmw_video.delete(save=False)

                with open(temp_output_video.name, "rb") as temp_file:
                    text_file_instance.generated_final_bgmw_video.save(
                        f"watermarked_output_{text_file_instance.id}.mp4",
                        ContentFile(temp_file.read()),
                    )

            logging.info("Watermarked video generated successfully.")
            time.sleep(5)

            self.text_file_instance.track_progress(100)

            return True

        except Exception as e:
            logging.error(f"Error generating watermarked video: {e}")
            return False

    def load_video_from_instance(self, text_file_instance, file_field) -> VideoFileClip:
        """
        Load a video from the specified file field in the text_file_instance, downloading it from S3,
        and return it as a MoviePy VideoFileClip.

        Args:
            text_file_instance: An instance containing the S3 path for the video file.
            file_field: The name of the file field in text_file_instance that holds the video.

        Returns:
            VideoFileClip: The loaded video clip.

        Raises:
            ValueError: If the specified file field is invalid or not a video file.
        """
        try:
            # Check if the specified file field exists and is valid
            if not hasattr(text_file_instance, file_field):
                raise ValueError(f"{file_field} does not exist in text_file_instance.")

            video_file_field = getattr(text_file_instance, file_field)

            if not video_file_field or not video_file_field.name:
                raise ValueError(
                    f"Video S3 key is empty for {file_field} in the text_file_instance."
                )

            # Create a temporary file to store the downloaded video
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_video:
                # Download the video file from S3 and save it to the temporary file
                video_content = download_from_s3(video_file_field.name, temp_video.name)

                if not video_content:
                    raise ValueError("Failed to download the video from S3.")

                # Write the video content to the temp file
                with open(temp_video.name, "wb") as video_file:
                    video_file.write(video_content)

            # Check if the downloaded file is a valid video
            video_clip = VideoFileClip(os.path.normpath(temp_video.name))

            # Check for duration or any other validation if needed
            if video_clip.duration <= 0:
                raise ValueError("Downloaded file is not a valid video.")

            # Return the video clip
            return video_clip

        except Exception as e:
            logging.error(f"Error loading video from text_file_instance: {e}")
            raise

    def load_audio_from_file_field(self, file_field) -> AudioFileClip:
        """
        Load an audio file from a file field, downloading it from S3,
        and return it as a MoviePy AudioFileClip.

        Args:
            file_field: The FileField containing the S3 path for the audio file.

        Returns:
            AudioFileClip: The loaded audio clip.

        Raises:
            ValueError: If the file field is empty or not a valid audio file.
        """
        try:
            # Ensure that the file field is valid
            if not file_field or not file_field:
                raise ValueError("File field is empty or invalid.")

            # Create a temporary file to store the downloaded audio
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_audio:
                # Download the audio file from S3 and save it to the temporary file
                audio_content = download_from_s3(file_field, temp_audio.name)

                if not audio_content:
                    raise ValueError("Failed to download the audio from S3.")

                # Write the audio content to the temp file
                with open(temp_audio.name, "wb") as audio_file:
                    audio_file.write(audio_content)

                # Load the audio using MoviePy
                audio_clip = AudioFileClip(os.path.normpath(temp_audio.name))

                # Return the audio clip
                return audio_clip

        except Exception as e:
            logging.error(f"Error loading audio from file field: {e}")
            raise
