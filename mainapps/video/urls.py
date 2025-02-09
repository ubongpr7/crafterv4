from django.urls import path
from . import views

app_name = "video"
urlpatterns = [
    path("add-scene/<str:textfile_id>/", views.add_video_clips, name="add_scenes"),
    path("get_clip/<str:cat_id>/", views.get_clip, name="get_clip"),
    path("upload-folder/", views.upload_video_folder, name="upload_video_folder"),
    path("assets/<str:category_id>/", views.category_view, name="subcategory_view"),
    path("assets/", views.category_view, name="category_view"),
    path(
        "assets/<str:category_id>/<str:video_id>/",
        views.category_view,
        name="category_view_video",
    ),
    path('api/video-categories/', views.fetch_video_categories, name='fetch_video_categories'),
    path(
        "categories/delete/<int:category_id>/",
        views.delete_category,
        name="delete_category",
    ),

    path("clips/delete/<int:clip_id>/", views.delete_clip, name="delete_video"),
    path(
        "add-video-clip/<int:category_id>/", views.add_video_clip, name="add_video_clip"
    ),
    path(
        "rename-video-clip/<int:video_id>/",
        views.rename_video_clip,
        name="rename_video_clip",
    ),
    path("rename-folder/<int:category_id>/", views.rename_folder, name="rename_folder"),
]
