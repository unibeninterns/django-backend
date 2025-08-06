from django.urls import path
from .views import UserListView, UserDetailView

urlpatterns = [
    path('account/users/', UserListView.as_view(), name='user-list'),
    path('account/users/<int:pk>/', UserDetailView.as_view(), name='user-detail'),
]
