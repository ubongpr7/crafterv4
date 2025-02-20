import json
import subprocess
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from mainapps.audio.models import BackgroundMusic
from mainapps.video.models import ClipCategory, VideoClip
from mainapps.vidoe_text.decorators import (
    check_credits_and_ownership,
    check_user_credits,
)
from mainapps.vidoe_text.video_converter import  convert_mov_to_mp4
from .models import SubClip, TextFile, TextLineVideoClip
from .forms import TextFileUpdateForm
from django.core.files.storage import default_storage

import os
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse, Http404
from django.conf import settings
from django.urls import reverse
import logging
import requests
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.core.files.base import ContentFile
import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError
from django.apps import apps
import tempfile


@csrf_exempt
def update_subtitle_positions(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            subtitles = data.get("subtitles", [])

            for subtitle in subtitles:
                TextLineVideoClip.objects.filter(id=subtitle["id"]).update(position=subtitle["position"])

            return JsonResponse({"message": "Success"}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse({"error": "Invalid request"}, status=400)

# views.py

def check_subtitles_length(request, text_file_id):
    text_file = get_object_or_404(TextFile, id=text_file_id)

    subtitles = text_file.video_clips.all()

    total_characters = sum(len(subtitle.slide) for subtitle in subtitles)

    if total_characters > 5000:
        return JsonResponse({'status': 'error', 'message': 'Character limit exceeded!'})
    
    return JsonResponse({'status': 'success', 'message': 'Character limit okay.'})



@csrf_exempt 
def add_text_clip_line(request, textfile_id):
    try:
        textfile = TextFile.objects.get(id=textfile_id)
    except TextFile.DoesNotExist:
        return JsonResponse({"success": False, "error": "TextFile not found"}, status=404)

    if request.method == "POST":
        try:
            data = json.loads(request.body) 
            slide_text = data.get('text')  
            # position = data.get('position')  

            if not slide_text:
                return JsonResponse({"success": False, "error": "Slide text is required"}, status=400)
            clip = TextLineVideoClip.objects.create(
                text_file=textfile,
                slide=slide_text,
                remaining=slide_text,
                # position=position
            )
            return JsonResponse({"success": True, "id": clip.id,'new':True})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON payload"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)


@csrf_exempt 
def edit_text_clip_line(request, id):
    clip = TextLineVideoClip.objects.get(id=id )

    if request.method == "POST":
        try:
            data = json.loads(request.body) 
            slide_text = data.get('text') 

            if not slide_text:
                return JsonResponse({"success": False, "error": "Slide text is required"}, status=400)
            # elif slide_text != clip.slide:
            clip.slide=slide_text
            clip.remaining=slide_text
            clip.save()
            for subclip in clip.subclips.all():
                subclip.delete()
            return JsonResponse({"success": True, "id": clip.id,"changed":True})

        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON payload"}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method"}, status=405)



@require_http_methods(["DELETE"])
def delete_clip(request, id):
    try:
        clip = get_object_or_404(TextLineVideoClip, id=id)
        if clip.video_file:
            clip.video_file.delete()
        clip.delete()

        return JsonResponse({"message": "Music deleted successfully!"}, status=200)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def get_subclip_data(request, subclip_id):
    text=request.GET.get('text')
    clip = get_object_or_404(TextLineVideoClip, id=subclip_id)
    subclip = SubClip.objects.filter(subtittle=text,main_line=clip).values("id")
    
    return JsonResponse( safe=False)

def get_clips_id(request, textfile_id):
    text_file = get_object_or_404(TextFile, id=textfile_id)
    clips = TextLineVideoClip.objects.filter(text_file=text_file).values("id")
    
    clip_ids = [clip["id"] for clip in clips]
    return JsonResponse(clip_ids, safe=False)

def add_subclip(request, id):
    text_clip = get_object_or_404(TextLineVideoClip, id=id)

    if request.method == "POST":
        textfile_id = request.POST.get('textfile_id')
        remaining = request.POST.get('remaining')
        file_ = request.FILES.get('slide_file')
        text = request.POST.get('slide_text')
        asset_clip_id = request.POST.get('selected_video')

        subclip = None  # Initialize variable for created subclip
        video_data=None
        if file_:
            subclip = SubClip.objects.create(
                subtittle=text,
                video_file=file_,
                main_line=text_clip
            )
        elif asset_clip_id:
            video = get_object_or_404(VideoClip, id=asset_clip_id)
            subclip = SubClip.objects.create(
                subtittle=text,
                video_clip=video,
                main_line=text_clip
            )
            video_data = {"id": video.id, "name": video.name}  # Add video data
        if subclip:
            # Update the text_clip remaining field
            text_clip.remaining = remaining
            text_clip.save()

            # Return the created SubClip data as JSON
            video_clip_id=''
            cat_id=''
            if subclip.video_clip:
                video_clip_id=subclip.video_clip.id
                cat_id=subclip.video_clip.category.id

            return JsonResponse({
                "success": True,
                "subclip_id": subclip.id,
                "current_file": subclip.get_video_file_name(),
                "video_clip_id": video_clip_id,
                "cat_id": cat_id,
                "video_data":video_data,
                "main_id": id,
            })

        return JsonResponse({"success": False, "error": "Failed to create subclip."}, status=400)

    return JsonResponse({"success": False, "error": "Invalid request method."}, status=400)



def add_subcliphtmx(request, id):
    text_clip = get_object_or_404(TextLineVideoClip, id=id)

    video_categories = ClipCategory.objects.filter(user=request.user).values("id", "name", "parent_id")
    if request.method == "POST":
        remaining = request.POST.get("remaining")
        file_ = request.FILES.get("slide_file")
        text = request.POST.get("slide_text")
        asset_clip_id = request.POST.get("selected_video")

        subclip = None

        if file_:
            file_extension = os.path.splitext(file_.name)[1].lower()

            if file_extension == ".mov":
                try:
                    # Convert .mov to .mp4
                    converted_file_path = convert_mov_to_mp4(file_)

                    # Save converted file to SubClip
                    with open(converted_file_path, "rb") as converted_file:
                        file_content = converted_file.read()
                        subclip = SubClip.objects.create(
                            subtittle=text,
                            video_file=ContentFile(file_content, name=os.path.basename(converted_file_path)),
                            main_line=text_clip,
                        )

                    # Cleanup the converted file
                    os.remove(converted_file_path)
                except Exception as e:
                    print(e)
                    return JsonResponse({"success": False, "error": str(e)}, status=500)
            else:
                subclip = SubClip.objects.create(
                    subtittle=text,
                    video_file=file_,
                    main_line=text_clip,
                )
        elif asset_clip_id:
            video = get_object_or_404(VideoClip, id=asset_clip_id)
            subclip = SubClip.objects.create(
                subtittle=text,
                video_clip=video,
                main_line=text_clip,
            )

        if subclip:
            text_clip.remaining = remaining
            text_clip.save()

            return JsonResponse(
                {
                    "success": True,
                    "id": subclip.id,
                    "current_file": subclip.get_video_file_name(),
                    "video_clip": subclip.get_video_clip_id(),
                }
            )
        return JsonResponse({"success": False, "error": "Failed to create subclip."}, status=400)

    selected_text = request.GET.get("selectedText")
    remaining_text = request.GET.get("remainingText")
    return render(
        request,
        "vlc/frontend/VLSMaker/test_scene/subclipform.html",
        {
            "clipId": id,
            "categories": video_categories,
            "selected_text": selected_text,
            "remaining_text": remaining_text,
        },
    )


def edit_subcliphtmx(request,id):
    video_categories = ClipCategory.objects.filter(user=request.user).values("id", "name", "parent_id")
    videos=None
    subclip= SubClip.objects.get(id= id)
    if subclip.video_clip:
        cat=subclip.video_clip.category
        videos =VideoClip.objects.filter(category=cat).values('id','title')
    if request.method =='POST':
        file_=request.FILES.get(f'slide_file')
        asset_clip_id=request.POST.get(f'selected_video')
        if subclip.video_file:
            subclip.video_file.delete(save=False)
        subclip.video_clip=None
        if file_:
            file_extension = os.path.splitext(file_.name)[1].lower()

            if file_extension == ".mov":
                try:
                    converted_file_path = convert_mov_to_mp4(file_)

                    with open(converted_file_path, "rb") as converted_file:
                        file_content = converted_file.read()
                        subclip.video_file=ContentFile(file_content, name=os.path.basename(converted_file_path))


                    os.remove(converted_file_path)
                except Exception as e:
                    print(e)
                    return JsonResponse({"success": False, "error": str(e)}, status=500)
            else:
                subclip.video_file=file_
        elif asset_clip_id:
            video= VideoClip.objects.get(id=asset_clip_id)
            subclip.video_clip=video
        subclip.save()

        return JsonResponse({
            "success": True,
            "id": subclip.id,
                "current_file": subclip.get_video_file_name(),
            "video_clip":subclip.get_video_clip_id(),
            
            
        })
    return render(request,'vlc//frontend/VLSMaker/test_scene/edit_subclip.html',{'videos':videos,'categories':video_categories,'subclip':subclip})


def delete_textfile(request, textfile_id):
    textfile=TextFile.objects.get(id=textfile_id)
    if request.method=='POST':
        try:
            textfile.delete()

            return HttpResponse(status=204)
        except Exception as e:
            pass 

    return render(request, "partials/confirm_delete.html", {"item":textfile })

# def manage_textfile(request):
#     user =request.user
#     textfiles=TextFile.objects.filter(user=user)
#     return render(request,'assets/text_files.html', {'textfiles':textfiles})

def manage_textfile(request):
    user = request.user
    textfiles = TextFile.objects.filter(user=user).values("id", "created_at")
    
    for textfile in textfiles:
        textfile["get_clip_number"] = TextFile.objects.get(id=textfile["id"]).get_clip_number()

    return render(request, "assets/text_files.html", {"textfiles": textfiles})

def edit_subclip(request,id):
    if request.method =='POST':
        subclip= SubClip.objects.get(id= id)
        textfile_id=request.POST.get('textfile_id')
        file_=request.FILES.get(f'slide_file')
        asset_clip_id=request.POST.get(f'selected_video')
        if subclip.video_file:
            subclip.video_file.delete(save=False)
        subclip.video_clip=None
        if file_:
            subclip.video_file=file_
        elif asset_clip_id:
            video= VideoClip.objects.get(id=asset_clip_id)
            subclip.video_clip=video
        subclip.save()

        
        video_clip_id=''
        cat_id=''
        if subclip.video_clip:

            video_clip_id=subclip.video_clip.id
            cat_id=subclip.video_clip.category.id

        return JsonResponse({
            "success": True,
            "subclip_id": subclip.id,
            "current_file": subclip.get_video_file_name(),
            "video_clip_id": video_clip_id,
            "cat_id": cat_id,
            "main_id": subclip.main_line.id,
        })

    return JsonResponse({"success": False, "error": "Failed to create subclip."}, status=400)


@csrf_exempt
def reset_subclip(request, id):
    if request.method == 'POST':
        textfile_id = request.POST.get('textfile_id')
        text_clip = TextLineVideoClip.objects.get(id=id)
        text_clip.remaining=text_clip.slide
        text_clip.save()
        for subclip in text_clip.subclips.all():
            if subclip.video_file:
                subclip.video_file.delete(save=True)
            subclip.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)

def check_text_clip(request,textfile_id):
    textfile=TextFile.objects.get(id=textfile_id)
    ids_of_no_subclip=[]
    for clip in textfile.video_clips.all():
        if not clip.remaining.strip()=='':
            ids_of_no_subclip.append(clip.id)
    return JsonResponse(ids_of_no_subclip,safe=False)

@require_http_methods(["DELETE"])
def delete_background_music(request, id):
    try:
        # Get the BackgroundMusic object with the given id
        background_music = get_object_or_404(BackgroundMusic, id=id)

        # Delete the object
        background_music.music.delete()
        background_music.delete()

        # Return a success response
        return JsonResponse({"message": "Music deleted successfully!"}, status=200)
    except Exception as e:
        # Return an error response in case something goes wrong
        return JsonResponse({"error": str(e)}, status=400)


def check_credits(api_key):
    url = "https://api.elevenlabs.io/v1/usage/character-stats"

    headers = {
        "xi-api-key": api_key,
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        remaining_credits = response.json()


        print(f"Remaining Credits: {remaining_credits}")
        return f"Remaining Credits: {remaining_credits}"
    else:
        print(f"Failed to fetch user info. Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def is_api_key_valid(api_key, voice_id):
    """
    Checks if the given ElevenLabs API key is valid.

    Args:
        api_key (str): The ElevenLabs API key to check.

    Returns:
        bool: True if the API key is valid, False otherwise.
    """
    endpoint_url = f"https://api.elevenlabs.io/v1/voices"
    endpoint_url_2 = f"https://api.elevenlabs.io/v1/voices/{voice_id}"

    headers = {
        "Accept": "application/json",
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    x, y = False, False
    try:
        response = requests.get(endpoint_url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx and 5xx)
        # Check p response content or status code to determine validity
        if response.status_code == 200:
            x = True

    except requests.RequestException as e:
        print(f"Error checking API key: {e}")
    try:
        response_2 = requests.get(endpoint_url_2, headers=headers)
        if response_2.status_code == 200:
            y = True

    except requests.RequestException as e:
        print(f"Error checking API key: {e}")

    return x, y


def convert_to_seconds(time_str):
    try:
        minutes, seconds = map(float, time_str.split(":"))
        return minutes * 60 + seconds
    except ValueError:
        return 0.0  # Return 0 or handle error as needed


def format_seconds_to_mm_ss(seconds):
    """Convert seconds to mm:ss format."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02}:{secs:02}"


def serve_file(request, file_name):
    file_path = os.path.join(settings.MEDIA_ROOT, file_name)

    if not os.path.exists(file_path):
        raise Http404("File does not exist")

    with open(file_path, "rb") as f:
        response = HttpResponse(f.read(), content_type="application/octet-stream")
        response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return response


@login_required
@check_credits_and_ownership(textfile_id_param="textfile_id", credits_required=1)
def process_background_music(request, textfile_id):
    # Run process_video command in a new thread
    def run_process_command(textfile_id):
        try:
            call_command("music_processor", textfile_id)
        except Exception as e:
            # Handle the exception as needed (e.g., log it)
            print(f"Error processing video: {e}")

    textfile = TextFile.objects.get(pk=textfile_id)
    textfile.progress = "0"
    textfile.save()
    musics = textfile.background_musics.all()
    n_musics = len(musics)

    if request.method == "POST" :
        if not textfile.text_file:
            return JsonResponse({"error": "Text file is missing."}, status=400)
        
        no_of_mp3 = int(request.POST.get("no_of_mp3", 0))  # Number of MP3 files
        for music in textfile.background_musics.all():
            music_file=request.FILES.get(f'saved-mp3-{music.id}')
            start=request.POST.get(f'saved-starts-{music.id}')
            end=request.POST.get(f'saved-ends-{music.id}')
            volume=request.POST.get(f'saved-volume-{music.id}')
            if music_file:
                music.music.delete(save=False)
                music.music=music_file
            if start:
                music.start_time=convert_to_seconds(start)
            if end:
                music.end_time=convert_to_seconds(end)
            if volume:
                music.bg_level=float(volume)/1000.0
            music.save()



        music_files = []
        music_files_dict = {}
        start_times_str = {}
        bg_levels = {}
        end_times_str = {}

        for i in range(1, no_of_mp3 + 1):
            music_file = request.FILES.get(f"bg_music_{i}")
            if music_file is not None:
                music_files.append(music_file)
                music_files_dict[f"bg_music_{i}"] = music_file

            start_time = request.POST.get(f"from_when_{i}")
            if start_time is not None:
                start_times_str[f"bg_music_{i}"] = start_time

            bg_level = request.POST.get(f"bg_level_{i}")
            if bg_level is not None:
                bg_levels[f"bg_music_{i}"] = float(bg_level) / 1000.0

            end_time = request.POST.get(f"to_when_{i}")
            if end_time is not None:
                end_times_str[f"bg_music_{i}"] = end_time

        start_times = [
            convert_to_seconds(time_str) for time_str in start_times_str.values()
        ]
        end_times = [
            convert_to_seconds(time_str) for time_str in end_times_str.values()
        ]

        bg_musics = []
        for i in range(1, no_of_mp3 + 1):
            if music_files_dict.get(f"bg_music_{i}"):
                bg_music = BackgroundMusic(
                    text_file=textfile,
                    music=music_files_dict[f"bg_music_{i}"],
                    start_time=convert_to_seconds(start_times_str[f"bg_music_{i}"]),
                    end_time=convert_to_seconds(end_times_str[f"bg_music_{i}"]),
                    bg_level=bg_levels[f"bg_music_{i}"],
                )

                bg_musics.append(bg_music)
        if bg_musics:
            BackgroundMusic.objects.bulk_create(bg_musics)
        
        lines = []
        bg_musics_updated=textfile.background_musics.all()

        for bg_music in bg_musics_updated:
            start_time_str = bg_music.start_time
            end_time_str = bg_music.end_time
            bg_level = str(float(bg_music.bg_level))
            lines.append(
                f"{bg_music.music.name} {start_time_str} {end_time_str} {bg_level}"
            )

        content = "\n".join(lines)

        file_name = f"background_music_info_{textfile_id}_.txt"

        textfile.bg_music_text.save(file_name, ContentFile(content))
        textfile.save()

        try:
            thread = threading.Thread(target=run_process_command, args=(textfile_id,))
            thread.start()
            return redirect(f"/text/progress_page/bg_music/{textfile_id}")

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    

    return render(
        request,
        "vlc/add_music.html",
        {
            "textfile_id": textfile_id,
            "textfile": textfile,
            "musics": musics,
            "n_musics": n_musics,
        },
    )

# def process_background_music(request, textfile_id):
#     # Run process_video command in a new thread
#     def run_process_command(textfile_id):
#         try:
#             call_command("music_processor", textfile_id)
#         except Exception as e:
#             # Handle the exception as needed (e.g., log it)
#             print(f"Error processing video: {e}")

#     textfile = TextFile.objects.get(pk=textfile_id)
#     textfile.progress = "0"
#     textfile.save()
#     musics = textfile.background_musics.all()
#     n_musics = len(musics)

#     if request.method == "POST" and request.POST.get("purpose") == "new":
#         if textfile.background_musics:
#             for bg in BackgroundMusic.objects.filter(text_file=textfile):
#                 bg.delete()
#         try:
#             # Fetch the TextFile instance
#             if textfile.user != request.user:
#                 messages.error(
#                     request, "You Do Not Have Access To The Resources You Requested "
#                 )

#                 return render(request, "permission_denied.html")
#         except TextFile.DoesNotExist:
#             return Http404("Text file not found")
#         no_of_mp3 = int(request.POST.get("no_of_mp3", 0))  # Number of MP3 files

#         # Check if the necessary fields are present in TextFile
#         if not textfile.text_file:
#             return JsonResponse({"error": "Text file is missing."}, status=400)
#         # Check for text file and return error if missing
#         music_files = []
#         music_files_dict = {}
#         start_times_str = {}
#         bg_levels = {}
#         end_times_str = {}

#         # Loop through each item based on the number of MP3s
#         for i in range(1, no_of_mp3 + 1):
#             # Get the music file and check if it's not None before adding to the list
#             music_file = request.FILES.get(f"bg_music_{i}")
#             if music_file is not None:
#                 music_files.append(music_file)
#                 music_files_dict[f"bg_music_{i}"] = music_file

#             # Get start time and check if it's not None before adding to the dictionary
#             start_time = request.POST.get(f"from_when_{i}")
#             if start_time is not None:
#                 start_times_str[f"bg_music_{i}"] = start_time

#             # Get background level and check if it's not None before adding to the dictionary
#             bg_level = request.POST.get(f"bg_level_{i}")
#             if bg_level is not None:
#                 bg_levels[f"bg_music_{i}"] = float(bg_level) / 1000.0

#             # Get end time and check if it's not None before adding to the dictionary
#             end_time = request.POST.get(f"to_when_{i}")
#             if end_time is not None:
#                 end_times_str[f"bg_music_{i}"] = end_time

#         start_times = [
#             convert_to_seconds(time_str) for time_str in start_times_str.values()
#         ]
#         end_times = [
#             convert_to_seconds(time_str) for time_str in end_times_str.values()
#         ]

#         # Save music files and their paths
#         bg_musics = []
#         for i in range(1, no_of_mp3 + 1):
#             if music_files_dict.get(f"bg_music_{i}"):
#                 bg_music = BackgroundMusic(
#                     text_file=textfile,
#                     music=music_files_dict[f"bg_music_{i}"],
#                     start_time=convert_to_seconds(start_times_str[f"bg_music_{i}"]),
#                     end_time=convert_to_seconds(end_times_str[f"bg_music_{i}"]),
#                     bg_level=bg_levels[f"bg_music_{i}"],
#                 )

#                 bg_musics.append(bg_music)
#                 # Perform bulk creation
#         if bg_musics:
#             BackgroundMusic.objects.bulk_create(bg_musics)

#         lines = []
#         for bg_music in bg_musics:
#             start_time_str = bg_music.start_time
#             end_time_str = bg_music.end_time
#             bg_level = str(float(bg_music.bg_level))
#             lines.append(
#                 f"{bg_music.music.name} {start_time_str} {end_time_str} {bg_level}"
#             )

#         content = "\n".join(lines)

#         file_name = f"background_music_info_{textfile_id}_.txt"

#         textfile.bg_music_text.save(file_name, ContentFile(content))
#         textfile.save()

#         try:
#             thread = threading.Thread(target=run_process_command, args=(textfile_id,))
#             thread.start()
#             return redirect(f"/text/progress_page/bg_music/{textfile_id}")

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)
#     elif request.method == "POST" and request.POST.get("purpose") == "update":
#         no_of_mp3 = int(request.POST.get("no_of_mp3", 0))

#         # Check if the necessary fields are present in TextFile
#         if not textfile.text_file:
#             return JsonResponse({"error": "Text file is missing."}, status=400)
#         # Check for text file and return error if missing
#         for music in textfile.background_musics.all():
#             music_file=request.POST.get(f'saved-mp3-{music.id}')
#             start=request.POST.get(f'saved-starts-{music.id}')
#             end=request.POST.get(f'saved-ends-{music.id}')
#             volume=request.POST.get(f'saved-volume-{music.id}')
#             if music_file:
#                 music.music.delete(save=False)
#                 music.music=music_file
#             if start:
#                 music.start_time=convert_to_seconds(start)
#             if end:
#                 music.end_time=convert_to_seconds(end)
#             if volume:
#                 music.bg_level=float(volume)/1000.0
#             music.save()

#         music_files = []
#         music_files_dict = {}
#         start_times_str = {}
#         bg_levels = {}
#         end_times_str = {}

#         for i in range(1, no_of_mp3 + 1):
#             # Get the music file and check if it's not None before adding to the list
#             changed_music_file = request.FILES.get(f"bg_music_{i}")
#             if changed_music_file is not None:
#                 music_files.append(changed_music_file)
#                 music_files_dict[f"bg_music_{i}"] = changed_music_file

#             # Get start time and check if it's not None before adding to the dictionary
#             start_time = request.POST.get(f"from_when_{i}")
#             if start_time is not None:
#                 start_times_str[f"bg_music_{i}"] = start_time

#             # Get background level and check if it's not None before adding to the dictionary
#             bg_level = request.POST.get(f"bg_level_{i}")
#             if bg_level is not None:
#                 bg_levels[f"bg_music_{i}"] = float(bg_level) / 1000.0

#             # Get end time and check if it's not None before adding to the dictionary
#             end_time = request.POST.get(f"to_when_{i}")
#             if end_time is not None:
#                 end_times_str[f"bg_music_{i}"] = end_time

#         start_times = [
#             convert_to_seconds(time_str) for time_str in start_times_str.values()
#         ]
#         end_times = [
#             convert_to_seconds(time_str) for time_str in end_times_str.values()
#         ]
#         bg_musics = []

#         for i in range(n_musics, no_of_mp3 + 1):
#             logging.info(f"This is i: {i}")
#             if music_files_dict.get(f"bg_music_{i}"):
#                 bg_music = BackgroundMusic(
#                     text_file=textfile,
#                     music=music_files_dict.get(f"bg_music_{i}"),
#                     start_time=convert_to_seconds(start_times_str[f"bg_music_{i}"]),
#                     end_time=convert_to_seconds(end_times_str[f"bg_music_{i}"]),
#                     bg_level=bg_levels[f"bg_music_{i}"],
#                 )
#                 try:
#                     bg_music.save()  # Save each object individually
#                 except Exception as e:
#                     logging.error(f"Error saving background music {i}: {e}")
#                     return JsonResponse(
#                         {"error": f"Error saving background music {i}: {str(e)}"},
#                         status=500,
#                     )

#         for i, music in enumerate(musics, start=1):
#             if music_files_dict.get(f"bg_music_{i}"):
#                 music.music.delete(save=False)
#                 music.music = music_files_dict.get(f"bg_music_{i}")
#             music.start_time = start_times[i - 1]
#             music.end_time = end_times[i - 1]
#             music.bg_level = bg_levels[f"bg_music_{i}"]
#             music.save()

#         lines = []
#         all_bg_musics = BackgroundMusic.objects.filter(text_file=textfile)

#         for bg_music in all_bg_musics:
#             start_time_str = bg_music.start_time
#             end_time_str = bg_music.end_time
#             bg_level = str(float(bg_music.bg_level))
#             lines.append(
#                 f"{bg_music.music.name} {start_time_str} {end_time_str} {bg_level}"
#             )

#         content = "\n".join(lines)

#         # Save the content to a text file
#         file_name = f"background_music_info_{textfile_id}_.txt"

#         textfile.bg_music_text.save(file_name, ContentFile(content))
#         # textfile.bg_level=float(request.POST.get('bg_level'))/100.0
#         textfile.save()

#         try:
#             # call_command('music_processor', textfile_id)
#             # # Start the background process/
#             thread = threading.Thread(target=run_process_command, args=(textfile_id,))
#             thread.start()
#             return redirect(f"/text/progress_page/bg_music/{textfile_id}")

#         except Exception as e:
#             return JsonResponse({"error": str(e)}, status=500)

#     return render(
#         request,
#         "vlc/add_music.html",
#         {
#             "textfile_id": textfile_id,
#             "textfile": textfile,
#             "musics": musics,
#             "n_musics": n_musics,
#         },
#     )


def clean_progress_file(text_file_id):
    """Deletes the progress file after 3 seconds when progress is 100%."""
    if os.path.exists(f"{settings.MEDIA_ROOT}/{text_file_id}_progress.txt"):
        os.remove(f"{settings.MEDIA_ROOT}/{text_file_id}_progress.txt")


def progress(request, text_file_id):
    text_file = TextFile.objects.get(id=text_file_id)
    try:
        return JsonResponse({"progress": int(text_file.progress)})
    except:
        messages.error(request, f"{text_file.progress}")
        return JsonResponse({"error": text_file.progress})


@login_required
def progress_page(request, al_the_way, text_file_id):
    textfile = get_object_or_404(TextFile, id=text_file_id)

    return render(
        request,
        "vlc/progress.html",
        {"al_the_way": al_the_way, "text_file_id": text_file_id,'textfile':textfile},
    )
def update_textfile(request, textfile_id):
    # Fetch the TextFile object
    textfile = get_object_or_404(TextFile, id=textfile_id)

    if request.method == 'POST':
        # Parse incoming data from the request body
        voice_id = request.POST.get('voice_id')
        api_key = request.POST.get('api_key')

        # Validate the inputs (basic example, you can expand this)
        if not voice_id or not api_key:
            return JsonResponse({'message': 'Voice ID and API Key are required.'}, status=400)

        # Update the TextFile fields
        textfile.voice_id = voice_id
        textfile.api_key = api_key
        textfile.save()
        messages.success(request,'Update Successful!')
        return JsonResponse({'message': 'Update successful!'})

    return JsonResponse({'message': 'Invalid request method.'}, status=405)

@login_required
@check_credits_and_ownership(textfile_id_param="textfile_id", credits_required=1)
def process_textfile(request, textfile_id):
    try:
        # Fetch the TextFile instance
        textfile = TextFile.objects.get(pk=textfile_id)
        textfile.progress='0'
        textfile.save()
        if textfile.user != request.user:
            messages.error(
                request, "You do not have access to the resources you requested."
            )
            return render(request, "permission_denied.html")
    except TextFile.DoesNotExist:
        raise Http404("Text file not found")

    if not textfile_id:
        return JsonResponse({"error": "text_file_id is required."}, status=400)

    def run_process_command(textfile_id):
        try:
            # call_command("process_video", textfile_id)
            call_command("process_clips", textfile_id)
        except Exception as e:
            # Handle the exception as needed (e.g., log it)
            print(f"Error processing video: {e}")

    thread = threading.Thread(target=run_process_command, args=(textfile_id,))
    thread.start()

    return redirect(f"/text/progress_page/build/{textfile_id}")


def validate_api_key(api_key, voice_id):
    # Try making a request to Eleven Labs API to validate the key
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key}
    data = {
        "text": "Test voice synthesis",  # Small test text to avoid large requests
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        response = requests.post(url, json=data, headers=headers)

        if response.status_code == 200:
            return {"valid": True}
        elif response.status_code == 401:
            error_detail = response.json().get("detail", {})
            if "status" in error_detail and error_detail["status"] == "quota_exceeded":
                return {
                    "valid": False,
                    "error": f"Quota exceeded: {error_detail.get('message', 'Insufficient credits')}",
                }
            else:
                return {"valid": False, "error": "Invalid API key"}
        else:
            return {"valid": False, "error": f"Invalid Voice ID"}
    except requests.exceptions.RequestException as e:
        return {"valid": False, "error": "Error connecting to Eleven Labs API"}



# def validate_api_keyv(request):
#     if request.method != "POST":
#         return JsonResponse({"valid": False, "error": "Invalid request method", "status": 405}, status=405)

#     api_key = request.POST.get("eleven_labs_api_key", "").strip()
#     voice_id = request.POST.get("voice_id", "").strip()

#     if not api_key:
#         return JsonResponse({"valid": False, "error": "API key is required", "status": 400}, status=400)

#     if not voice_id:
#         return JsonResponse({"valid": False, "error": "Voice ID is required", "status": 400}, status=400)

#     url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
#     headers = {"xi-api-key": api_key}
#     data = {
#         "text": "Test voice synthesis",
#         "model_id": "eleven_monolingual_v1",
#         "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
#     }

#     try:
#         response = requests.post(url, json=data, headers=headers)
#         response.raise_for_status()  # Raise an error for HTTP 4xx or 5xx

#         if response.status_code == 200:
#             return JsonResponse({"valid": True})

#     except requests.exceptions.RequestException as e:
#         error_message = f"Error connecting to Eleven Labs API: {str(e)}"
#         status_code = 500  # Internal Server Error (default)

#         if isinstance(e, requests.exceptions.HTTPError):
#             try:
#                 error_data = response.json()
#                 detail = error_data.get("detail")

#                 if isinstance(detail, dict):  # Eleven Labs structured error
#                     status = detail.get("status")
#                     message = detail.get("message")

#                     if status == "quota_exceeded":
#                         return JsonResponse({"valid": False, "error": "Quota exceeded: " + (message or "Insufficient credits"), "status": 402}, status=402)

#                     if status == "invalid_api_key":
#                         return JsonResponse({"valid": False, "error": "Invalid API key", "status": 401}, status=401)

#                     if status == "voice_not_found":
#                         return JsonResponse({"valid": False, "error": "Invalid Voice ID", "status": 400}, status=400)

#                     return JsonResponse({"valid": False, "error": message or "API error", "status": response.status_code}, status=response.status_code)

#                 return JsonResponse({"valid": False, "error": detail or "Unknown API error", "status": response.status_code}, status=response.status_code)

#             except ValueError:
#                 return JsonResponse({"valid": False, "error": "Invalid API response", "status": response.status_code}, status=response.status_code)

#         return JsonResponse({"valid": False, "error": error_message, "status": status_code}, status=status_code)
def validate_api_keyv(request):
    if request.method != "POST":
        return JsonResponse({"valid": False, "error": "Invalid request method", "status": 405}, status=405)

    api_key = request.POST.get("eleven_labs_api_key", "").strip()
    voice_id = request.POST.get("voice_id", "").strip()

    if not api_key:
        return JsonResponse({"valid": False, "error": "API key is required", "status": 400}, status=400)

    if not voice_id:
        return JsonResponse({"valid": False, "error": "Voice ID is required", "status": 400}, status=400)

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key}
    data = {
        "text": "Test voice synthesis",
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raises error for HTTP 4xx or 5xx

        if response.status_code == 200:
            return JsonResponse({"valid": True})

    except requests.exceptions.RequestException as e:
        status_code = 500  # Default error status
        error_message = "Failed to validate API key."

        if isinstance(e, requests.exceptions.HTTPError):
            try:
                error_data = response.json()  # Parse Eleven Labs error
                detail = error_data.get("detail")

                if isinstance(detail, dict):
                    status = detail.get("status")

                    if status == "quota_exceeded":
                        error_message = "Quota exceeded: Insufficient credits"
                        status_code = 402
                    elif status == "invalid_api_key":
                        error_message = "Invalid API key"
                        status_code = 401
                    elif status == "voice_not_found":
                        error_message = "Invalid Voice ID"
                        status_code = 400
                    else:
                        error_message = "Invalid API key"

            except ValueError:
                pass  # Ignore invalid JSON response

        return JsonResponse({"valid": False, "error": error_message, "status": status_code}, status=status_code)

@login_required
@check_user_credits(minimum_credits_required=1)
def add_text(request):
    if request.method == "POST":
        voice_id = request.POST.get("voiceid")
        api_key = request.POST.get("elevenlabs_apikey")
        resolution = request.POST.get("resolution")
        font_color = request.POST.get("font_color")
        subtitle_box_color = request.POST.get("subtitle_box_color")
        font_select = request.POST.get("font_select")
        font_size = request.POST.get("font_size")
        box_radius = int(request.POST.get("box_radius"))*2
        # subtitle_opacity = float(int(request.POST.get("subtitle_opacity"))/ 100)
        
    
        print('======>',font_size)
        x, y = is_api_key_valid(api_key, voice_id)

        if x and y:
            if voice_id and api_key:
                text_obj = TextFile.objects.create(
                    user=request.user,
                    bg_level=0.06,
                    voice_id=voice_id,
                    api_key=api_key,
                    resolution=resolution,
                    font=font_select,
                    subtitle_box_color=subtitle_box_color,
                    font_size=font_size,
                    font_color=font_color,
                    # subtitle_opacity=subtitle_opacity,
                    box_radius=box_radius

                )

                return redirect(reverse("video:add_scenes", args=[text_obj.id]))

            else:
                messages.error(request, "Please provide all required fields.")
                return render(
                    request,
                    "vlc/frontend/VLSMaker/index.html",
                    {"error": "Please provide all required fields."},
                )
        elif x and not y:
            messages.error(
                request,
                "The voice ID you provided is invalid, please provide a valid one",
            )
            return render(
                request,
                "vlc/frontend/VLSMaker/index.html",
                {"error": "Please provide valid API key"},
            )
        elif not x:
            messages.error(
                request,
                "The API key you provided is invalid, please provide a valid one!",
            )
            return render(
                request,
                "vlc/frontend/VLSMaker/index.html",
                {"error": "Please provide valid API key"},
            )

    return render(request, "vlc/frontend/VLSMaker/index.html")


@login_required
@check_credits_and_ownership(textfile_id_param="textfile_id", credits_required=1)
def download_video(
    request,
    textfile_id,
):

    text_file = TextFile.objects.get(pk=textfile_id)
    if not text_file.generated_final_video.name:
        return redirect(f'/video/add-scene/{textfile_id}')
    if request.user.subscription.credits > 0:
        bg_music = request.GET.get("bg_music", None)
        if not text_file.generated_final_bgmw_video.name:
            bg_music="false"

        return render(
            request,
            "vlc/download.html",
            {
                "textfile_id": textfile_id,
                "bg_music": bg_music,
                "text_file": text_file,
                "plans": apps.get_model("accounts", "Plan").objects.all(),
            },
        )
    else:
        messages.info(request, "You do not have enough credit to Proceed")
        return redirect(reverse("home:home") + "#pricing")


@login_required
def download_file_from_s3(request, file_key, textfile_id=None):
    s3 = boto3.client(
        "s3",
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    )

    if textfile_id:
        text_file = TextFile.objects.get(id=textfile_id)
        user_sub = request.user.subscription
        if user_sub.credits > 0:
            if not text_file.processed:
                user_sub.credits -= 1
                user_sub.save()

                text_file.processed = True
                text_file.save()

            try:
                # Get the file from S3
                s3_response = s3.get_object(
                    Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key
                )
                print('===========>',file_key)

                # Set the appropriate headers for file download
                response = HttpResponse(
                    s3_response["Body"].read(), content_type=s3_response["ContentType"]
                )
                
                if file_key == "logos/VSL-Maker-Script-Template.txt":
                    custom_filename = "VideoCrafter.txt"
                    response["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
                else:
                    response["Content-Disposition"] = (
                        f'attachment; filename="{file_key.split("/")[-1]}"'
                    )
                
                response["Content-Length"] = s3_response["ContentLength"]

                return response
            except s3.exceptions.NoSuchKey:
                return HttpResponse("File not found.", status=404)
            except (NoCredentialsError, PartialCredentialsError):
                return HttpResponse("Credentials not available.", status=403)
        return HttpResponse(status=403)

    else:
        try:
            # Get the file from S3
            s3_response = s3.get_object(
                Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=file_key
            )
            print('===========>',file_key)
            # Set the appropriate headers for file download
            response = HttpResponse(
                s3_response["Body"].read(), content_type=s3_response["ContentType"]
            )
            if file_key == "logos/VSL-Maker-Script-Template.txt":
                custom_filename = "VideoCrafter.txt"
                response["Content-Disposition"] = f'attachment; filename="{custom_filename}"'
            else:
                response["Content-Disposition"] = (
                    f'attachment; filename="{file_key.split("/")[-1]}"'
                )
            response["Content-Length"] = s3_response["ContentLength"]

            return response
        except s3.exceptions.NoSuchKey:
            return HttpResponse("File not found.", status=404)
        except (NoCredentialsError, PartialCredentialsError):
            return HttpResponse("Credentials not available.", status=403)

    return HttpResponse(status=403)