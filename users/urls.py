from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import UserListView, UserDetailView, AdminLoginView, UserViewSet


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('account/users/', UserListView.as_view(), name='user-list'),
    path('account/users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path("admin-login/", AdminLoginView.as_view(), name="admin-login"),
]  + router.urls
