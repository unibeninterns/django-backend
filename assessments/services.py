from django.core.mail import send_mail
from django.template.defaultfilters import title

from users.models import CustomUser as User
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from assessments.models import Notification
from payments.models import Enrollment

def send_reminder(reminder):
    users = User.objects.none()

    # 1. Identify the Audience
    if reminder.audience == 'students':
        users = User.objects.filter(role='student')

    elif reminder.audience == 'tutors':
        users = User.objects.filter(role='tutor')

    elif reminder.audience == 'course' and reminder.course:
        user_ids = Enrollment.objects.filter(
            status='active',
            package__course=reminder.course
        ).values_list('user_id', flat=True)
        users = User.objects.filter(id__in=user_ids)

    user_count = users.count()

    # 2. Deliver the Reminder
    if reminder.reminder_type == 'email':
        for user in users:
            if user.email:
                send_mail(
                    subject='New Course Reminder',
                    message=reminder.message,
                    from_email=None,
                    recipient_list=[user.email],
                    fail_silently=True
                )

    elif reminder.reminder_type == 'in_app':
        # Step A: Bulk create in DB for history (Fast)
        notifications = [
            Notification(user=user, message=reminder.message)
            for user in users
        ]
        Notification.objects.bulk_create(notifications)

        # Step B: Trigger Real-Time WebSocket pings (Instant UI update)
        # We use a loop for the pings. Note: In massive apps,
        # this part is usually sent to a background task.
        for user in users:
            # We call your existing notify_user logic or directly send to group
            # Since we already did the DB create above, we can just use
            # the WebSocket part of notify_user logic here.
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"user_{user.id}",
                {
                    "type": "send_notification",
                    "data": {
                        "message": reminder.message,
                        "type": "REMINDER"
                    }
                }
            )

    return user_count

def notify_user(user, message, payload=None):
    notification = Notification.objects.create(
        user=user,
        message=message,
        title=title
    )

    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user.id}",
        {
            "type": "send_notification",
            "data": {
                "id": notification.id,
                "message": message,
                "created_at": notification.created_at.isoformat(),
                "payload": payload or {}
            }
        }
    )

    return notification

def send_notification(user_id, payload):
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "notify",
            "data": payload
        }
    )