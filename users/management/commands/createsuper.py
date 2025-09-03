import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates a superuser with environment-based credentials.'

    def handle(self, *args, **kwargs):
        email = os.getenv("DJANGO_SUPERUSER_EMAIL")
        password = os.getenv("DJANGO_SUPERUSER_PASSWORD")
        first_name = os.getenv("DJANGO_SUPERUSER_FIRSTNAME", "Admin")
        last_name = os.getenv("DJANGO_SUPERUSER_LASTNAME", "User")

        if not email or not password:
            self.stdout.write(self.style.ERROR("Email or password not set in environment."))
            return

        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            self.stdout.write(self.style.SUCCESS("Superuser created successfully."))
        else:
            self.stdout.write(self.style.WARNING("Superuser already exists."))
