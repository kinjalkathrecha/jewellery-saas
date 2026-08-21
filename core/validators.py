import os
from django.core.exceptions import ValidationError

def validate_image_upload(file):
    """
    Validates that the uploaded file is a valid image type (JPEG, PNG, WebP)
    and does not exceed the maximum allowed file size of 5MB.
    """
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    if file.size > MAX_SIZE:
        raise ValidationError("File too large (max 5MB)")
    
    allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
    content_type = getattr(file, 'content_type', None)
    if content_type and content_type not in allowed_types:
        raise ValidationError("Only JPEG, PNG, WebP allowed")
    
    ext = os.path.splitext(file.name)[1].lower()
    allowed_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    if ext not in allowed_extensions:
        raise ValidationError("Only JPEG, PNG, and WebP images are allowed.")
