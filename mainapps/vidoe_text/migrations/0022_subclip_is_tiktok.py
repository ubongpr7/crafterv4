# Generated by Django 4.2.16 on 2025-02-22 17:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vidoe_text', '0021_textlinevideoclip_subtitled_clip'),
    ]

    operations = [
        migrations.AddField(
            model_name='subclip',
            name='is_tiktok',
            field=models.BooleanField(default=False),
        ),
    ]
