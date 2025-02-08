# backgroundmusic/models.py

import os
import uuid
from django.db import models

# from mainapps.video.models import Video
from mainapps.vidoe_text.models import TextFile


# def bg_music_file_upload_path(instance, filename):
#     """Generate a unique file path for each uploaded text file."""
#     ext = filename.split('.')[-1]
#     unique_name = f'{uuid.uuid4()}{instance.text_file.id}.{ext}'  # Use UUID to ensure unique file names
#     return os.path.join('background', filename)
def bg_music_file_upload_path(instance, filename):
    """Generate a unique file path for each uploaded text file."""
    unique_name = f"{uuid.uuid4()}"  # Use UUID to ensure unique file names

    return os.path.join("text_clip", str(instance.text_file.id), unique_name, filename)


class BackgroundMusic(models.Model):
    text_file = models.ForeignKey(
        TextFile, on_delete=models.CASCADE, related_name="background_musics"
    )
    title = models.CharField(max_length=255, null=True, blank=True)
    music = models.FileField(null=True, blank=True, upload_to=bg_music_file_upload_path)
    start_time = models.FloatField(help_text="Start time in seconds")
    end_time = models.FloatField(help_text="End time in seconds")
    bg_level = models.DecimalField(
        null=True, blank=True, max_digits=12, decimal_places=9, default=0.1
    )

    # video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name='background_music')
    def get_music_file_name(self):
        filename = self.music.name.split("/")[-1]
        return filename

    def __str__(self):
        return f"{self.text_file} {self.start_time}-{self.end_time}"
