import uuid
import os
from datetime import datetime

def generate_unique_filename(filename: str) -> str:
    """
    Generate a unique filename using UUID.
    """
    ext = filename.split(".")[-1] if "." in filename else ""
    return f"{uuid.uuid4()}.{ext}"

def get_upload_path(instance, filename):
    """
    Django-like upload path generator.
    """
    return f"uploads/{datetime.now().strftime('%Y/%m/%d')}/{generate_unique_filename(filename)}"
