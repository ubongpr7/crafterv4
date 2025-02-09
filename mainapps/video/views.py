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

        if text_file.text_file and request.POST.get("purpose") == "process":
            if text_file.video_clips.all():
                text_file.text_file.delete(save=True)
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                    for clip in text_file.video_clips.all():
                        for subclip in clip.subclips.all():
                            temp_file.write(subclip.subtittle + "\n")
                    
                    temp_file.flush() 

                    with open(temp_file.name, "rb") as file_to_save:
                        text_file.subclips_text_file.save(
                            f"{text_file.id}_subclips.txt", file_to_save, save=True
                        )
            
                with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
                    for clip in text_file.video_clips.all():
                            temp_file.write(clip.slide + "\n")
                    
                    temp_file.flush() 

                    with open(temp_file.name, "rb") as file_to_save:
                        text_file.text_file.save(
                            f"{text_file.id}_text_file.txt", file_to_save, save=True
                        )
            

                return redirect(f"/text/process-textfile/{textfile_id}")
            return redirect(reverse("video:add_scenes", args=[textfile_id]))


        elif text_file.text_file and request.POST.get("purpose") == "update":
            for i, clip in enumerate(existing_clips):
                video_file = request.FILES.get(f"uploaded_video_{i}")
                video_clip_id = request.POST.get(f"selected_video_{i}")
                if video_clip_id:
                    video_clip = get_object_or_404(VideoClip, id=video_clip_id)
                else:
                    video_clip = None
                clip.video_file = video_clip
                if request.POST.get(f"video_{i}_status") == "filled":
                    pass
                elif (
                    request.POST.get(f"video_{i}_status") == "empty"
                    and clip.video_file_path
                ):
                    clip.video_file_path.delete()
                if video_file and request.POST.get(f"video_{i}_status") == "changed":
                    clip.video_file_path = video_file
                clip.save()
            messages.success(request, "TextFile updated successfully")
            # return redirect(reverse('video:add_scenes', args=[textfile_id]))
            return redirect(f"/text/process-textfile/{textfile_id}")

        elif request.POST.get("purpose") == "text_file":
            if request.FILES.get("text_file"):
                if request.user.subscription.plan.name.lower() == "free":
                    slides_count = 0
                    for _ in request.FILES.get("text_file"):
                        slides_count += 1

                    if slides_count > 10:
                        messages.error(
                            request,
                            "Adding More Than 10 Lines Is Only Available On Paid Plans. Please Delete Some Lines From Txt File",
                        )
                        return redirect(reverse("video:add_scenes", args=[textfile_id]))

                if text_file.video_clips:
                    for video_clip in TextLineVideoClip.objects.filter(
                        text_file=text_file
                    ):
                        video_clip.delete()
                        print("Deleted a video_clip")

                text_file.text_file = request.FILES.get("text_file")
                text_file.save()
                lines =text_file.process_text_file()
                video_clips=[] 
                for i,line in enumerate(lines, start=1):
                    video_clip=TextLineVideoClip(
                        text_file=text_file,
                        slide=line,
                        line_number=i,
                        remaining=line,

                    )
                    video_clips.append(video_clip)
                if video_clips:
                    TextLineVideoClip.objects.bulk_create(video_clips)
                return redirect(reverse("video:add_scenes", args=[textfile_id]))


            messages.error(request, "You Did Not Upload Text File")
            return redirect(reverse("video:add_scenes", args=[textfile_id]))

    else:
        video_clips= text_file.video_clips.all()
        if video_clips:
            return render(
                request,
                # "vlc/frontend/VLSMaker/sceneselection/index.html",
                "vlc//frontend/VLSMaker/test_scene/index.html",
                {"key":key,'no_of_slides':no_of_slides,"video_clips": video_clips,"textfile": text_file,'video_categories':list(video_categories)},
            )
        else:
             return render(
                request,
                # "vlc/frontend/VLSMaker/sceneselection/index.html",
                "vlc//frontend/VLSMaker/test_scene/index.html",
                { "key":key, "textfile": text_file},
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