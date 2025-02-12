from django.core.management.base import BaseCommand
from mainapps.vidoe_text.models import TextFile
from django.utils.timezone import now
from datetime import timedelta


class Command(BaseCommand):
    help = "Deletes TextFile objects older than 2 weeks."

    def handle(self, *args, **kwargs):
        two_weeks_ago = now() - timedelta(weeks=2)

        old_files = TextFile.objects.filter(created_at__lt=two_weeks_ago)
        count = old_files.count()

        old_files.delete()

        self.stdout.write(self.style.SUCCESS(f"{count} TextFiles deleted successfully."))
