from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DashboardOverviewAPIView,
    DashboardHighlightsAPIView,
    DashboardTasksAPIView,
    RevenueAnalyticsAPIView,
    ExpenseAnalyticsAPIView,
    CourseRevenueAPIView,
    PaymentTransactionViewSet
)
router = DefaultRouter()
router.register(r'transactions', PaymentTransactionViewSet, basename='transactions')

urlpatterns = [
    # Dashboard Endpoints
    path('dashboard/overview/', DashboardOverviewAPIView.as_view(), name='dashboard-overview'),
    path('dashboard/highlights/', DashboardHighlightsAPIView.as_view(), name='dashboard-highlights'),
    path('dashboard/tasks/', DashboardTasksAPIView.as_view(), name='dashboard-tasks'),

    # Analytics Endpoints
    path('analytics/revenue/', RevenueAnalyticsAPIView.as_view(), name='analytics-revenue'),
    path('analytics/expenses/', ExpenseAnalyticsAPIView.as_view(), name='analytics-expenses'),
    path('analytics/course-revenue/', CourseRevenueAPIView.as_view(), name='analytics-course-revenue'),

    # Transaction (ViewSet) Endpoints
    path('', include(router.urls)),
]
