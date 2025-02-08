from django.http import JsonResponse
from django.views import View
from django.core.management import call_command
from .models import TextFile


class ProcessVideoView(View):
    def post(self, request, *args, **kwargs):
        text_file_id = request.POST.get("text_file_id")

        if not text_file_id:
            return JsonResponse({"error": "text_file_id is required."}, status=400)

        try:
            call_command("process_video", text_file_id)
            return JsonResponse(
                {"success": f"Processing initiated for text file {text_file_id}."}
            )
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)


from django.core.files.base import ContentFile


def convert_text_to_speech(self, text_file_path, voice_id, api_key, output_audio_file):
    # Convert text to speech as you did before
    audio_data = b"".join(audio_data_generator)  # This is the audio data

    # Instead of manually saving the file, save it using Django's FileField
    audio_file_name = f"{timestamp}_{text_file_id}_audio.mp3"
    text_file_instance.generated_audio.save(audio_file_name, ContentFile(audio_data))

    return (
        text_file_instance.generated_audio.url
    )  # This will return the URL managed by Django's FileField


# In the handle function:
audio_file_url = self.convert_text_to_speech(
    text_file, voice_id, api_key, output_audio_file
)

# No need to manually assign the URL, it will be managed by the FileField
text_file_instance.save()


import time
from django.utils import timezone


def main():
    # Existing argument parsing...

    # Use the current timestamp for unique filenames
    timestamp = int(time.time())
    original_filename = os.path.splitext(os.path.basename(text_file))[0]

    # Save audio file
    output_audio_file = os.path.join(
        base_path, "text_audio", f"{original_filename}_{timestamp}_audio.mp3"
    )
    audio_file = convert_text_to_speech(text_file, voice_id, api_key, output_audio_file)

    # Save SRT file
    output_srt_file_path = os.path.join(
        base_path, "srt_files", f"{original_filename}_{timestamp}_srt_output.json"
    )
    srt_file_path = generate_srt_file(audio_file, text_file, output_srt_file_path)

    # Process and save blank video
    blank_vide_path = os.path.join(
        base_path, f"blank_vide_{original_filename}_{timestamp}.mp4"
    )
    blank_vide = generate_blank_video_with_audio(
        audio_file, srt_file_path, blank_vide_path, resolution
    )

    # Final video file paths
    output_file = os.path.join(
        base_path, "final", f"final_output_{original_filename}_{timestamp}.mp4"
    )
    watermarked_path = os.path.join(
        base_path,
        "final",
        "w",
        f"final_output_{original_filename}_{timestamp}_watermarked.mp4",
    )

    # Write the final video file with audio
    final_video_speeded_up_clip.write_videofile(
        os.path.normpath(output_file),
        preset="ultrafast",
        codec="libx264",
        audio_codec="aac",
        temp_audiofile="temp-audio.m4a",
        remove_temp=True,
    )

    # Save file references to the TextFile instance
    text_file_instance = TextFile.objects.get(id=textfile_id)
    text_file_instance.generated_audio = output_audio_file
    text_file_instance.generated_srt = output_srt_file_path
    text_file_instance.generated_blank_video = blank_vide_path
    text_file_instance.generated_final_video = output_file
    text_file_instance.generated_watermarked_video = watermarked_path

    # Save the instance to update the database
    text_file_instance.save()

    update_progress(100, dir_s)


if __name__ == "__main__":
    main()
