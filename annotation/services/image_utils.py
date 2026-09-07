import json
import base64
from django.core.files.base import ContentFile
from io import BytesIO
from pathlib import Path
from django.core.files.storage import FileSystemStorage
import uuid
from PIL import Image
from django.core.files.base import ContentFile
import os
from django.core.files.storage import default_storage

def load_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def image_from_base64(image_data):

    if not image_data:
        raise ValueError("imageData is empty")

    if image_data.startswith("data:"):
        image_data = image_data.split(",", 1)[1]

    image_bytes = base64.b64decode(image_data)

    return Image.open(
        BytesIO(image_bytes)
    ).convert("RGB")


def extract_image_file(data, image_name):

    image = image_from_base64(
        data["imageData"]
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="JPEG",
        quality=95
    )

    return ContentFile(
        buffer.getvalue(),
        name=image_name
    )


def clamp_bbox(
    x1, y1,
    x2, y2,
    width,
    height
):

    x1, x2 = sorted([x1, x2])
    y1, y2 = sorted([y1, y2])

    x1 = max(0, min(x1, width))
    x2 = max(0, min(x2, width))

    y1 = max(0, min(y1, height))
    y2 = max(0, min(y2, height))

    return (
        x1,
        y1,
        x2,
        y2
    )



# def generate_unique_name(info, label, x1, y1, x2, y2):

#     base_name = info["filename"]

#     return (
#         f"{base_name}"
#         f"_0000_{label.upper()}_{x1}_{y1}_{x2}_{y2}.jpg"
#     )


def save_pil_to_imagefield(image, filename, base_path="frames"):
    buffer = BytesIO()
    image.save(buffer, format="JPEG")
    buffer.seek(0)

    if base_path:
        full_path = f"{base_path}/{filename}"
    else:
        full_path = filename

    if default_storage.exists(full_path):
        default_storage.delete(full_path)

    return ContentFile(buffer.getvalue(), name=filename)

