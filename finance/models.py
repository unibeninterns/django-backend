from django.db import models
from django.utils import timezone

class FinancialAnalytics(models.Model):
    """Aggregated financial analytics data for dashboard"""
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)  
    total_payouts = models.DecimalField(max_digits=12, decimal_places=2)  
    total_expenses = models.DecimalField(max_digits=12, decimal_places=2)  
    profit = models.DecimalField(max_digits=12, decimal_places=2)         
    profit_percentage = models.CharField(max_length=10)                   
    revenue_this_month = models.DecimalField(max_digits=12, decimal_places=2)  
    pending_payouts = models.DecimalField(max_digits=12, decimal_places=2)     
    total_transactions = models.IntegerField()                                  
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Analytics Snapshot on {self.created_at.date()}"


class RevenueTracking(models.Model):
    """Weekly revenue and expense tracking"""
    week = models.CharField(max_length=20)  
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    expenses = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    last_aggregated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['date']
        verbose_name_plural = "Revenue Tracking"

    def __str__(self):
        return f"{self.week} - {self.date}"


class CourseRevenue(models.Model):
    """Revenue and payout per course"""
    course = models.CharField(max_length=255)  
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    payouts = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()

    class Meta:
        ordering = ['-revenue']
        verbose_name_plural = "Course Revenues"

    def __str__(self):
        return f"{self.course} - {self.revenue}"


class PaymentTransaction(models.Model):
    """Transaction-level payment tracking"""
    STATUS_CHOICES = [
        ("Succeeded", "Succeeded"),
        ("Pending", "Pending"),
        ("Failed", "Failed"),
    ]

    transaction_id = models.CharField(max_length=50, unique=True)  
    name = models.CharField(max_length=255)  
    course = models.CharField(max_length=255)  
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=50)  
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    class Meta:
        ordering = ['-date']
        verbose_name_plural = "Payment Transactions"

    def __str__(self):
        return f"{self.transaction_id} - {self.name} - {self.amount}"
