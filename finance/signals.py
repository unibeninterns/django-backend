from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PaymentTransaction

@receiver(post_save, sender=PaymentTransaction)
def update_financial_metrics(sender, instance, created, **kwargs):
    if created:
        # Real-time update logic here
        print(f"Updating financial metrics for transaction {instance.transaction_id}")
