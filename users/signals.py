from allauth.account.signals import email_confirmed
from django.dispatch import receiver

@receiver(email_confirmed)
def activate_user_and_mark_verified(request, email_address, **kwargs):
    user = email_address.user
    user.is_verified = True
    user.save()
