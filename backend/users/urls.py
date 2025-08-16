from django.urls import path
from .views import UserListView, UserDetailView, AdminLoginView

urlpatterns = [
    path('account/users/', UserListView.as_view(), name='user-list'),
    path('account/users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
    path("admin-login/", AdminLoginView.as_view(), name="admin-login"),
]
