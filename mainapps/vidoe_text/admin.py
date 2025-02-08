from django.contrib import admin

# Register your models here.
from .models import TextFile, TextLineVideoClip, LogoModel,SubClip

admin.site.register(TextLineVideoClip)
admin.site.register(TextFile)
admin.site.register(LogoModel)
admin.site.register(SubClip)
