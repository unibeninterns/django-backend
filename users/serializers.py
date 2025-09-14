from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from django.utils.text import slugify
from .models import CustomUser
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from .models import EmailOTP
from django.conf import settings
from .models import CustomUser, EmailOTP
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'first_name', 'last_name', 'email', 'is_verified', 'username', 'role', 'cohort']
        read_only_fields = ['username', 'is_verified', 'role', 'cohort']


class CustomRegisterSerializer(RegisterSerializer):
    _has_phone_field = False
    username = None

    first_name = serializers.CharField(required=True)
    last_name = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "password",
        ]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def get_cleaned_data(self):
        return {
            'first_name': self.validated_data.get('first_name', ''),
            'last_name': self.validated_data.get('last_name', ''),
            'email': self.validated_data.get('email', ''),
            'password1': self.validated_data.get('password1', ''),
            'password2': self.validated_data.get('password2', ''),
        }

    def save(self, request):
        user = super().save(request)

        # Generate unique username if missing
        if not user.username:
            base_username = slugify(f'{user.first_name}_{user.last_name}')
            username = base_username
            counter = 1
            while CustomUser.objects.filter(username=username).exists():
                username = f'{base_username}_{counter}'
                counter += 1
            user.username = username

        # Add user info
        user.first_name = self.validated_data['first_name']
        user.last_name = self.validated_data['last_name']
        user.is_active = False

        user.save()

        # Generate and send OTP
        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp_obj.generate_otp()

        send_mail(
            subject="Your verification code",
            message=f"Your OTP code is: {otp_obj.otp_code}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        return user


class CustomLoginSerializer(LoginSerializer):
    username = None
    email = serializers.EmailField(required=True)
    password = serializers.CharField(style={'input_type': 'password'})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove username field completely
        if 'username' in self.fields:
            del self.fields['username']

    def authenticate(self, **kwargs):
        return authenticate(self.context['request'], **kwargs)

    def _validate_email(self, email, password):
        if email and password:
            user = self.authenticate(email=email, password=password)
            if not user:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        return user

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = self._validate_email(email, password)

            # Did we get back an active user?
            if user:
                if not user.is_active:
                    msg = _('User account is disabled.')
                    raise serializers.ValidationError(msg, code='authorization')
            else:
                msg = _('Unable to log in with provided credentials.')
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = _('Must include "email" and "password".')
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs


class OTPVerificationSerializer(serializers.Serializer):
    email = serializers.EmailField()
    otp_code = serializers.CharField(max_length=6)

    def validate(self, attrs):
        email = attrs.get('email')
        otp_code = attrs.get('otp_code')

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

        try:
            otp_obj = EmailOTP.objects.get(user=user)
        except EmailOTP.DoesNotExist:
            raise serializers.ValidationError("OTP not found for this user.")

        if otp_obj.otp_code != otp_code:
            raise serializers.ValidationError("Invalid OTP code.")
        
        if otp_obj.is_expired():
            raise serializers.ValidationError("OTP has expired. Please request a new one.")

        attrs['user'] = user
        attrs['otp_obj'] = otp_obj
        return attrs

    def save(self):
        user = self.validated_data['user']
        otp_obj = self.validated_data['otp_obj']

        # Activate user
        user.is_active = True
        user.is_verified = True  # If your model has this field
        user.save()

        # Remove used OTP
        otp_obj.delete()

        # 🔑 Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
    


