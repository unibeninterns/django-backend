from django.db import models
from django.conf import settings
from module.models import Course
import uuid
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum


now = timezone.now()


class Feature(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Package(models.Model):
    PACKAGE_TYPES = (
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('addon', 'Add-on'),
    )

    name = models.CharField(max_length=100)
    package_type = models.CharField(max_length=20, choices=PACKAGE_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_weeks = models.IntegerField(default=12)
    description = models.TextField()
    features = models.ManyToManyField(Feature, blank=True, related_name='packages')

    # Package-specific settings
    includes_assessments = models.BooleanField(default=False)
    includes_certification = models.BooleanField(default=False)
    includes_transcript = models.BooleanField(default=False)
    includes_support = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ₦{self.price}"

    def get_duration_days(self):
        return self.duration_weeks * 7


class AddOn(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ₦{self.price}"


class Payment(models.Model):
    PAYMENT_OPTIONS = (
        ('card', 'Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('abandoned', 'Abandoned'),
    )

    # Package-related fields (only package, no course)
    package = models.ForeignKey(Package, on_delete=models.SET_NULL, null=True, blank=True)
    add_ons = models.ManyToManyField(AddOn, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments'
    )
    course = models.ForeignKey(
        Course,  # Reference the Course model from the module app
        on_delete=models.CASCADE,
        related_name='payments'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_option = models.CharField(max_length=50, choices=PAYMENT_OPTIONS)
    transaction_id = models.CharField(max_length=100, unique=True)
    flutterwave_ref = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')


    def __str__(self):
        return f"{self.user.username} - {self.payment_option} - ₦{self.total_amount}"

    @classmethod
    def get_monthly_revenue(cls):
        now = timezone.now()
        return (
                cls.objects.filter(
                    status="completed",
                    created_at__year=now.year,
                    created_at__month=now.month
                ).aggregate(total=Sum("total_amount"))["total"] or 0
        )

    def save(self, *args, **kwargs):
        # Calculate total amount if not set
        if not self.total_amount and self.package:
            self.total_amount = self.package.price
            # Add add-ons prices
            for add_on in self.add_ons.all():
                self.total_amount += add_on.price
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Payment"
        verbose_name_plural = "Payments"

    # def __str__(self):
    #     return f"{self.user.email} - {self.course.title} - {self.status}"


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('dropped', 'Dropped'),
        ('pending_payment', 'Pending Payment'),
    )

    # Package enrollment only (no course)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    add_ons = models.ManyToManyField(AddOn, blank=True)

    # Enrollment details
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'package')

    def __str__(self):
        return f"{self.user.username} - {self.package.name}"

    def save(self, *args, **kwargs):
        # Set expiration date when status becomes active
        if self.status == 'active' and not self.expires_at and self.package:
            self.expires_at = timezone.now() + timedelta(days=self.package.get_duration_days())
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == 'active' and (
                not self.expires_at or self.expires_at > timezone.now()
        )