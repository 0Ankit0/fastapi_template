import uuid
import os
from datetime import datetime

def generate_unique_filename(instance, filename):
    """
    Generate a unique filename using UUID and preserve the original file extension.
    """
    ext = os.path.splitext(filename)[1]  # Get the file extension
    return f"{uuid.uuid4()}{ext}"  # Create a unique filename

def get_upload_path(instance, filename):
    """
    Generate a unique file path for uploading files, organized by date.
    """
    date_path = datetime.now().strftime("%Y/%m/%d")  # Create a date-based path
    unique_filename = generate_unique_filename(instance, filename)  # Generate a unique filename
    return os.path.join("uploads", date_path, unique_filename)  # Combine to create the full upload path