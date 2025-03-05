import json
from django.shortcuts import render, redirect, get_object_or_404
from mainapps.vidoe_text.models import TextFile, TextLineVideoClip, LogoModel
from django.http import HttpResponse
from .models import VideoClip, ClipCategory
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import JsonResponse
import tempfile
from django.db.models import F, Func, Value, CharField
from django.views.decorators.csrf import csrf_exempt
from django.http import FileResponse
from .speed_up_video_ import process_video_speed  

from django.http import FileResponse, JsonResponse
import os



@login_required
def speed_up_video(request):
    if request.method == "POST":
        speed = float(request.POST.get("speed", 1.0))
        video_file = request.FILES.get("file")

        if video_file:
            processed_video_path = process_video_speed(video_file, speed)

            if processed_video_path:
                try:
                    response = FileResponse(
                        open(processed_video_path, 'rb'), content_type='video/mp4'
                    )
                    response['Content-Disposition'] = 'attachment; filename="sped_up_video.mp4"'
                    response['Content-Length'] = os.path.getsize(processed_video_path)  # Ensure correct file size

                    # Cleanup AFTER response is sent
                    response['X-Delete-File'] = processed_video_path  # Custom header for cleanup
                    return response

                except Exception as e:
                    return JsonResponse({'error': str(e)}, status=500)

    return render(request, 'speed_up_video.html', )

# def speed_up_video(request):
#     processing = False
#     processed_video_url = None

#     if request.method == "POST":
#         speed = float(request.POST.get("speed", 1.0)) 
#         video_file = request.FILES.get("file")

#         if video_file:
#             processing = True
#             processed_video_path = process_video_speed(video_file, speed)

#             if processed_video_path:
#                 try:
#                     with open(processed_video_path, 'rb') as f:
#                         response = FileResponse(f, content_type='video/mp4')
#                         response['Content-Disposition'] = 'attachment; filename="sped_up_video.mp4"'
#                         cleanup_processed_video(processed_video_path) #cleanup after sending.
#                         processing = False
#                         return response
#                 except FileNotFoundError:
#                     processing = False
#                     return render(request, 'speed_up_video.html', {'processing': processing, 'error': 'Processed video file not found.'})
#                 except Exception as e:
#                     processing = False
#                     return render(request, 'speed_up_video.html', {'processing': processing, 'error': f'An error occurred: {e}'})

#             else:
#                 processing = False
#                 return render(request, 'speed_up_video.html', {'processing': processing, 'error': 'Video processing failed.'})

#     return render(request, 'speed_up_video.html', {'processing': processing})

def rename_video_clip(request, video_id):
    video_clip = get_object_or_404(VideoClip, id=video_id)
    if request.method == "POST":
        new_title = request.POST.get("newName")
        video_clip.title = new_title
        video_clip.save()
        return HttpResponse(status=204)
    return render(request, "rename.html", {"item": video_clip})


def rename_folder(request, category_id):
    folder = get_object_or_404(ClipCategory, id=category_id)
    if request.method == "POST":
        new_name = request.POST.get("newName")
        folder.name = new_name
        folder.save()
        return HttpResponse(status=200)
    return render(request, "rename.html", {"item": folder})


@login_required
def add_video_clip(request, category_id):
    category = get_object_or_404(ClipCategory, id=category_id)

    if request.method == "POST":
        video_file = request.FILES.get("video_file")
        if video_file:
            clip = VideoClip.objects.create(
                video_file=video_file, title=video_file.name, category=category
            )
            clip.save()
            return HttpResponse(status=200)

    return render(request, "partials/add_video.html", {"category": category})


@login_required
def delete_clip(request, clip_id):
    clip = get_object_or_404(VideoClip, id=clip_id)
    if request.method == "POST":
        if clip.video_file:
            clip.video_file.delete(save=False)

        clip.delete()

        return HttpResponse(status=204)

    return render(request, "partials/confirm_delete.html", {"item": clip})


@login_required
def delete_category(request, category_id):
    category = get_object_or_404(ClipCategory, id=category_id)
    if request.method == "POST":

        def delete_category_and_subcategories(cat):
            cat.video_clips.all().delete()
            cat.delete()

        delete_category_and_subcategories(category)

        return HttpResponse(status=204)

    return render(request, "partials/confirm_delete.html", {"item": category})


@login_required
def category_view(request, category_id=None, video_id=None):
    videos = []
    subcategories = []
    main_categories = []
    current_category = None
    video = None
    if category_id:
        current_category = get_object_or_404(
            ClipCategory, id=category_id, user=request.user
        )
        subcategories = current_category.subcategories.all()
        videos = current_category.video_clips.all()

        if video_id:
            video = VideoClip.objects.get(category=current_category, id=video_id)
    else:
        main_categories = ClipCategory.objects.filter(user=request.user)

    context = {
        "current_category": current_category,
        "folders": main_categories,
        "subcategories": subcategories,
        "videos": videos,
        "category_id": category_id,
        "video_id": video_id,
        "video": video,
    }
    return render(request, "assets/assets.html", context)


@login_required
def upload_video_folder(request):
    if request.method == "POST":
        categories_ = []
        if "directories" not in request.POST:
            return render(
                request, "upload.html", {"error": "No directory data provided."}
            )

        uploaded_folder = request.FILES.getlist("folder")
        directories = json.loads(request.POST["directories"])

        for folder_path, files in directories.items():
            folder_parts = folder_path.split("/")
            parent = None

            for folder_name in folder_parts:
                if not ClipCategory.objects.filter(name=folder_name, user=request.user):
                    category = ClipCategory.objects.create(
                        name=folder_name, parent=parent, user=request.user
                    )
                    categories_.append(category)
                    parent = category
                else:
                    category = ClipCategory.objects.filter(
                        name=folder_name, user=request.user
                    ).first()
                    parent = category

            for file_name in files:
                file = next((f for f in uploaded_folder if f.name == file_name), None)
                if file:
                    if file.size != 0:
                        video_extensions = ["mp4", "webm", "mkv", "avi", "mov"]
                        if file.name.split(".")[-1].lower() in video_extensions:
                            VideoClip.objects.create(
                                title=file_name, video_file=file, category=parent
                            )
                        else:
                            messages.warning(
                                request,
                                f"File '{file_name}' Is Not A Valid Video Format.",
                            )
                    else:
                        messages.warning(
                            request,
                            f"File '{file_name}' Is Empty And Has Been Skipped.",
                        )

                        continue
                else:
                    continue
        for cat in categories_:
            if len(cat.video_clips.all()) == 0:
                messages.info(
                    request,
                    f"The Folder {cat.name} Was Deleted Since It Has No Fideo Files In It",
                )
                cat.delete()
        messages.success(request, "Files Uploaded Successfully!")
        return HttpResponse("Upload Successful!")

    return render(request, "dir_upload.html")


@login_required
def add_video_clips(request, textfile_id):
    text_file = get_object_or_404(TextFile, id=textfile_id)
    text_file.progress = "0"
    text_file.save()
    key = LogoModel.objects.get(id=2).logo.name
    existing_clips = TextLineVideoClip.objects.filter(text_file=text_file)

    no_of_slides= len(existing_clips)
    if text_file.user != request.user:
        messages.error(
            request, "You Do Not Have Access To The Resources You Requested "
        )
        return render(request, "permission_denied.html")
    video_categories = ClipCategory.objects.filter(user=request.user).values("id", "name", "parent_id")
    if request.method == "POST":

        if  request.POST.get("purpose") == "process":
            if text_file.text_file:
                text_file.text_file.delete(save=False)
            if text_file.video_clips.all():
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                    for clip in text_file.video_clips.all():
                        for subclip in clip.subclips.all():
                            if subclip.subtittle:
                                temp_file.write(subclip.subtittle.strip() + "\n")
                    
                    temp_file.flush() 

                    with open(temp_file.name, "rb") as file_to_save:
                        text_file.subclips_text_file.save(
                            f"{text_file.id}_subclips.txt", file_to_save, save=True
                        )
            
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                    for clip in text_file.video_clips.all():
                            if clip.slide:
                               
                                temp_file.write(clip.slide.strip() + "\n")
                    
                    temp_file.flush() 

                    with open(temp_file.name, "rb") as file_to_save:
                        text_file.text_file.save(
                            f"{text_file.id}_text_file.txt", file_to_save, save=True
                        )
            

                return redirect(f"/text/process-textfile/{textfile_id}")
            return redirect(reverse("video:add_scenes", args=[textfile_id]))

    else:
        video_clips= text_file.video_clips.all()
        return render(
                request,
                "vlc//frontend/VLSMaker/test_scene/index.html",
                {
                    "key":key,
                    'no_of_slides':no_of_slides,
                    "video_clips": video_clips,
                    "textfile": text_file,
                    'video_categories':list(video_categories)
                },
            )
        

@login_required
def fetch_video_categories(request):
    categories = ClipCategory.objects.filter(user=request.user).values("id", "name", "parent_id")
    return JsonResponse(list(categories), safe=False)

def get_clip(request, cat_id):
    category = get_object_or_404(ClipCategory, id=cat_id)
    videos = VideoClip.objects.filter(category=category)

    # Use the `id_as_string` method
    response_data = [{"id": video.id_as_string(), "title": video.title} for video in videos]
    return JsonResponse(response_data, safe=False)