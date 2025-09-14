from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserListView, UserDetailView, AdminLoginView, UserViewSet
from .views import CustomRegisterView
from .views import OTPVerificationView
from .views import ResendOTPView


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user') 

urlpatterns = [
    path('account/users/', UserListView.as_view(), name='user-list'),
    path('account/users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path('auth/verify-otp/', OTPVerificationView.as_view(), name='verify-otp'),
    path('auth/resend-otp/', ResendOTPView.as_view(), name='resend-otp'),
    path("admin-login/", AdminLoginView.as_view(), name="admin-login"),
    path('register/', CustomRegisterView.as_view(), name='custom_register'),
]  + router.urls
