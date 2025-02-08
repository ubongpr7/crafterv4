from celery import shared_task
from datetime import timedelta
from django.utils.timezone import now
from .models import TextFile

@shared_task
def delete_old_textfiles():
    two_weeks_ago = now() - timedelta(weeks=2)
    old_files = TextFile.objects.filter(created_at__lt=two_weeks_ago)
    old_files.delete()
