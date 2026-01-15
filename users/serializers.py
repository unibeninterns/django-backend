from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import LoginSerializer
from rest_framework import serializers
from django.utils.text import slugify
from .models import CustomUser, TutorProfile, TutorInvitation, TutorCourseAssignment
from django.contrib.auth import authenticate
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mail
from .models import EmailOTP
from django.conf import settings
from .models import CustomUser, EmailOTP
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from core.email_utils import send_html_email
from django.contrib.auth import get_user_model
from payments.models import Enrollment
from module.models import CertificateRequest
import uuid
from module.models import Course

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

    password1 = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("Passwords don't match.")
        return data

    class Meta:
        model = CustomUser
        fields = [
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        ]

    def validate_email(self, value):
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def get_cleaned_data(self):
        try:
            parent_data = super().get_cleaned_data()
            print("Parent get_cleaned_data returns:", parent_data)  # Check your console/logs
        except Exception as e:
            print("Parent get_cleaned_data error:", e)

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
                # Add a safety limit
                if counter > 100:
                    # Fallback: use email or UUID
                    username = f'{base_username}_{uuid.uuid4().hex[:8]}'
                    break
            user.username = username

        # Add user info
        user.is_active = False

        user.save()

        # Generate and send OTP
        otp_obj, _ = EmailOTP.objects.get_or_create(user=user)
        otp_obj.generate_otp()

        # Send OTP email
        send_html_email(
            subject="Your verification code",
            template_name="email/otp_email.html",
            context={'user': user, 'otp_code': otp_obj.otp_code},
            recipient_list=[user.email],
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


class UserSettingsSerializer(serializers.ModelSerializer):
    profile_photo = serializers.ImageField(required=False, allow_null=True)
    email_alerts = serializers.BooleanField(default=True)
    platform_alerts = serializers.BooleanField(default=True)
    full_name = serializers.SerializerMethodField()
    enrolled_courses = serializers.SerializerMethodField()
    certificates = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "profile_photo",
            "first_name",
            "last_name",
            "full_name",
            "email",
            "phone_number",
            "password",
            "email_alerts",
            "platform_alerts",
            "enrolled_courses",
            "certificates",
        ]
        extra_kwargs = {
            'password': {'write_only': True, 'required': False},
            'email': {'required': True},
        }

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

    def get_enrolled_courses(self, obj):
        # Return course titles the user is enrolled in
        enrollments = Enrollment.objects.filter(user=obj)
        return [enrollment.package.title for enrollment in enrollments]

    def get_certificates(self, obj):
        certs = CertificateRequest.objects.filter(student=obj)
        return [{"course": cert.course.title, "status": cert.status} for cert in certs]

    def update(self, instance, validated_data):
        # Update basic info
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.phone_number = validated_data.get("phone_number", getattr(instance, "phone_number", None))

        # Profile photo
        if "profile_photo" in validated_data:
            instance.profile_photo = validated_data.get("profile_photo")

        # Alerts
        instance.email_alerts = validated_data.get("email_alerts", getattr(instance, "email_alerts", True))
        instance.platform_alerts = validated_data.get("platform_alerts", getattr(instance, "platform_alerts", True))

        # Password change
        password = validated_data.get("password", None)
        if password:
            instance.set_password(password)

        instance.save()
        return instance


class TutorProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    course = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = [
            'id',
            'full_name',
            'email',
            'course',
            'status',
            'is_active',
            'created_at',
        ]

    def get_full_name(self, obj):
        return f"{obj.user.first_name} {obj.user.last_name}".strip()

    def get_course(self, obj):
        assignment = getattr(obj, 'course_assignment', None)
        return assignment.course.title if assignment else None

    def get_status(self, obj):
        assignment = getattr(obj, 'course_assignment', None)
        return assignment.status if assignment else 'unassigned'

class TutorInvitationSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = TutorInvitation
        fields = [
            'id',
            'email',
            'course',
            'course_title',
            'status',
            'sent_at',
            'accepted_at',
        ]


class TutorCourseAssignmentSerializer(serializers.ModelSerializer):
    tutor_email = serializers.EmailField(source='tutor.user.email', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True)

    class Meta:
        model = TutorCourseAssignment
        fields = [
            'id',
            'tutor',
            'tutor_email',
            'course',
            'course_title',
            'status',
            'assigned_at',
            'completed_at',
        ]


class TutorInvitationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorInvitation
        fields = ['email']
