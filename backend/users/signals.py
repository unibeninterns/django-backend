# from .models import CustomUser
# from django.db.models.signals import post_save, pre_save
# from django.dispatch import receiver
# from django.utils.text import slugify
from allauth.account.signals import email_confirmed
from django.dispatch import receiver

@receiver(email_confirmed)
def activate_user_and_mark_verified(request, email_address, **kwargs):
    user = email_address.user
    user.is_verified = True
    user.save()


# # @receiver(post_save, sender=User)
# # def create_user_profile(sender, instance, created, **kwargs):
# #     if created:
# #         Profile.objects.create(user=instance)


