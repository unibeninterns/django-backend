from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserSettings, ContentItem, Resource

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_settings(sender, instance, created, **kwargs):
    """
    Automatically creates a UserSettings object whenever a new
    user with the role 'student' is created.
    """
    if created and instance.role == 'student':
        UserSettings.objects.create(user=instance)

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def save_user_settings(sender, instance, **kwargs):
    """
    Ensures that if the User object is saved, the linked
    settings object is also saved.
    """
    if instance.role == 'student' and hasattr(instance, 'settings'):
        instance.settings.save()