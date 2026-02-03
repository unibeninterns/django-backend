from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
import random
from datetime import timedelta
from django.utils import timezone
import uuid
from django.conf import settings
from module.models import Course

ROLE_CHOICES = (
    ('student', 'Student'),
    ('admin', 'Admin'),
    ('tutor', 'Tutor'),
)

# Create your models here.
class CustomAccountManager(BaseUserManager):

    def create_superuser(self, email, username=None, first_name=None, last_name=None, password=None, **other_fields):
        other_fields.setdefault('is_superuser', True)
        other_fields.setdefault('is_staff', True)
        other_fields.setdefault('is_active', True)
        other_fields.setdefault('is_verified', True)
        other_fields.setdefault('role', 'admin')

        if other_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must be assigned to is_superuser=True'))

        if other_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must be assigned to is_staff=True'))

        if not username:
            username = email.split('@')[0]

        return self.create_user(
            email=email,
            first_name=first_name,
            last_name=last_name,
            password=password,
            username=username,  # ✅ explicitly keyword arg
            **other_fields
        )

    def create_user(self, email, first_name="", last_name="", password=None, username=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)

        role = extra_fields.pop('role', 'student')

        user = self.model(
            email=email,
            first_name=first_name,
            last_name=last_name,
            role=role,
            username=username or "",  # ✅ allow passing username
            **extra_fields
        )

        if not user.username:
            base_username = "new_user"
            counter = 1
            username = f"{base_username}_{counter}"
            while CustomUser.objects.filter(username=username).exists():
                counter += 1
                username = f"{base_username}_{counter}"
            user.username = username

        user.set_password(password)
        user.save(using=self._db)
        return user


class CustomUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(_('email address'), unique=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    start_date = models.DateTimeField(default=timezone.now)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)

    # To help distinguish
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    cohort = models.CharField(max_length=50, blank=True, null=True)

    # **New fields for settings**
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    email_alerts = models.BooleanField(default=True)
    platform_alerts = models.BooleanField(default=True)

    objects = CustomAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


    def __str__(self):
        return self.username

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()


class TutorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tutor_profile"
    )


    bio = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.user.email})"

class TutorCourseAssignment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
    )

    tutor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_assignment',
        # This filters the options in the Django Admin and Forms
        limit_choices_to={'role': 'tutor'}
    )

    course = models.ForeignKey(
        'module.Course',
        on_delete=models.CASCADE,
        related_name='tutor_assignment'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.tutor.email} → {self.course.title}"

class TutorInvitation(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_EXPIRED, 'Expired'),
    )

    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='sent_tutor_invites'
    )

    course = models.ForeignKey(
        'module.Course',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tutor_invitations'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    sent_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    rejected_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation to {self.email} ({self.status})"

    def is_valid(self):
        return (
                self.status == self.STATUS_PENDING
                and timezone.now() <= self.expires_at
        )

    def is_expired(self):
        return timezone.now() > self.expires_at

class TutorCourse(models.Model):
    tutor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'tutor'},
        related_name='course_assignments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='tutor_assignments'
    )

    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_PENDING = 'pending'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_PENDING, 'Pending'),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
    )

    assigned_at = models.DateTimeField(auto_now_add=True)
    unassigned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('tutor', 'course')
        verbose_name = 'Tutor Course Assignment'
        verbose_name_plural = 'Tutor Course Assignments'

    def __str__(self):
        return f"{self.tutor.email} → {self.course.title}"



class EmailOTP(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    
    def generate_otp(self):
        self.otp_code = str(random.randint(100000, 999999))
        self.created_at = timezone.now()
        self.save()

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

    def __str__(self):
        return f"OTP for {self.user.email} - {self.otp_code}"

