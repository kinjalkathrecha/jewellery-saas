import io
import uuid
from datetime import date

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from PIL import Image

from .models import RepairStatusHistory


def generate_job_card_number(repair):
    """
    Generates a unique job card number scoped to the shop:
    Format: SHOP<id>-JOB-YYYYMMDD-<6-char unique hash>
    """
    today_str = date.today().strftime('%Y%m%d')
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"SHOP{repair.shop.id}-JOB-{today_str}-{unique_suffix}"

def compress_repair_photo(item_photo):
    """
    Compresses the uploaded photo to max 800px width/height and 80% JPEG quality
    to optimize SaaS storage.
    """
    if not item_photo:
        return
        
    img = Image.open(item_photo)
    
    # Resize if necessary
    max_size = 800
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size))
        
    # Convert RGBA/P to RGB for clean JPEG conversion
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
        
    buffer = io.BytesIO()
    img.save(buffer, format='JPEG', quality=80)
    
    # Save back to file field
    filename = item_photo.name
    dot_idx = filename.rfind('.')
    if dot_idx != -1:
        filename = filename[:dot_idx] + '.jpg'
    else:
        filename = filename + '.jpg'
        
    item_photo.save(filename, ContentFile(buffer.getvalue()), save=False)

def validate_status_transition(from_status, to_status):
    """
    Validates status transition path.
    Allowed:
      - RECEIVED -> UNDER_REPAIR, CANCELLED
      - UNDER_REPAIR -> READY, CANCELLED
      - READY -> DELIVERED, CANCELLED
      - DELIVERED, CANCELLED are terminal states
    """
    if from_status == to_status:
        return
        
    allowed_transitions = {
        'RECEIVED': ['UNDER_REPAIR', 'CANCELLED'],
        'UNDER_REPAIR': ['READY', 'CANCELLED'],
        'READY': ['DELIVERED', 'CANCELLED'],
        'DELIVERED': [],
        'CANCELLED': [],
    }
    
    if to_status not in allowed_transitions.get(from_status, []):
        raise ValidationError(
            f"Invalid transition from '{from_status}' to '{to_status}'."
        )

def process_repair_status_change(repair, to_status, user, notes=""):
    """
    Updates repair status, sets delivered_at timestamp on transition to DELIVERED,
    validates the transition, and writes to RepairStatusHistory.
    """
    from_status = repair.status
    if from_status == to_status:
        return
        
    validate_status_transition(from_status, to_status)
    
    with transaction.atomic():
        repair.status = to_status
        if to_status == 'DELIVERED':
            repair.delivered_at = timezone.now()
        else:
            repair.delivered_at = None
            
        repair.save()
        
        # Create history log entry
        RepairStatusHistory.objects.create(
            repair=repair,
            from_status=from_status,
            to_status=to_status,
            changed_by=user,
            notes=notes or f"Status changed from {repair.get_status_display()}."
        )
