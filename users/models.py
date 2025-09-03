from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _ 
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

ROLE_CHOICES = (
    ('student', 'Student'),
    ('admin', 'Admin'),
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

    objects = CustomAccountManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"


    def __str__(self):
        return self.username

    