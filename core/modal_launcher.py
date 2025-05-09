import os
import sys
import modal
import django
import os
from django.core.management import call_command

modal.config.token_id = os.getenv("MODAL_TOKEN_ID")
modal.config.token_secret = os.getenv("MODAL_TOKEN_SECRET")

image = modal.Image.from_dockerfile("./Dockerfile")
app = modal.App(
    name="video_crafter",
    image=image
)

@app.function(
    gpu=modal.gpu.H100(), 
    cpu=32,  
    memory=65536, 
    timeout=3600
)
def process_video(task_id: int):
    sys.path.insert(0, "/app")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

    django.setup()

    call_command("process_clips", task_id)



@app.function(
    gpu=modal.gpu.H100(), 
    cpu=32,  
    memory=65536, 
    timeout=3600
)
def process_bg_music(task_id: int):
    
    sys.path.insert(0, "/app")
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hooks_app.settings')

    django.setup()

    call_command("music_processor", task_id)


