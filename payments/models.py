from django.db import models
from django.conf import settings
from module.models import Course
import uuid
from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from django.db.models.signals import m2m_changed
from django.dispatch import receiver


now = timezone.now()

class Feature(models.Model):
    FEATURE_CHOICES = (
        ('one-on-one research clinic', 'One-on-One research Clinic'),
        ('capstone project feedback', 'Capstone Project Feedback'),
        ('premium add-on', 'Premium Add-on'),
    )

    name = models.CharField(max_length=30, choices=FEATURE_CHOICES, null=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name

class AddOn(models.Model):
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.feature.name} - ₦{self.price}"

class Package(models.Model):
    PACKAGE_TYPES = (
        ('basic', 'Basic'),
        ('premium', 'Premium'),
        ('addon', 'Add-on'),
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="packages",
        null=True,
        blank=True,
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
        return f"{self.id} -> {self.name} - ₦{self.price}"

    def get_duration_days(self):
        return self.duration_weeks * 7


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

    amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
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


class Enrollment(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('inactive', 'Inactive'),
        ('pending_payment', 'Pending Payment'),
        ('registered', 'Registered'),
        ('suspended', 'Suspended'),
        ('enrolled', 'Enrolled'),
    )

    # Package enrollment only (no course)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    package = models.ForeignKey(Package, on_delete=models.CASCADE, null=True) # TODO: change the null field to false in production
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    add_ons = models.ManyToManyField(AddOn, blank=True)

    # Enrollment details
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_payment')
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('user', 'package')

    def __str__(self):
        return f"Enrollment ID: {self.id} for {self.user.username} - {self.package.name}"

    def save(self, *args, **kwargs):
        # Set expiration date when status becomes active
        if self.status == 'active' and not self.expires_at and self.package:
            self.expires_at = timezone.now() + timedelta(days=self.package.get_duration_days() + 1)
        super().save(*args, **kwargs)

    @property
    def is_active(self):
        return self.status == 'active' and (
                not self.expires_at or self.expires_at > timezone.now()
        )

class Payout(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts'
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payouts'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50)  # bank, wallet, etc.
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    reference = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    bank_code = models.CharField(max_length=10, default='')  # e.g., '044' for Access Bank
    account_number = models.CharField(max_length=20, default='')  # e.g., '0690000000'
    currency = models.CharField(max_length=3, default='NGN')

    # Store the Flutterwave specific ID for tracking
    flutterwave_id = models.CharField(max_length=100, blank=True, null=True)

    notes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Payout"
        verbose_name_plural = "Payouts"

    def __str__(self):
        return f"Payout ₦{self.amount} → {self.recipient}"

@receiver(m2m_changed, sender=Payment.add_ons.through)
def update_payment_total(sender, instance, action, **kwargs):
    # This triggers AFTER the many-to-many relationship is saved
    if action in ['post_add', 'post_remove', 'post_clear']:
        total = instance.package.price if instance.package else 0
        # Now we can safely see the add-ons!
        for add_on in instance.add_ons.all():
            total += add_on.price

        # We use .update() to avoid re-triggering the save() method
        Payment.objects.filter(pk=instance.pk).update(total_amount=total, amount=total)