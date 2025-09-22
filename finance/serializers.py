from rest_framework import serializers
from .models import (
    FinancialAnalytics,
    RevenueTracking,
    CourseRevenue,
    PaymentTransaction
)

class FinancialAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAnalytics
        fields = '__all__'


class RevenueTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueTracking
        fields = '__all__'


class CourseRevenueSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseRevenue
        fields = '__all__'


class PaymentTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentTransaction
        fields = '__all__'
