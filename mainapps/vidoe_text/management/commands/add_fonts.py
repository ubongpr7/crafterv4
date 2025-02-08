import os
import shutil
from xml.etree import ElementTree as ET
from django.conf import settings
from django.core.management.base import BaseCommand

# Paths
FONTS_DIR = os.path.join(settings.BASE_DIR, 'fonts')
CONTAINER_FONTS_DIR = "/usr/share/fonts/fonts"
TYPE_GHOSTSCRIPT_XML = "/etc/ImageMagick-6/type-ghostscript.xml"

SUPPORTED_FORMATS = ["ttf", "otf", "woff", "woff2"]


def handle_font_upload(font_path):
    """
    Handles uploading and registering a single font file.
    """
    font_name, font_extension = os.path.splitext(os.path.basename(font_path))
    font_extension = font_extension.lower().strip(".")

    if font_extension not in SUPPORTED_FORMATS:
        print(f"Skipping unsupported font format: {font_extension}")
        return

    os.makedirs(FONTS_DIR, exist_ok=True)
    local_font_path = os.path.join(FONTS_DIR, os.path.basename(font_path))

    if not os.path.exists(local_font_path):
        shutil.copy(font_path, local_font_path)
        print(f"Font saved: {local_font_path}")

    shutil.copytree(FONTS_DIR, CONTAINER_FONTS_DIR, dirs_exist_ok=True)
    print(f"Fonts copied to Docker container: {CONTAINER_FONTS_DIR}")

    add_font_to_ghostscript(font_name, font_extension, local_font_path)


def add_font_to_ghostscript(font_name, font_format, font_path):
    """
    Adds a font to ImageMagick's type-ghostscript.xml file if not already present.
    """
    # Parse the XML
    tree = ET.parse(TYPE_GHOSTSCRIPT_XML)
    root = tree.getroot()

    # Check if the font is already listed
    for element in root.findall("type"):
        if element.attrib.get("name") == font_name and element.attrib.get("glyphs") == font_path:
            print(f"Font '{font_name}' is already in type-ghostscript.xml")
            return

    # Add the new font entry
    new_font = ET.Element(
        "type",
        attrib={
            "name": font_name,
            "format": font_format,
            "glyphs": font_path,
        },
    )
    root.append(new_font)

    # Write changes back to the XML file
    tree.write(TYPE_GHOSTSCRIPT_XML)
    print(f"Font '{font_name}' added to type-ghostscript.xml")


class Command(BaseCommand):
    help = 'Update fonts in the system and register them with ImageMagick'

    def handle(self, *args, **kwargs):
        if not os.path.isdir(FONTS_DIR):
            self.stderr.write(f"Fonts directory not found: {FONTS_DIR}")
            return

        # Process each file in the fonts directory
        for font_file in os.listdir(FONTS_DIR):
            font_path = os.path.join(FONTS_DIR, font_file)
            if os.path.isfile(font_path):
                try:
                    handle_font_upload(font_path)
                except Exception as e:
                    self.stderr.write(f"Error processing font '{font_file}': {str(e)}")
                    continue

        self.stdout.write(self.style.SUCCESS("All fonts processed successfully."))
