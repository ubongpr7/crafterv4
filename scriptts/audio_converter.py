import os
import subprocess
from django.core.files.storage import default_storage
from django.shortcuts import render
# from mainapps.vidoe_text.models import TextFile, VideoClip
# from elevenlabs import Voice, VoiceSettings, generate
# from django.conf import settings


def align_text_audio(request):
    if request.method == "POST":
        audio_file = request.FILES["audio"]
        script_file = request.FILES["script"]

        # Save audio and text file
        audio_path = default_storage.save(
            os.path.join("tmp", audio_file.name), audio_file
        )
        script_path = default_storage.save(
            os.path.join("tmp", script_file.name), script_file
        )

        # Define paths for output files
        output_srt_file_path = script_path.replace(".txt", "_aligned.json")

        # Run Aeneas command
        command = f'python3.10 -m aeneas.tools.execute_task "{audio_path}" "{script_path}" "task_language=eng|is_text_type=plain|os_task_file_format=json" "{output_srt_file_path}"'
        result = subprocess.run(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        # Check result and display output
        if result.returncode == 0:
            return render(
                request, "success.html", {"output": result.stdout.decode("utf-8")}
            )
        else:
            return render(
                request, "error.html", {"error": result.stderr.decode("utf-8")}
            )

    return render(request, "upload.html")
