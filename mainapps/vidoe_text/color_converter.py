import re
from colorsys import hls_to_rgb


def convert_color_input_to_normalized_rgb(color_input: str):
    color_input = color_input.strip()  # Remove any leading/trailing whitespace

    # Hexadecimal format (#RRGGBB or #RGB)
    if color_input.startswith("#"):
        return hex_to_rgb_normalized(color_input)

    # RGB or RGBA format (rgb(...), rgba(...))
    elif color_input.startswith("rgb"):
        if "a" in color_input:  # RGBA format
            return rgba_str_to_rgb_normalized(color_input)
        else:  # RGB format
            return rgb_str_to_rgb_normalized(color_input)

    # HSL format (hsl(...))
    elif color_input.startswith("hsl"):
        return hsl_str_to_rgb_normalized(color_input)

    # Invalid format
    else:
        raise ValueError("Unsupported color format")


def hex_to_rgb_normalized(hex_color: str):
    hex_color = hex_color.lstrip("#")

    # Support for shorthand hex (#RGB)
    if len(hex_color) == 3:
        hex_color = "".join([2 * c for c in hex_color])

    rgb = tuple(int(hex_color[i : i + 2], 16) / 255.0 for i in (0, 2, 4))
    return rgb


def rgb_str_to_rgb_normalized(rgb_str: str):
    rgb = re.findall(r"\d+", rgb_str)
    rgb_normalized = tuple(int(value) / 255.0 for value in rgb[:3])
    return rgb_normalized


def rgba_str_to_rgb_normalized(rgba_str: str):
    rgba = re.findall(r"\d+", rgba_str)
    rgb_normalized = tuple(int(rgba[i]) / 255.0 for i in range(3))
    return rgb_normalized


def hsl_str_to_rgb_normalized(hsl_str: str):
    hsl = re.findall(r"\d+", hsl_str)
    h, s, l = [float(hsl[0]), float(hsl[1]) / 100.0, float(hsl[2]) / 100.0]
    rgb = hls_to_rgb(h / 360.0, l, s)
    return rgb


def parse_time(time_str):
    """Convert mm:ss time string to total seconds."""
    try:
        minutes, seconds = map(int, time_str.split(":"))
        return minutes * 60 + seconds
    except ValueError:
        raise ValueError("Invalid time format. Use mm:ss.")
