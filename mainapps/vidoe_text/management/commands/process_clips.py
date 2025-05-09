import concurrent.futures
from django.core.management.base import BaseCommand
from mainapps.vidoe_text.models import TextFile, TextLineVideoClip, LogoModel
import sys
import time
import matplotlib.colors as mcolors
import imageio
from django.templatetags.static import static
from moviepy.editor import ImageClip

import numpy as np
from django.contrib.staticfiles.storage import staticfiles_storage
import textwrap

from PIL import ImageFont, Image,ImageDraw,ImageColor
from pathlib import Path
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
    CompositeAudioClip,
    TextClip,
    VideoFileClip,
)
import moviepy
from pilmoji import Pilmoji

from moviepy.video.fx.all import crop as fix_all_crop
import moviepy.video.fx.resize as rz
from moviepy.video.fx.crop import crop
from moviepy.video.fx.loop import loop
from moviepy.config import change_settings
import openai
import requests
import shutil

from django.core.files.base import ContentFile

from moviepy.video.fx.speedx import speedx
from elevenlabs import Voice, VoiceSettings, play, save as save_11
from elevenlabs.client import ElevenLabs
import subprocess
import json
import sys
import moviepy.video.fx.all as vfx
import logging
import warnings
from pydantic import BaseModel, ConfigDict, Field
import os
import re
import json
from typing import List, Dict
import pysrt
from pysrt import SubRipTime, SubRipFile, SubRipItem
import os
import subprocess
import logging
import tempfile
from django.core.files.base import ContentFile

import time
from django.utils import timezone
from django.conf import settings
import boto3

import subprocess

base_path = settings.MEDIA_ROOT

RESOLUTIONS = {
    "1:1": (480, 480),  # Square video
    "4:5": (800, 1000),  # Common social media format
    "16:9": (1920, 1080),  # Full HD (1080p)
    "9:16": (1080, 1920),  # Vertical video (social media, mobile)
    "21:9": (2560, 1080),  # Ultra-wide HD
    "18:9": (1440, 720),  # Mobile phone aspect ratio
    "3:2": (720, 480),  # DSLR cameras
    "2:3": (480, 720),  # Rotated 3:2
    "4:3": (1024, 768),  # Old monitors, TVs
    "3:4": (768, 1024),  # Portrait 4:3
    "5:4": (1280, 1024),  # Old square-like monitors
    "32:9": (5120, 1440),  # Super ultra-wide monitors
    "32:10": (3840, 1200),  # Rare ultra-wide resolution
    "17:9": (2048, 1080),  # DCI 2K format
    "5:3": (1280, 768),  # Rare widescreen aspect ratio
    "14:9": (700, 450),  # Transitional broadcasting ratio
    "2.39:1": (2560, 1070),  # Cinematic widescreen
    "2.35:1": (1920, 817),  # Cinematic widescreen
    "1.85:1": (1920, 1038),  # Widescreen cinema standard
    "7:8": (700,800)
}


warnings.filterwarnings(
    "ignore",
    category=UserWarning,
)

openai.api_key = (
    os.getenv('OPEN_API_KEY')
)
PEXELS_API_KEY = (
    os.getenv('PEXELS_API_KEY')
   
)
# Base URL for Pexels API
BASE_URL = "https://api.pexels.com/videos/search"
os.environ["PYTHONIOENCODING"] = "UTF-8"
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)
imagemagick_path = "/usr/bin/convert"  # Set the path to the ImageMagick executable
os.environ["IMAGEMAGICK_BINARY"] = imagemagick_path
change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})

AWS_ACCESS_KEY_ID = settings.AWS_ACCESS_KEY_ID
bucket_name = settings.AWS_STORAGE_BUCKET_NAME
aws_secret = settings.AWS_SECRET_ACCESS_KEY
s3 = boto3.client(
    "s3", aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=aws_secret
)

fonts1 = {
    "Arial": os.path.join(os.getcwd(), "fonts", "arial.ttf"),
    "Open Sans": os.path.join(os.getcwd(), "fonts", "OpenSans-Semibold.ttf"),
    "Helvetica": os.path.join(os.getcwd(), "fonts", "Helvetica.otf"),
    "Montserrat": os.path.join(os.getcwd(), "fonts", "montserra.ttf"),
    "Roboto": os.path.join(os.getcwd(), "fonts", "Roboto-Medium.ttf"),
}

fonts = {
    "Arial": "/usr/share/fonts/custom/arial.ttf",
    "Open Sans Condensed": "/usr/share/fonts/custom/OpenSans-Semibold.ttf",
    "HelveticaforTarget-Bold": "/usr/share/fonts/custom/Helvetica.otf",
    "Montserrat": "/usr/share/fonts/custom/Montserrat.otf",
    "Roboto Medium": "/usr/share/fonts/custom/Roboto-Medium.ttf",
}


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


def parse_s3_url(s3_url):
    """
    Parse the S3 URL to extract the bucket name and the key.

    Args:
        s3_url (str): The S3 URL (e.g., s3://mybucket/myfile.txt)

    Returns:
        tuple: (bucket_name, key)
    """
    s3_url = s3_url.replace("s3://", "")
    bucket_name, key = s3_url.split("/", 1)
    return bucket_name, key

aspect_ratios_list = [
    "1:1", "4:5", "16:9", "9:16", "21:9", "18:9", "3:2", "2:3", 
    "4:3", "3:4", "5:4", "4:5", "32:9", "32:10", "17:9", 
    "11:8", "5:3", "3:5", "14:9", "2.39:1", "2.35:1", "1.85:1","7:8",
]

MAINRESOLUTIONS = {
    "1:1": 1,
    "4:5": 4/5,
    "16:9": 16/9,
    "9:16": 9/16,
    "21:9": 21/9,
    "18:9": 18/9,
    "3:2": 3/2,
    "2:3": 2/3,
    "4:3": 4/3,
    "3:4": 3/4,
    "5:4": 5/4,
    "4:5": 4/5,
    "32:9": 32/9,
    "32:10": 32/10,
    "17:9": 17/9,
    "11:8": 11/8,
    "5:3": 5/3,
    "3:5": 3/5,
    "14:9": 14/9,
    "2.39:1": 2.39,  
    "2.35:1": 2.35,  
    "1.85:1": 1.85,  
    "7:8": 7/8,  
}

s3_client = boto3.client("s3")

timestamp = int(time.time())

VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp'}

class Command(BaseCommand):
    help = "Process video files based on TextFile model"

    def add_arguments(self, parser):
        parser.add_argument("text_file_id", type=int)

    def handle(self, *args, **kwargs):
        text_file_id = kwargs["text_file_id"]
        text_file_instance = TextFile.objects.get(id=text_file_id)
        self.text_file_instance = TextFile.objects.get(id=text_file_id)
        text_file = text_file_instance.text_file
        resolution = text_file_instance.resolution
        self.text_file_instance.track_progress(2)

        voice_id = text_file_instance.voice_id
        api_key = text_file_instance.api_key
        audio_file = None
        output_audio_file = os.path.join(
            base_path, "audio", f"{timestamp}_{text_file_id}_audio.mp3"
        )

        audio_file = self.convert_text_to_speech(
            text_file, voice_id, api_key, output_audio_file
        )  
        if not audio_file:
            self.text_file_instance.track_progress(
                "The Credit On Your ElevenLabs API Key Is Not Enough To Process The Text File"
            )
            return

        self.text_file_instance.track_progress(10)

        logging.info("done with audio file ")

        if audio_file or text_file_instance.generated_audio:
            srt_file = self.generate_srt_file()
            subtitles_srt_file=self.generate_subclips_srt_file()

            self.text_file_instance.track_progress(25)
            self.text_file_instance.track_progress(26)

        else:
            return
        subclips_processed=self.generate_subclip_videos_with_duration()
        # if  subclips_processed:


        aligned_output = self.process_srt_file(self.text_file_instance.generated_srt)
        self.text_file_instance.track_progress(27)

        blank_video = self.generate_blank_video_with_audio()

        if blank_video:
            blank_vide_clip = self.load_video_from_file_field(
                self.text_file_instance.generated_blank_video
            )
            logging.info("Blank Video clip loaded")

        else:
            logging.error("Blank video file could not be loaded")
            self.text_file_instance.track_progress("error")

            return
        self.text_file_instance.track_progress(29)

        subtitles = self.load_subtitles_from_text_file_instance()
        self.text_file_instance.track_progress(32)

        print(subtitles)
        print("aligned_output: ", aligned_output)
        blank_video_segments, subtitle_segments = self.get_segments_using_srt(
            blank_vide_clip, subtitles
        )
        self.text_file_instance.track_progress(36)
####################################################################################################################
        text_clips = TextLineVideoClip.objects.filter(text_file=self.text_file_instance)

        num_segments = len(text_clips)
        output_video_segments = []
        start = 0
        logging.info("output_video_segments is to start")
        for video_segment, new_subtitle_segment in zip(blank_video_segments, subtitles):
            end = self.subriptime_to_seconds(new_subtitle_segment.end)
            required_duration = end - start
            new_video_segment = self.adjust_segment_duration(
                video_segment, required_duration
            )

            output_video_segments.append(new_video_segment.without_audio())
            start = end
        self.text_file_instance.track_progress(39)

        ################################################################

        replacement_video_files = self.get_video_paths_for_text_file()
        self.text_file_instance.track_progress(40)

        replacement_videos_per_combination = []

        replacement_video_clips = []
        for video_file in replacement_video_files:
            clip = self.load_video_from_file_field(video_file)
            clip = clip.set_fps(30)  
            replacement_video_clips.append(clip)
        replacement_video_clips = self.resize_clips_to_max_size(replacement_video_clips)
        
        logging.info("Concatination Done")
        self.text_file_instance.track_progress(48)

        final_blank_video = self.concatenate_clips(
            blank_video_segments,

        )
        try:
            final__blank_audio = final_blank_video.audio
            self.text_file_instance.track_progress(50)

        except Exception as e:
            logging.error(f"Error loading background music: {e}")
            return

        



        self.text_file_instance.track_progress(54)
        replacement_video_clips=self.resize_clips_to_max_size(replacement_video_clips)
        final_video_segments = self.replace_video_segments(
            output_video_segments, replacement_video_clips, subtitles, blank_vide_clip
        )
        logging.info("Done  replace_video_segments")
        final_resized_clips=self.resize_clips_to_max_size(final_video_segments)
        concatenated_video = self.concatenate_clips(
            final_resized_clips,
        )
        original_audio = blank_vide_clip.audio.subclip(
            0, min(concatenated_video.duration, blank_vide_clip.audio.duration)
        )
        final_video = concatenated_video.set_audio(
            original_audio
        )  
        final_video_speeded_up_clip = self.speed_up_video_with_audio(final_video, 1)
        final_video = self.save_final_video(final_video_speeded_up_clip)
        watermarked = self.add_static_watermark_to_instance()
        self.text_file_instance.track_progress(100)

        self.stdout.write(
            self.style.SUCCESS(f"Processing complete for {text_file_id}.")
        )
    

# I'm
    def generate_subclip_videos_with_duration(self):
        
        extracted_times = self.extract_start_end(self.text_file_instance.generated_subclips_srt)
        logging.debug(f"Extracted times: {extracted_times}")
        
        file_clips = []
        clip_subclips = []
        logging.debug("Starting to process video clips.")
        
        for clip in self.text_file_instance.video_clips.all():
            logging.debug(f"Processing clip with ID: {clip.id}")
            clip_subclip=[]
            for subclip in clip.subclips.all():
                clip_subclips.append(subclip)
        if len(clip_subclips) != len(extracted_times):
            logging.error("Mismatch between the number of clips and JSON fragments.")
            raise ValueError("Mismatch between the number of clips and JSON fragments.")
        
        from decimal import Decimal
        for i,subclip in enumerate(clip_subclips):
            start,end=extracted_times[i]
            subclip.start=Decimal(self.srt_time_to_float(start))
            subclip.end=Decimal(self.srt_time_to_float(end))
            subclip.save()
        for clip in self.text_file_instance.video_clips.all():
            clip_subclips = []
            for subclip in clip.subclips.all():
                logging.debug(f"Processing subclip with ID: {subclip.id}")
                if self.text_file_instance.resolution=='9:16':
                    mv_clip=self.crop_video_ffmpeg(subclip.to_dict().get('video_path').url)
                    
                    clip_with_duration = self.adjust_segment_duration(mv_clip,float(subclip.end - subclip.start))
                    clip_subclips.append(clip_with_duration)

                else:
                    mv_clip = self.load_video_from_file_field(subclip.to_dict().get('video_path'))
                    if subclip.is_tiktok:
                        cropped_clip=self.crop_video_with_ffmpeg(
                            subclip.to_dict().get('video_path').url, 
                            RESOLUTIONS[self.text_file_instance.resolution],
                            mv_clip,
                            subclip.is_tiktok
                            )
                    else:
                        cropped_clip = self.crop_to_aspect_ratio_(mv_clip, MAINRESOLUTIONS[self.text_file_instance.resolution])
                    clip_with_duration = self.adjust_segment_duration(cropped_clip,float(subclip.end - subclip.start))
                    logging.debug(f"Loaded video clip from path: {subclip.to_dict().get('video_path')}")
                    logging.debug(f"Cropped clip to resolution: {MAINRESOLUTIONS[self.text_file_instance.resolution]}")
                    clip_subclips.append(clip_with_duration)
            if len(clip_subclips) == 1:
                self.write_clip_file(clip_subclips[0], clip.video_file,clip)
            else:

                resized_subclips = self.resize_clips_to_max_size(clip_subclips)
                concatenated_clip = self.concatenate_clips(resized_subclips)
                self.write_clip_file(concatenated_clip, clip.video_file,clip)
        return True 

    def crop_video_ffmpeg(self, video_url):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            output_path = temp_output.name

            cmd1 = [
                "ffmpeg", "-y", "-i", video_url,  
                "-vf", "scale=-2:1280,crop=720:1280",  # Scale height to 1280, then crop width to 720
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", 
                "-c:a", "copy", 
                output_path
            ]

            # Second attempt with a different set of parameters
            cmd2 = [
                "ffmpeg", "-y", "-i", video_url,  
                "-vf", "scale=720:1280",  # Directly scale to 720x1280 without cropping
                "-c:v", "libx264", "-preset", "fast", "-crf", "23", 
                "-c:a", "copy", 
                output_path
            ]

            try:
                # Try the first command
                subprocess.run(cmd1, check=True)
            except subprocess.CalledProcessError as e:
                logging.error(f"First command failed with error: {e}")
                try:
                    # If the first command fails, try the second command
                    subprocess.run(cmd2, check=True)
                except subprocess.CalledProcessError as e:
                    logging.error(f"Second command also failed with error: {e}")
                    raise  # Re-raise the exception if both commands fail

            clip = VideoFileClip(output_path)
            return clip
    
    def crop_video_with_ffmpeg(self,input_video, output_resolution,clip,is_tiktok):
        """
        Crops a video to the desired resolution without stretching.
        
        Parameters:
        - input_video (str): Path to the input video file.
        - output_resolution (tuple): Desired (width, height) output resolution.
        
        Returns:
        - str: Path to the cropped output video.
        """
        output_width, output_height = output_resolution

        input_width, input_height = clip.size
        clip.close()

        input_aspect = input_width / input_height
        output_aspect = output_width / output_height
        if input_aspect > output_aspect:
            new_width = int(input_height * output_aspect)
            new_height = input_height
            x_offset = (input_width - new_width) // 2
            y_offset = 0
        else:
            new_width = input_width
            new_height = int(input_width / output_aspect)
            x_offset = 0
            y_offset = (input_height - new_height) // 2

        # Create a temporary output file
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_output:
            output_path = temp_output.name
            if is_tiktok:
            
                # cmd = [
                #     "ffmpeg", "-y", "-i", input_video,
                #     "-vf", 
                #     f"split=2[original][blurred];"                                               # Split the video into two streams
                #     f"[blurred]scale={output_width}:{output_height},boxblur=luma_radius=min(h\,w)/20:luma_power=1[blurred];"  # Blur the entire video
                #     f"[original]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease[scaled];"  # Scale the original video
                #     f"[blurred][scaled]overlay=(W-w)/2:(H-h)/2",                                # Overlay the scaled video on the blurred background
                #     "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                #     "-c:a", "aac", "-b:a", "128k",
                #     output_path
                # ]
                cmd = [
                        "ffmpeg", "-y", "-i", input_video,
                        "-fflags", "+genpts",  # Generate new timestamps
                        "-r", "30",           # Set a common framerate of 30 FPS
                        "-vf", 
                        f"split=2[original][blurred];"                                               # Split the video into two streams
                        f"[blurred]scale={output_width}:{output_height},boxblur=luma_radius=min(h\,w)/20:luma_power=1[blurred];"  # Blur the entire video
                        f"[original]scale={output_width}:{output_height}:force_original_aspect_ratio=decrease[scaled];"  # Scale the original video
                        f"[blurred][scaled]overlay=(W-w)/2:(H-h)/2",                                # Overlay the scaled video on the blurred background
                        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                        "-c:a", "aac", "-b:a", "128k",
                        "-fps_mode", "vfr",  # Control synchronization
                        output_path
                    ]
                
                
            # FFmpeg command to crop the video
            else:

                cmd = [
                    "ffmpeg", "-y", "-i", input_video,
                    "-vf", f"crop={new_width}:{new_height}:{x_offset}:{y_offset}",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                    "-c:a", "copy",
                    output_path
                ]

            # Run FFmpeg
            subprocess.run(cmd, check=True)

            return VideoFileClip(output_path)
    
    def get_video_resolution(self,input_video):
        """
        Uses FFmpeg to get the width and height of a video.
        """
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0", input_video
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        width, height = map(int, result.stdout.strip().split(","))
        return width, height
    def extract_start_end(self,generated_srt):
        """
        Extracts the start and end times from each index in the aligned_output list.

        Args:
            aligned_output (list): List of formatted SRT entries.

        Returns:
            list: A list of tuples containing the start and end times for each entry.
        """
        aligned_output = self.process_srt_file(generated_srt)

        time_data = []

        for entry in aligned_output:
            # Split the entry into lines
            lines = entry.split("\n")
            
            # Check if there's a time range in the second line
            if len(lines) > 1 and '-->' in lines[1]:
                time_range = lines[1]
                # Split the time range into start and end
                start, end = time_range.split(" --> ")
                time_data.append((start.strip(), end.strip()))
        
        return time_data

    def convert_clips_to_videos(self, clips,generated_srt):
        """
        Converts a list of ImageClips to VideoClips using durations from the processed SRT file.

        Args:
            clips (list): List of MoviePy ImageClip objects.

        Returns:
            list: List of converted VideoClips with specified durations.
        """
        extracted_times= self.extract_start_end(generated_srt)

        if len(clips) != len(extracted_times):
            raise ValueError("Mismatch between the number of clips and JSON fragments.")

        video_clips = []
        for i, clip in enumerate(clips):
            if self.is_video_clip(clip):
                video_clips.append(clip)
            elif self.is_image_clip(clip):
                try:
                    begin,end= extracted_times[i]
                    duration = float(self.srt_time_to_float(end)) - float(self.srt_time_to_float((begin))) +1.0

                    video_clip = self.image_to_video(clip, duration)
                    video_clips.append(video_clip)
                except IndexError:
                    raise ValueError(f"Mismatch between the number of clips and JSON fragments at index {i}.")
        
        return video_clips


    def write_clip_file(self, clip,file_to_write,main_clip):
        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False
        ) as temp_output_video:
            if self.text_file_instance.resolution=='9:16':

                clip.write_videofile(
                    temp_output_video.name,
                    codec="libx264",
                    # preset="ultrafast",
                    audio_codec="aac",
                    fps=30,
                    
                    
                )
            else:
                clip.write_videofile(
                    temp_output_video.name,
                    codec="libx264",
                    preset="ultrafast",
                    audio_codec="aac",
                    fps=30,
                    

                    
                )

            if file_to_write:
                file_to_write.delete(save=False)

            with open(temp_output_video.name, "rb") as output_video_file:
                video_content = output_video_file.read()

                file_to_write.save(
                    f"video_{main_clip.id}_{self.generate_random_string()}_{timestamp}.mp4",
                    ContentFile(video_content),
                )
            return True

    def generate_random_string(self,length=10):
        import random
        import string

        characters = string.ascii_letters + string.digits
        return ''.join(random.choice(characters) for _ in range(length))


    def save_final_video(self, clip):
        with tempfile.NamedTemporaryFile(
            suffix=".mp4", delete=False
        ) as temp_output_video:
            self.text_file_instance.track_progress(60)
        
            clip.write_videofile(
                temp_output_video.name,
                codec="libx264",
                preset="ultrafast",
                audio_codec="aac",
                fps=30,
                
                # temp_audiofile='temp-audio.m4a', 
                # remove_temp=True
                # ffmpeg_params=["-movflags", "+faststart"],
            )
            self.text_file_instance.track_progress(70)

            # Save the watermarked video to the generated_watermarked_video field
            if self.text_file_instance.generated_final_video:
                self.text_file_instance.generated_final_video.delete(save=False)
                self.text_file_instance.track_progress(74)

            with open(temp_output_video.name, "rb") as output_video_file:
                video_content = output_video_file.read()

                self.text_file_instance.generated_final_video.save(
                    f"final_{self.text_file_instance.id}_{timestamp}.mp4",
                    ContentFile(video_content),
                )
            self.text_file_instance.track_progress(75)
            return True

    def speed_up_video_with_audio(self, input_video, speed_factor):
        sped_up_video = input_video.fx(vfx.speedx, speed_factor)

        return sped_up_video

    def convert_text_to_speech(
        self, text_file_path, voice_id, api_key, output_audio_file
    ):
        """
        Converts a text file to speech using ElevenLabs and saves the audio in the specified output directory.

        Args:
            text_file_path (str): Path to the text file.
            voice_id (str): The voice ID for speech synthesis.
            api_key (str): API key for ElevenLabs authentication.
            output_audio_file (str): Path where the output audio file will be saved.

        Returns:
            str: Presigned URL of the uploaded audio file or None if an error occurred.
        """
        try:
            # Read the text from the file
            with text_file_path.open("r") as f:
                lines = f.readlines()
                # Combine lines into a single paragraph
                text = " ".join(line.strip() for line in lines)
                logging.info(
                    f"Read text for TTS: {text}..."
                )  # Log first 50 characters
                self.text_file_instance.track_progress(5)

            # Initialize the ElevenLabs client
            client = ElevenLabs(api_key=api_key)

            # Generate speech from the text using the specified voice
            audio_data_generator = client.generate(
                text=text,
                voice=Voice(
                    voice_id=voice_id,
                    settings=VoiceSettings(
                        stability=1.0,
                        similarity_boost=0.66,
                        style=0.0,
                        use_speaker_boost=True,
                        speed=1.1,
                    ),
                ),
            )
            self.text_file_instance.track_progress(7)

            # Convert the generator to bytes
            audio_data = b"".join(audio_data_generator)

            # Instead of manually saving the file, save it using Django's FileField
            # Check if the generated_audio field already contains a file, and delete it if it does
            if self.text_file_instance.generated_audio:
                self.text_file_instance.generated_audio.delete(
                    save=False
                )  # Delete the old file, don't save yet

            # Create a new file name for the audio (no leading /)
            audio_file_name = f"{timestamp}_{self.text_file_instance.id}_audio.mp3"

            # Save the new file to Django's FileField (linked to S3 storage)
            self.text_file_instance.generated_audio.save(
                audio_file_name, ContentFile(audio_data)
            )
            self.text_file_instance.track_progress(8)
            # time.sleep(2)
            # Return the URL to
            return (
                self.text_file_instance.generated_audio
            )  # This will return the URL managed by Django's FileField
        except Exception as e:
            print(e)
            return None
            
    def convert_time(self, seconds):
        milliseconds = int((seconds - int(seconds)) * 1000)
        minutes, seconds = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"
    def srt_time_to_float(self,srt_time):
        """
        Converts an SRT time string to a float representing the total seconds.

        Args:
            srt_time (str): Time string in the format 'HH:MM:SS,mmm'.

        Returns:
            float: Total time in seconds.
        """
        try:
            hours, minutes, rest = srt_time.split(":")
            seconds, milliseconds = rest.split(",")
            
            total_seconds = (
                int(hours) * 3600 +
                int(minutes) * 60 +
                int(seconds) +
                int(milliseconds) / 1000
            )
            return total_seconds
        except ValueError:
            raise ValueError(f"Invalid SRT time format: {srt_time}")

    def generate_subclips_srt_file(self):
        """
        Download the audio and text files from S3, and process them using a subprocess.
        """
        text_file_instance = self.text_file_instance

        s3_text_url = (
            text_file_instance.subclips_text_file.name
        ) 
        s3_audio_url = (
            text_file_instance.generated_audio.name
        )  

        logging.info(f"Downloading audio from S3: {s3_audio_url}")
        logging.info(f"Downloading text from S3: {s3_text_url}")

        if not s3_audio_url or not s3_text_url:
            logging.error("Audio or text file path from S3 is empty")
            return False

        with tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False
        ) as temp_audio, tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as temp_text, tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        ) as temp_srt:

            audio_content = download_from_s3(s3_audio_url, temp_audio.name)
            if not audio_content:
                logging.error(f"Failed to download audio file {s3_audio_url}")
                return False

            with open(temp_audio.name, "wb") as audio_file:
                audio_file.write(audio_content)

            text_content = download_from_s3(s3_text_url, temp_text.name)
            # self.text_file_instance.track_progress(16)

            if not text_content:
                logging.error(f"Failed to download text file {s3_text_url}")
                return False

            with open(temp_text.name, "wb") as text_file:
                text_file.write(text_content)

            command = (
                f'python3.10 -m aeneas.tools.execute_task "{temp_audio.name}" "{temp_text.name}" '
                f'"task_language=eng|is_text_type=plain|os_task_file_format=json" "{temp_srt.name}"'
            )

            try:
                logging.info(f"Running command: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                # self.text_file_instance.track_progress(20)

                # Log command output
                logging.info(f"Command output: {result.stdout}")
                logging.error(f"Command error (if any): {result.stderr}")

                # Check for errors in subprocess execution
                if result.returncode == 0:
                    logging.info(f"SRT content generated successfully")

                    # Save the SRT content to the TextFile instance's srt_file field
                    with open(temp_srt.name, "rb") as srt_file:
                        srt_content = srt_file.read()

                    srt_file_name = f"{text_file_instance.id}_subclip_generated.json"

                    # If there is an existing SRT file, delete it first
                    if text_file_instance.generated_subclips_srt:
                        text_file_instance.generated_subclips_srt.delete(save=False)
                        # self.text_file_instance.track_progress(22)

                    # Save the new SRT content to the srt_file field
                    text_file_instance.generated_subclips_srt.save(
                        srt_file_name, ContentFile(srt_content)
                    )

                    logging.info(f"SRT file saved to instance: {srt_file_name}")
                    # time.sleep(3)
                    # self.text_file_instance.track_progress(24)

                    return text_file_instance.generated_subclips_srt

                else:
                    logging.error(f"Error generating SRT file: {result.stderr}")
                    return False
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred while generating the SRT file: {e}"
                )
                return False

    def generate_srt_file(self):
        """
        Download the audio and text files from S3, and process them using a subprocess.
        """
        text_file_instance = self.text_file_instance

        s3_text_url = (
            text_file_instance.text_file.name
        ) 
        s3_audio_url = (
            text_file_instance.generated_audio.name
        )  

        logging.info(f"Downloading audio from S3: {s3_audio_url}")
        logging.info(f"Downloading text from S3: {s3_text_url}")
        self.text_file_instance.track_progress(12)

        if not s3_audio_url or not s3_text_url:
            logging.error("Audio or text file path from S3 is empty")
            return False

        with tempfile.NamedTemporaryFile(
            suffix=".mp3", delete=False
        ) as temp_audio, tempfile.NamedTemporaryFile(
            suffix=".txt", delete=False
        ) as temp_text, tempfile.NamedTemporaryFile(
            suffix=".json", delete=False
        ) as temp_srt:
            self.text_file_instance.track_progress(14)

            audio_content = download_from_s3(s3_audio_url, temp_audio.name)
            if not audio_content:
                logging.error(f"Failed to download audio file {s3_audio_url}")
                return False

            with open(temp_audio.name, "wb") as audio_file:
                audio_file.write(audio_content)

            text_content = download_from_s3(s3_text_url, temp_text.name)
            self.text_file_instance.track_progress(16)

            if not text_content:
                logging.error(f"Failed to download text file {s3_text_url}")
                return False

            with open(temp_text.name, "wb") as text_file:
                text_file.write(text_content)

            command = (
                f'python3.10 -m aeneas.tools.execute_task "{temp_audio.name}" "{temp_text.name}" '
                f'"task_language=eng|is_text_type=plain|os_task_file_format=json" "{temp_srt.name}"'
            )

            try:
                logging.info(f"Running command: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

                logging.info(f"Command output: {result.stdout}")
                logging.error(f"Command error (if any): {result.stderr}")

                # Check for errors in subprocess execution
                if result.returncode == 0:
                    logging.info(f"SRT content generated successfully")

                    # Save the SRT content to the TextFile instance's srt_file field
                    with open(temp_srt.name, "rb") as srt_file:
                        srt_content = srt_file.read()

                    srt_file_name = f"{text_file_instance.id}_generated.json"

                    # If there is an existing SRT file, delete it first
                    if text_file_instance.generated_srt:
                        text_file_instance.generated_srt.delete(save=False)
                        self.text_file_instance.track_progress(22)

                    # Save the new SRT content to the srt_file field
                    text_file_instance.generated_srt.save(
                        srt_file_name, ContentFile(srt_content)
                    )

                    logging.info(f"SRT file saved to instance: {srt_file_name}")
                    # time.sleep(3)
                    self.text_file_instance.track_progress(24)

                    return text_file_instance.generated_srt

                else:
                    logging.error(f"Error generating SRT file: {result.stderr}")
                    return False
            except Exception as e:
                logging.error(
                    f"An unexpected error occurred while generating the SRT file: {e}"
                )
                return False

    def process_srt_file(self,generated_srt):
        """
        Downloads the generated SRT file from S3, processes it, and returns the aligned output.

        Args:
            text_file_instance: The instance containing the S3 path to the generated SRT file.

        Returns:
            list: A list of formatted SRT entries.
        """
        text_file_instance = self.text_file_instance
        s3_srt_key = (
            generated_srt.name
        )  # S3 key (SRT file path in the bucket)

        if not s3_srt_key:
            logging.error("SRT file path from S3 is empty")
            return None

        logging.info(f"Downloading SRT file from S3: {s3_srt_key}")

        # Create a temporary file to hold the downloaded SRT content
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_srt:
            srt_content = download_from_s3(s3_srt_key, temp_srt.name)

            if not srt_content:
                logging.error(f"Failed to download SRT file {s3_srt_key}")
                return None

            # Write the SRT content to the temporary file
            with open(temp_srt.name, "wb") as srt_file:
                srt_file.write(srt_content)

            # Load and process the SRT file
            try:
                with open(temp_srt.name, "r") as f:
                    sync_map = json.load(f)

                aligned_output = []
                for index, fragment in enumerate(sync_map["fragments"]):
                    start = self.convert_time(float(fragment["begin"]))
                    end = self.convert_time(float(fragment["end"]))
                    text = fragment["lines"][0].strip()

                    # Format the SRT entry
                    aligned_output.append(f"{index + 1}\n{start} --> {end}\n{text}\n")

                logging.info("Finished processing the SRT file")
                return aligned_output

            except Exception as e:
                logging.error(f"Error processing SRT file: {e}")
                return None

    def generate_blank_video_with_audio(self):
        """
        Generate a blank video with audio and save the result.

        Returns:
            bool: True if successful, False otherwise.
        """
        text_file_instance = self.text_file_instance
        try:
            # Get the resolution from text_file_instance
            resolution = text_file_instance.resolution
            if resolution not in RESOLUTIONS:
                raise ValueError(
                    f"Resolution '{resolution}' is not supported. Choose from {list(RESOLUTIONS.keys())}."
                )
            width, height = RESOLUTIONS[resolution]

            # Download the audio file from S3
            audio_s3_key = text_file_instance.generated_audio.name
            srt_s3_key = text_file_instance.generated_srt.name
            if not audio_s3_key or not srt_s3_key:
                logging.error("Audio or SRT file path from S3 is empty.")
                return False

            # Create temporary files for audio and SRT
            with tempfile.NamedTemporaryFile(
                suffix=".mp3", delete=False
            ) as temp_audio, tempfile.NamedTemporaryFile(
                suffix=".json", delete=False
            ) as temp_srt, tempfile.NamedTemporaryFile(
                suffix=".mp4", delete=False
            ) as temp_output_video:
                # Download the audio and SRT files from S3
                audio_content = download_from_s3(audio_s3_key, temp_audio.name)
                srt_content = download_from_s3(srt_s3_key, temp_srt.name)

                if not audio_content or not srt_content:
                    logging.error("Failed to download audio or SRT file from S3.")
                    return False

                # Write the contents to the temp files
                with open(temp_audio.name, "wb") as audio_file, open(
                    temp_srt.name, "wb"
                ) as srt_file:
                    audio_file.write(audio_content)
                    srt_file.write(srt_content)

                # Load the SRT file and calculate duration
                srt_duration = self.get_video_duration_from_json(temp_srt.name)

                # Load the audio file and calculate duration
                audio_clip = AudioFileClip(temp_audio.name)
                audio_duration = audio_clip.duration

                # Log the calculated durations
                logging.info(
                    f"Audio duration: {audio_duration}, SRT duration: {srt_duration}"
                )

                # Determine the maximum duration between the SRT and audio file
                duration = max(srt_duration, audio_duration)
                if duration == 0:
                    logging.error("Duration is zero, cannot create a video.")
                    return False

                # Log the video creation process
                logging.info(
                    f"Creating a blank video with resolution {width}x{height} and duration {duration}"
                )

                # Create a blank (black) video clip with the specified resolution and duration
                blank_clip = ColorClip(
                    size=(width, height), color=(0, 0, 0)
                ).set_duration(duration)

                # Combine the audio with the blank video
                final_video = CompositeVideoClip([blank_clip]).set_audio(audio_clip)

                # Write the final video to the temporary output file

                final_video.write_videofile(
                    temp_output_video.name,
                    fps=30,
                    audio_codec="aac",
                    

                )

                # Save the final video to the `text_file_instance`
                if text_file_instance.generated_blank_video:
                    text_file_instance.generated_blank_video.delete(save=False)

                # Save the video content correctly
                with open(temp_output_video.name, "rb") as output_video_file:
                    video_content = output_video_file.read()

                text_file_instance.generated_blank_video.save(
                    f"blank_output_{text_file_instance.id}.mp4",
                    ContentFile(video_content),
                )
                # time.sleep(2)
                logging.info(
                    f"Video generated successfully and saved as {text_file_instance.generated_blank_video.name}"
                )
                # time.sleep(4)

                return True

        except Exception as e:
            logging.error(f"Error generating video: {e}")
            return False

    def get_video_duration_from_json(self, json_file):
        with open(json_file, "r") as file:
            data = json.load(file)

        # Extract the end times from the fragments
        end_times = [fragment["end"] for fragment in data["fragments"]]

        # Get the last end time (duration of the video)
        last_end_time = end_times[-1] if end_times else "0.000"

        # Convert the time format (seconds) to float
        return float(last_end_time)

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

    def load_subtitles_from_text_file_instance(self) -> SubRipFile:
        """
        Load subtitles from the generated SRT JSON file in the text_file_instance and convert them to SRT format.

        Returns:
            SubRipFile: The loaded subtitles in SRT format.

        Raises:
            ValueError: If the specified file field is invalid or not a valid JSON file.
        """
        text_file_instance = self.text_file_instance
        try:
            # Check if the specified file field exists and is valid

            json_file_field = text_file_instance.generated_srt

            if not json_file_field or not json_file_field.name:
                raise ValueError(
                    f"JSON S3 key is empty for {json_file_field} in the text_file_instance."
                )

            # Create a temporary file to store the downloaded JSON
            with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_json:
                # Download the JSON file from S3 and save it to the temporary file
                json_content = download_from_s3(json_file_field.name, temp_json.name)

                if not json_content:
                    raise ValueError("Failed to download the JSON file from S3.")

                # Write the JSON content to the temp file
                with open(temp_json.name, "wb") as json_file:
                    json_file.write(json_content)

            # Load the JSON data
            with open(temp_json.name, "r") as file:
                data = json.load(file)

            fragments = data.get("fragments", [])

            # Create a SubRipFile object
            subs = SubRipFile()

            # Iterate through fragments and create SubRipItem for each
            for i, fragment in enumerate(fragments, start=1):
                start_time = self.convert_seconds_to_subrip_time(
                    float(fragment["begin"])
                )
                end_time = self.convert_seconds_to_subrip_time(float(fragment["end"]))
                text = "\n".join(
                    fragment["lines"]
                )  # Join the lines to mimic subtitle text
                sub = SubRipItem(index=i, start=start_time, end=end_time, text=text)
                subs.append(sub)

            return subs

        except Exception as e:
            logging.error(f"Error loading subtitles from text_file_instance: {e}")
            raise

    def convert_seconds_to_subrip_time(self, seconds):
        """Helper function to convert seconds into SubRipTime."""
        ms = int((seconds % 1) * 1000)
        s = int(seconds) % 60
        m = (int(seconds) // 60) % 60
        h = int(seconds) // 3600
        return SubRipTime(hours=h, minutes=m, seconds=s, milliseconds=ms)

    def subriptime_to_seconds(self, srt_time: pysrt.SubRipTime) -> float:
        return (
            srt_time.hours * 3600
            + srt_time.minutes * 60
            + srt_time.seconds
            + srt_time.milliseconds / 1000.0
        )

    def get_segments_using_srt(
        self, video: VideoFileClip, subtitles: pysrt.SubRipFile
    ) -> (List[VideoFileClip], List[pysrt.SubRipItem]):
        subtitle_segments = []
        video_segments = []
        video_duration = video.duration

        for subtitle in subtitles:
            start = self.subriptime_to_seconds(subtitle.start)
            end = self.subriptime_to_seconds(subtitle.end)

            if start >= video_duration:
                logging.warning(
                    f"Subtitle start time ({start}) is beyond video duration ({video_duration}). Skipping this subtitle."
                )
                continue

            if end > video_duration:
                logging.warning(
                    f"Subtitle end time ({end}) exceeds video duration ({video_duration}). Clamping to video duration."
                )
                end = video_duration

            if end <= start:
                logging.warning(
                    f"Invalid subtitle duration: start ({start}) >= end ({end}). Skipping this subtitle."
                )
                continue

            video_segment = video.subclip(start, end)
            if video_segment.duration == 0:
                logging.warning(
                    f"Video segment duration is zero for subtitle ({subtitle.text}). Skipping this segment."
                )
                continue

            subtitle_segments.append(subtitle)
            video_segments.append(video_segment)

        return video_segments, subtitle_segments

    def adjust_segment_duration(
            self, 
            segment: VideoFileClip, 
            duration: float,
            strict: bool = True
        ) -> VideoFileClip:
            current_duration = segment.duration

            if duration < 0:
                raise ValueError("Target duration must be non-negative.")
            if current_duration == 0:
                raise ValueError("Segment duration is zero; cannot adjust.")

            # If durations are very close, still adjust to be exact
            if abs(current_duration - duration) < 1e-3:
                return segment.subclip(0, duration)

            adjusted_segment = None
            if current_duration < duration:
                # Calculate speed factor with a small buffer to prevent overshooting
                speed_factor = (current_duration / duration) * 0.999
                adjusted_segment = segment.fx(vfx.speedx, speed_factor)
            else:
                adjusted_segment = segment.subclip(0, duration)

            # When strict mode is enabled, force exact duration
            if strict:
                final_duration = adjusted_segment.duration
                if abs(final_duration - duration) > 0.001:
                    adjusted_segment = adjusted_segment.subclip(0, duration)
                
                # Verify the final duration
                if abs(adjusted_segment.duration - duration) > 0.001:
                    raise ValueError(
                        f"Failed to achieve target duration. "
                        f"Target: {duration:.3f}, Actual: {adjusted_segment.duration:.3f}"
                    )

            return adjusted_segment

    def get_video_paths_for_text_file(self):
        """
        Get a list of video paths for all TextLineVideoClip instances associated with the given text_file_instance.

        Args:

        Returns:
            List[str]: A list of video paths.
        """
        video_clips = TextLineVideoClip.objects.filter(
            text_file=self.text_file_instance
        )

        return [clip.video_file for clip in video_clips ]


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
            if not file_field or not file_field.name:
                raise ValueError("File field is empty or invalid.")
            file_extension = os.path.splitext(file_field.name)[1].lower()

            with tempfile.NamedTemporaryFile(suffix=file_extension, delete=False) as temp_file:
                file_content = download_from_s3(file_field.name, temp_file.name)

                if not file_content:
                    raise ValueError("Failed to download the video from S3.")
                clip=None
                with open(temp_file.name, "wb") as video_file:
                    video_file.write(file_content)
                if file_extension in VIDEO_EXTENSIONS:
                    clip = VideoFileClip(os.path.normpath(temp_file.name))
                elif file_extension in IMAGE_EXTENSIONS:
                    clip = ImageClip(os.path.normpath(temp_file.name))

                # Return the video clip
                return clip

        except Exception as e:
            logging.error(f"Error loading video from file field: {e}")
            raise

    def add_margin_based_on_aspect_ratio(self,clip, target_aspect_ratio):
        """
        Adds margins to a video clip to achieve the desired aspect ratio.
        
        Args:
            clip (VideoClip): The MoviePy VideoClip to process.
            target_aspect_ratio (float): The desired aspect ratio (width/height).
        
        Returns:
            VideoClip: The video clip with added margins.
        """
        original_width, original_height = clip.size
        original_aspect_ratio = original_width / original_height

        if abs(original_aspect_ratio - target_aspect_ratio) < 0.01:
            return clip 

        if original_aspect_ratio > target_aspect_ratio:
            new_height = int(original_width / target_aspect_ratio)
            margin =int((new_height - original_height) / 2)
            clip_with_margins = clip.margin(top=margin, bottom=margin)
        else:
            new_width = int(original_height * target_aspect_ratio)
            margin = int((new_width - original_width) / 2)
            clip_with_margins = clip.margin(left=margin, right=margin)

        return clip_with_margins

    def crop_to_aspect_ratio_(self, clip, desired_aspect_ratio):

        original_width, original_height = clip.size

        original_aspect_ratio = original_width / original_height

        if (
            abs(original_aspect_ratio - desired_aspect_ratio) < 0.01
        ):  
            return clip
        
        if desired_aspect_ratio==9/16:
            crop_width = original_height * 9/16

            cropped_clip = fix_all_crop(clip, width=600, height=5000, x_center=original_width/2, y_center=original_height/2)
            return cropped_clip
        
        if original_aspect_ratio > desired_aspect_ratio:
            new_width = int(original_height * desired_aspect_ratio)
            new_height = original_height
            x1 = (original_width - new_width) // 2 
            y1 = 0
        else:
            new_width = original_width
            new_height = int(original_width / desired_aspect_ratio)
            x1 = 0
            y1 = (original_height - new_height) // 2  

        x2 = x1 + new_width
        y2 = y1 + new_height

        return crop(clip, x1=x1, y1=y1, x2=x2, y2=y2)
    
    def is_image_clip(self,clip):
        """
        Checks if the provided MoviePy clip is an ImageClip.
        """
        return isinstance(clip, ImageClip)

    def is_video_clip(self,clip):
        """
        Checks if the provided MoviePy clip is a VideoFileClip.
        """
        return isinstance(clip, VideoFileClip)

    def concatenate_clips(self, clips, target_resolution=None, target_fps=30):
        processed_clips = []
        total_duration = 0

        for clip in clips:
            original_duration = clip.duration

            # Set frame rate
            clip = clip.set_fps(target_fps)

            # Ensure audio matches video duration
            if clip.audio:
                clip = clip.set_audio(clip.audio.subclip(0, min(clip.audio.duration, clip.duration)))

            # Ensure clip doesn't exceed its original duration
            clip = clip.subclip(0, original_duration)

            if abs(original_duration - clip.duration) > 0.1: 
                logging.warning(f"Clip duration changed from {original_duration} to {clip.duration}")

            total_duration += clip.duration
            processed_clips.append(clip)

        method = "chain" if all(c.size == processed_clips[0].size and c.fps == target_fps for c in processed_clips) else "compose"
        final_clip = concatenate_videoclips(processed_clips, method=method)

        # Trim final clip to expected duration
        expected_duration = sum(clip.duration for clip in processed_clips)
        final_clip = final_clip.subclip(0, min(final_clip.duration, expected_duration))

        logging.info(f"Clips concatenated successfully. Duration: {final_clip.duration}")
        return final_clip

    def resize_clips_to_max_size(self, clips):
        max_width = max(clip.w for clip in clips)
        max_height = max(clip.h for clip in clips)
        if self.text_file_instance.resolution=='9:16':
            resized_clips = [clip.resize(newsize=(720, 1280)) for clip in clips]

        else:
            resized_clips = [clip.resize(newsize=(max_width, max_height)) for clip in clips]

        return resized_clips
    
    def image_to_video(self,clip, duration):
        """
        Converts an ImageClip to a VideoClip with the specified duration.

        Args:
            image_clip (ImageClip): The MoviePy ImageClip to convert.
            duration (float): The duration of the resulting VideoClip in seconds.

        Returns:
            VideoClip: The converted VideoClip with the specified duration.
        """
        if self.is_video_clip(clip):
            return clip
        elif self.is_image_clip(clip):
            if duration <= 0:
                raise ValueError("Duration must be greater than 0.")
            
            # Set the duration for the ImageClip to make it a VideoClip
            video_clip = clip.set_duration(duration)
            return video_clip
        return None

    def replace_video_segments(
            self,
            original_segments: List[VideoFileClip],
            replacement_videos: Dict[int, VideoFileClip],
            subtitles: pysrt.SubRipFile,
            original_video: VideoFileClip,
        ) -> List[VideoFileClip]:
            combined_segments = original_segments.copy()
            for replace_index in range(len(replacement_videos)):
                if 0 <= replace_index < len(combined_segments):
                    # Get exact target duration from subtitle timings
                    start = self.subriptime_to_seconds(subtitles[replace_index].start)
                    end = self.subriptime_to_seconds(subtitles[replace_index].end)
                    target_duration = end - start  # Use exact subtitle duration instead of segment duration

                    replacement_segment = self.adjust_segment_duration(
                        replacement_videos[replace_index], 
                        duration=target_duration,
                        strict=True  # New parameter for strict duration control
                    )

                    adjusted_segment = self.adjust_segment_properties(
                        replacement_segment,
                        original_video,
                    )
                    adjusted_segment_with_subtitles = self.add_subtitles_to_clip(
                        adjusted_segment, subtitles[replace_index]
                    )
                    
                    # Verify final duration
                    if abs(adjusted_segment_with_subtitles.duration - target_duration) > 0.001:
                        adjusted_segment_with_subtitles = adjusted_segment_with_subtitles.subclip(
                            0, target_duration
                        )
                    
                    combined_segments[replace_index] = adjusted_segment_with_subtitles
            return combined_segments
    def adjust_segment_properties(
        self, segment: VideoFileClip, original: VideoFileClip
    ) -> VideoFileClip:
        segment = segment.set_fps(original.fps)
        segment = segment.set_duration(segment.duration)
        return segment

    def add_subtitles_to_clip(
            self, clip: VideoFileClip, subtitle: pysrt.SubRipItem
        ) -> VideoFileClip:
            logging.info(f"Adding subtitle: {subtitle.text}")
            subtitle_box_color = self.text_file_instance.subtitle_box_color
            
            scaling_factor = clip.h / 1080
            base_font_size = self.text_file_instance.font_size 
            if self.text_file_instance.resolution == '9:16' and base_font_size >40:
                base_font_size=40
            # if self.text_file_instance.resolution == '4:5' and base_font_size >35:
            #     base_font_size=35

            color = self.text_file_instance.font_color
            margin = 29
            box_radius = self.text_file_instance.box_radius
            subtitle_opacity = self.text_file_instance.subtitle_opacity
            font_path = self.text_file_instance.font
            
            x, y, z = mcolors.to_rgb(subtitle_box_color)
            subtitle_box_color = (x * 255, y * 255, z * 255)
            rectangle_color = (int(x * 255), int(y * 255), int(z * 255))
            
            font_size = int(base_font_size * scaling_factor)

            def wrap_text_dynamically(text: str, max_text_width: int, font_size: int, font: str, max_lines: int = 4) -> str:
                """
                Wraps text dynamically to fit within a specified maximum width and number of lines.
                If the text exceeds the maximum width, it reduces the font size and tries again.
                Ensures all text is included within the specified number of lines.

                Args:
                    text (str): The input text to wrap.
                    max_text_width (int): The maximum allowed width for the text.
                    font_size (int): The initial font size.
                    font (str): The font to use.
                    max_lines (int): The maximum number of lines allowed.

                Returns:
                    str: The wrapped text with adjusted font size.
                """
                words = text.split()
                min_font_size = 10  # Minimum font size to avoid making the text too small

                while font_size >= min_font_size:
                    lines = []
                    current_line = []
                    for word in words:
                        test_line = " ".join(current_line + [word])
                        test_clip = TextClip(test_line, fontsize=font_size, font=font)

                        if test_clip.w <= max_text_width:
                            current_line.append(word)
                        else:
                            if current_line:
                                lines.append(" ".join(current_line))
                            current_line = [word]

                            # If adding a new line exceeds max_lines, reduce font size and retry
                            if len(lines) >= max_lines:
                                break

                    # Add the last line if it exists
                    if current_line:
                        lines.append(" ".join(current_line))

                    # Check if all words are included and the number of lines is within the limit
                    if len(lines) <= max_lines and len(" ".join(lines).split()) == len(words):
                        return "\n".join(lines),font_size

                    # Reduce font size and try again
                    font_size -= 2  # Decrease font size by 2 (adjust as needed)

                # If the font size reaches the minimum and the text still doesn't fit, return the best effort
                return "\n".join(lines),font_size
            

            def split_text_two_lines(text: str, max_line_width: int=32) -> str:
                words = text.split()
                lines = []
                current_line = []
                current_length = 0

                for word in words:
                    if current_length + len(word) <= max_line_width:
                        current_line.append(word)
                        current_length += len(word) + 1  # +1 for the space
                    else:
                        lines.append(" ".join(current_line))
                        current_line = [word]
                        current_length = len(word) + 1

                if current_line:
                    lines.append(" ".join(current_line))

                return "\n".join(lines)

            if self.text_file_instance.resolution=='9:16':

                wrapped_text = split_text_two_lines(
                    subtitle.text 
                )
                print('wrapped_text, ',wrapped_text)
                tiktok= self.create_text_clips_for_tiktok(wrapped_text,color,clip)
                logging.info(f'Done with tiktok')
                return tiktok  
            max_text_width = clip.w*0.8 
            max_text_width_2=clip.w*0.9
            if self.text_file_instance.resolution=='16:9':
                max_text_width = clip.w*0.65
            elif self.text_file_instance.resolution=='1:1':
                max_text_width = clip.w*0.75

            
            elif self.text_file_instance.resolution=='4:5':
                max_text_width = clip.w*0.70
            

            max_line_width = max_text_width // (font_size // 2)
            
            
            if self.text_file_instance.resolution !='16:9':
                wrapped_text_1,font_size_1 = wrap_text_dynamically(

                        subtitle.text, 
                        max_text_width, 
                        font_size, 
                        self.text_file_instance.font,
                        2
                    )
                if font_size_1<font_size:
                    wrapped_text_1,font_size_1 = wrap_text_dynamically(

                        subtitle.text, 
                        max_text_width_2, 
                        font_size, 
                        self.text_file_instance.font,
                        2
                    )
            else:
                wrapped_text_1,font_size_1 = wrap_text_dynamically(
                    subtitle.text, 
                    max_text_width=max_text_width, 
                    font_size=font_size, 
                    font=self.text_file_instance.font,
                    max_lines=3
                )
            temp_subtitle_clip = TextClip(
                wrapped_text_1,
                fontsize=font_size_1,
                font=self.text_file_instance.font
            )
            longest_line_width, text_height = temp_subtitle_clip.size

            subtitle_clip = TextClip(
                wrapped_text_1,
                fontsize=font_size_1,
                color=color,
                stroke_width=0,
                font=self.text_file_instance.font,
                method="caption",
                align="center",
                size=(longest_line_width, None),
            ).set_duration(clip.duration)

            text_width, text_height = subtitle_clip.size
            small_margin = max(10, int(box_radius * 1.5))
            
            box_width = min(text_width + small_margin, clip.w * 0.92)

            box_height = text_height + margin
            rounded_box_array = self.create_rounded_rectangle(
                (int(box_width), 
                 int(box_height)), 
                 int(box_radius),
                 bg_color=self.text_file_instance.subtitle_box_color
                 )
            box_clip = ImageClip(rounded_box_array, ismask=False).set_duration(subtitle_clip.duration)

            safe_zone_offset = int(clip.h * 0.15) if self.text_file_instance.resolution == '9:16' else 0
            x_offset = 30 if self.text_file_instance.resolution == '9:16' else 0 

            box_position = (
                ("center", clip.h - box_height - 2 * margin - safe_zone_offset)
                if not x_offset else (x_offset, clip.h - box_height - 2 * margin - safe_zone_offset)
            )

            subtitle_x = x_offset + (box_width - text_width) // 2 if x_offset else "center"
            subtitle_y = clip.h - box_height - 2 * margin + (box_height - text_height) / 2 - safe_zone_offset

            subtitle_position = (subtitle_x, subtitle_y)

            box_clip = box_clip.set_position(box_position)
            subtitle_clip = subtitle_clip.set_position(subtitle_position)

            return CompositeVideoClip([clip, box_clip, subtitle_clip])


    def create_rounded_rectangle(self, size, radius,bg_color= '#ffffff',upscale_factor=20,):
        """Create an ultra-smooth RGBA rounded rectangle."""
        

        # High-resolution canvas
        upscale_size = (size[0] * upscale_factor, size[1] * upscale_factor)
        rectangle_color = ImageColor.getrgb(self.text_file_instance.subtitle_box_color) + (255,)
        
        img = Image.new("RGBA", upscale_size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw at higher resolution
        draw.rounded_rectangle((0, 0, upscale_size[0], upscale_size[1]), 
                            radius=radius * upscale_factor, 
                            fill=rectangle_color)

        # Apply Gaussian Blur for extra smoothness
        from PIL import   ImageFilter

        img = img.filter(ImageFilter.GaussianBlur(radius=upscale_factor / 2))

        # Downscale using high-quality Lanczos filter
        img = img.resize(size, Image.LANCZOS)

        return np.array(img)

    def render_text_with_emoji(self, text, font_size):
        """
        Renders text with emojis, using a custom font for text and ensuring emojis retain their default color.
        Emojis are rendered in their correct positions relative to the text.
        Text is centered horizontally.
        """

        # Load text color
        color = ImageColor.getrgb(self.text_file_instance.font_color) + (255,)

        # Load fonts
        text_font = ImageFont.truetype(os.path.join(os.getcwd(), 'fonts', 'tiktokfont.otf'), font_size)

        # Create a blank image (temporary, just for size calculation)
        image = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Get text bounding box to determine final image size
        text_width, text_height = draw.textbbox((0, 0), text, font=text_font)[2:]

        # Add padding for centering
        padding = 19
        image_width = text_width + 2 * padding # add double the padding for both sides

        # Create the final image with transparent background
        image = Image.new("RGBA", (image_width, text_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image) #create a new draw object for the new image

        # Calculate the horizontal center position
        x_center = image_width / 2

        # Calculate the starting x-coordinate for the text
        text_x = x_center - text_width / 2

        # Draw text with emojis
        with Pilmoji(image) as pilmoji:
            # Use the same font for both text and emojis
            pilmoji.text((int(text_x), 0), text, fill=color, font=text_font, emoji_position_offset=(-5, 5))

        # Convert PIL image to numpy array for MoviePy
        return np.array(image)
   
    def create_text_clips_for_tiktok(self, text, color, clip):
        lines = text.split("\n") 
        text_clips = []
        box_clips = []
        video_width, video_height = clip.size
        base_char_width = video_width * 0.0245
        max_allowed_width = int(video_width * 0.85)  
        total_text_height = 0
        text_clip_sizes = []
        box_padding = 16  
        apparent_padding = 0  
        x_padding = 0
        box_radius = 10
        font_size=40
        def contains_emoji(text):
            import emoji
            """
            Check if the given string contains any emojis.
            """
            for character in text:
                if character in emoji.UNICODE_EMOJI['en']:
                    return True
            return False



        for line in lines:
            if not line.strip():
                continue 
            # l_contain_emoji=contains_emoji(line)
            l_contain_emoji=False
            if not l_contain_emoji:
                x_padding=10
                # push_text_up=0


                text_clip = TextClip(       
                    line, 
                    font='tiktokfont', 
                    fontsize=font_size, 
                    color=color, 
                    align="center",
                )
            else:


                text_image = self.render_text_with_emoji(line.strip(), font_size=font_size, )

            # Create a TextClip from the rendered image
                text_clip = ImageClip(text_image,ismask=False)


            if text_clip.size:
                box_width, box_height = text_clip.size
                total_text_height += box_height
                text_clip_sizes.append((text_clip, box_width, box_height,l_contain_emoji))

        first_text_top = int(video_height * 0.7 - 18)
        y_offset = first_text_top
        push_text_up=5

        for idx, (text_clip, box_width, box_height,l_contain_emoji) in enumerate(text_clip_sizes):
            if idx > 0:
                apparent_padding = 15  # Set apparent padding after the first text clip

            rounded_box_array = self.create_rounded_rectangle(
                (int(box_width) + x_padding, int(box_height + box_padding + apparent_padding)), int(box_radius)
            )
            box_clip = ImageClip(rounded_box_array, ismask=False).set_duration(clip.duration)

            box_clip = box_clip.set_position(("center", y_offset-apparent_padding))

            text_clip = text_clip.set_position((
                "center", 
                y_offset + (box_height / 2) - (text_clip.size[1] / 2) + box_padding / 2 + (apparent_padding / 2 - 5 if apparent_padding != 0 else 0)-(push_text_up if l_contain_emoji else 0)

            )).set_duration(clip.duration)

            text_clips.append(text_clip)
            box_clips.append(box_clip)

            y_offset += box_height  -apparent_padding*2
            push_text_up=0

        return CompositeVideoClip([clip] + box_clips + text_clips)

    def add_static_watermark_to_instance(
        self,
    ):
        """
        Add a static watermark to the video from text_file_instance and save the result.
        """
        text_file_instance = self.text_file_instance
        video = self.load_video_from_file_field(
            text_file_instance.generated_final_video
        )

        watermark_s3_path = LogoModel.objects.first().logo.name

        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False
        ) as watermark_temp_path:
            content = download_from_s3(watermark_s3_path, watermark_temp_path.name)
            with open(watermark_temp_path.name, "wb") as png_file:
                png_file.write(content)

        try:
            watermark = (
                ImageClip(watermark_temp_path.name)
                .resize(width=video.w * 1.2)
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
                    codec='libx264',
                    preset="ultrafast",
                    audio_codec="aac",
                    fps=30,
                    
                    # temp_audiofile='temp-audio.m4a', 
                    # remove_temp=True
                )
                self.text_file_instance.track_progress(95)

                # Save the watermarked video to the model field
                if text_file_instance.generated_watermarked_video:
                    text_file_instance.generated_watermarked_video.delete(save=False)
                    self.text_file_instance.track_progress(97)

                with open(temp_output_video.name, "rb") as temp_file:
                    text_file_instance.generated_watermarked_video.save(
                        f"watermarked_output_{self.generate_random_string(5)}-{text_file_instance.id}.mp4",
                        ContentFile(temp_file.read()),
                    )
                    self.text_file_instance.track_progress(99)

            logging.info("Watermarked video generated successfully.")
            # time.sleep(5)

            self.text_file_instance.track_progress(100)

            return True

        except Exception as e:
            logging.error(f"Error generating watermarked video: {e}")
            return False
