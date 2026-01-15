from celery import shared_task
from .services import send_reminder
from .models import Reminder
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def send_reminder_task(self, reminder_id):
    try:
        reminder = Reminder.objects.get(id=reminder_id)
        # Call your optimized service logic
        count = send_reminder(reminder)
        return f"Successfully notified {count} users."

    except Reminder.DoesNotExist:
        logger.error(f"Reminder with ID {reminder_id} does not exist.")
        return "Reminder not found."

    except Exception as exc:
        # If the email server is down, this will retry the task 3 times
        logger.warning(f"Error sending reminder {reminder_id}: {exc}. Retrying...")
        raise self.retry(exc=exc, countdown=60)  # Retry in 60 seconds