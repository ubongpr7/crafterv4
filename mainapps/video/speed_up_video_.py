import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

import tempfile
# import moviepy.editor as mp


# def process_video_speed(video_file, speed):
#     try:
#         # Save uploaded file to a temporary location
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
#             for chunk in video_file.chunks():
#                 temp_file.write(chunk)
#             temp_file_path = temp_file.name

#         # Load the video
#         video_clip = mp.VideoFileClip(temp_file_path)

#         # Ensure duration is set
#         if not video_clip.duration:
#             raise ValueError("Invalid video file: No duration found.")

#         # Extract audio
#         if video_clip.audio:
#             audio_clip = video_clip.audio.fx(mp.vfx.speedx, speed)  # Speed up audio
#         else:
#             audio_clip = None

#         # Speed up video (without audio)
#         sped_up_video = video_clip.fx(mp.vfx.speedx, speed)

#         # Attach the processed audio back
#         if audio_clip:
#             sped_up_video = sped_up_video.set_audio(audio_clip)

#         # Save processed video to another temp file
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as output_file:
#             processed_video_path = output_file.name

#         sped_up_video.write_videofile(
#             processed_video_path, 
#             codec='libx264', 
#             audio_codec='aac'
#         )

#         # Clean up
#         video_clip.close()
#         sped_up_video.close()
#         if audio_clip:
#             audio_clip.close()

#         return processed_video_path

#     except Exception as e:
#         print(f"Error processing video: {e}")
#         return None
import tempfile
import subprocess

def process_video_speed(video_file, speed):
    try:
        # Save uploaded file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_file:
            for chunk in video_file.chunks():
                temp_file.write(chunk)
            temp_file_path = temp_file.name

        # Create temp output file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as output_file:
            processed_video_path = output_file.name

        # FFmpeg command
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", temp_file_path,
            "-filter_complex",
            f"[0:v]setpts={1/speed}*PTS[v];[0:a]atempo={speed}[a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k",
            processed_video_path
        ]

        # Run FFmpeg
        subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        return processed_video_path

    except subprocess.CalledProcessError as e:
        print(f"FFmpeg error: {e.stderr.decode()}")
        return None

def cleanup_processed_video(processed_video_path):
    """
    Cleans up the processed video file.

    Args:
        processed_video_path: The path to the processed video file.
    """
    if os.path.exists(processed_video_path):
        logger.info("Deleting processed video file: %s", processed_video_path)
        os.remove(processed_video_path)
    else:
        logger.warning("Processed video file not found for cleanup: %s", processed_video_path)
