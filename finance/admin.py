from django.contrib import admin
from .models import FinancialAnalytics, RevenueTracking, CourseRevenue, PaymentTransaction

admin.site.register(FinancialAnalytics)
admin.site.register(RevenueTracking)
admin.site.register(CourseRevenue)
admin.site.register(PaymentTransaction)
