# users/adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils.text import slugify
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()


class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def populate_user(self, request, sociallogin, data):
        # 1. Let allauth do its default population first (sets email, first, last name)
        user = super().populate_user(request, sociallogin, data)

        # 2. Generate unique username
        if not user.username:
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')

            # Fallback just in case Google doesn't provide names
            if not first_name and not last_name:
                base_username = user.email.split('@')[0]
            else:
                base_username = slugify(f'{first_name}_{last_name}')

            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}_{counter}'
                counter += 1
                if counter > 100:
                    username = f'{base_username}_{uuid.uuid4().hex[:8]}'
                    break
            user.username = username

        # 3. Auto-Verify User (Trusting Google's verification)
        user.is_active = True

        if hasattr(user, 'is_verified'):
            user.is_verified = True

        return user