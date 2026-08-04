import os
import subprocess
import gzip
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from datetime import timedelta

logger = logging.getLogger(__name__)

def upload_to_cloud_storage(filepath):
    """
    Extensible interface for uploading backups to external cloud storage.
    Currently stubbed - can be extended to support AWS S3, Google Cloud Storage, or Azure Blob.
    """
    logger.info(f"[Backup Storage] Ready to upload {filepath} to cloud storage (GCS/S3 placeholder).")
    # TODO: Add S3/GCS upload client logic here
    pass

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def send_invoice_email_task(self, invoice_id):
    """
    Retrieve invoice, generate invoice receipt details, and send an email to the customer.
    Autoretry on network/SMTP failure.
    """
    from billing.models import Invoice
    try:
        invoice = Invoice.objects.select_related("customer", "shop").get(id=invoice_id)
    except Invoice.DoesNotExist:
        logger.error(f"Invoice {invoice_id} not found. Cannot send email.")
        return

    customer_email = invoice.customer.email if invoice.customer else None
    if not customer_email:
        logger.warning(f"No email address found for customer of Invoice {invoice_id}. Skipping email.")
        return

    subject = f"Invoice #{invoice.invoice_number} from {invoice.shop.name}"
    message = (
        f"Dear {invoice.customer.name},\n\n"
        f"Thank you for shopping with us! Here is a summary of your invoice:\n"
        f"Invoice Number: {invoice.invoice_number}\n"
        f"Total Amount: {invoice.total_amount} {getattr(settings, 'CURRENCY_CODE', 'INR')}\n"
        f"Date: {invoice.created_at.strftime('%Y-%m-%d')}\n\n"
        f"Please log in to your account or contact our branch for physical copies.\n\n"
        f"Best regards,\n"
        f"{invoice.shop.name}"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@aureate.com"),
        recipient_list=[customer_email],
        fail_silently=False,
    )
    logger.info(f"Successfully sent invoice email for Invoice #{invoice.invoice_number} to {customer_email}")

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def check_subscriptions_task(self):
    """
    Scans for shops whose subscription expires within the next 3 days,
    and sends a reminder notification email.
    """
    from core.models import Shop
    now = timezone.now()
    cutoff = now + timedelta(days=3)

    shops = Shop.objects.filter(is_active=True).select_related("active_subscription")

    email_count = 0
    for shop in shops:
        sub = shop.active_subscription
        if not sub:
            continue

        expires_at = sub.expires_at
        # Check if expiring soon and not already notified (or just alert expiring in the target window)
        if now < expires_at <= cutoff:
            days_left = (expires_at - now).days
            subject = f"Action Required: Subscription Expiry Warning - {shop.name}"
            message = (
                f"Dear {shop.owner_name},\n\n"
                f"Your subscription plan ({sub.plan.name if hasattr(sub, 'plan') and sub.plan else 'Active Plan'}) "
                f"expires on {expires_at.strftime('%Y-%m-%d %H:%M:%S')} (in {days_left} days).\n"
                f"Please renew your subscription to prevent system lockout and continue operations.\n\n"
                f"Thank you for choosing Aureate,\n"
                f"SaaS Administration Team"
            )
            try:
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@aureate.com"),
                    recipient_list=[shop.email],
                    fail_silently=False,
                )
                email_count += 1
            except Exception as e:
                logger.error(f"Failed to send expiry warning to {shop.email}: {e}")

    logger.info(f"Subscription checker finished. Sent {email_count} expiry warning emails.")

@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 5},
)
def backup_database_task(self):
    """
    Runs pg_dump to backup the PostgreSQL database, compresses it using gzip,
    saves the file locally, and triggers the cloud upload wrapper.
    """
    db_conn = settings.DATABASES["default"]
    engine = db_conn["ENGINE"]

    if "postgresql" not in engine:
        logger.warning("Database engine is not PostgreSQL. Skipping backup task.")
        return

    db_name = db_conn["NAME"]
    db_user = db_conn["USER"]
    db_password = db_conn["PASSWORD"]
    db_host = db_conn["HOST"]
    db_port = db_conn["PORT"]

    backup_dir = "/app/backups"
    # Fallback to local workspace backups directory if executing outside Docker
    if not os.path.exists(backup_dir):
        backup_dir = os.path.join(settings.BASE_DIR, "backups")

    os.makedirs(backup_dir, exist_ok=True)

    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    sql_filepath = os.path.join(backup_dir, f"backup_{db_name}_{timestamp}.sql")
    gzip_filepath = f"{sql_filepath}.gz"

    env = os.environ.copy()
    env["PGPASSWORD"] = db_password

    cmd = [
        "pg_dump",
        "-h", db_host,
        "-p", str(db_port),
        "-U", db_user,
        "-d", db_name,
        "-f", sql_filepath
    ]

    try:
        # Run pg_dump command
        result = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info(f"Database dump completed: {result.stdout}")

        # Compress the SQL dump file
        with open(sql_filepath, "rb") as f_in:
            with gzip.open(gzip_filepath, "wb") as f_out:
                f_out.writelines(f_in)

        # Remove the uncompressed file
        os.remove(sql_filepath)
        logger.info(f"Backup compressed successfully: {gzip_filepath}")

        # Extensible cloud upload hook
        upload_to_cloud_storage(gzip_filepath)

    except Exception as e:
        logger.error(f"Database backup task failed: {e}")
        # Clean up files on error
        if os.path.exists(sql_filepath):
            os.remove(sql_filepath)
        raise

@shared_task
def send_sms_notification_task(to_number, message):
    """
    Placeholder task for sending SMS notifications.
    Can be wired to Twilio or other SMS APIs later.
    """
    logger.info(f"[SMS Notification Stub] Sending to {to_number}: {message}")

@shared_task
def send_whatsapp_notification_task(to_number, message):
    """
    Placeholder task for sending WhatsApp notifications.
    Can be wired to actual WhatsApp Business API later.
    """
    logger.info(f"[WhatsApp Notification Stub] Sending to {to_number}: {message}")

@shared_task
def handle_failed_task(task_name, task_id, args, kwargs, exception_msg):
    """
    DLQ Task: Receives metadata about permanently failed tasks for audit and replay.
    """
    logger.error(
        f"[DLQ Audit] Task '{task_name}' [{task_id}] permanently failed!\n"
        f"Args: {args}\nKwargs: {kwargs}\nException: {exception_msg}"
    )

