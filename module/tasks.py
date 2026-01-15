# assessments/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from assessments.services import notify_user
# Use the correct import path for your Announcement model
from module.models import Announcement

User = get_user_model()


@shared_task
def broadcast_announcement_task(announcement_id):
    try:
        announcement = Announcement.objects.get(id=announcement_id)

        if announcement.audience == 'all':
            users = User.objects.all()
        elif announcement.audience == 'students':
            users = User.objects.filter(role='student')
        else:
            users = User.objects.filter(role='tutor')

        for user in users:
            notify_user(
                user,
                f"{announcement.title}: {announcement.message}",
                payload={"type": "announcement", "id": announcement.id}
            )
        return f"Broadcasted announcement {announcement_id} to {users.count()} users."
    except Announcement.DoesNotExist:
        return "Announcement not found."