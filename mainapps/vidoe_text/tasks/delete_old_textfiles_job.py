# python manage.py crontab add
from mainapps.vidoe_text.models import TextFile
from django.utils.timezone import now
from datetime import timedelta

# python manage.py crontab show
# python manage.py crontab remove

def delete_od_files():
    two_weeks_ago = now() - timedelta(weeks=2)

    old_files = TextFile.objects.filter(created_at__lt=two_weeks_ago)
    count = old_files.count()

    old_files.delete()