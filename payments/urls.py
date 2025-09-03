from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, EnrollmentViewSet, PackageViewSet, AddOnViewSet
from .webhooks import flutterwave_webhook


router = DefaultRouter()
# router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
router.register(r'packages', PackageViewSet, basename='package')
router.register(r'addons', AddOnViewSet, basename='addon')

urlpatterns = [
    path('', include(router.urls)),
    path('webhooks/flutterwave/', flutterwave_webhook, name='flutterwave-webhook'),
]

# router = DefaultRouter()
# router.register(r'payments', PaymentViewSet, basename='payment')
#
# router = DefaultRouter()
# router.register(r'payments', PaymentViewSet, basename='payment')
# router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')
# router.register(r'packages', PackageViewSet, basename='package')
# router.register(r'addons', AddOnViewSet, basename='addon')
#
# urlpatterns = [
#     # API endpoints
#     path('', include(router.urls)),
#     path('my-payments/', PaymentViewSet.as_view({'get': 'user_payments'}), name='user-payments'),
#     path('my-enrollments/', EnrollmentViewSet.as_view({'get': 'user_enrollments'}), name='user-enrollments'),
#     path('initiate-package/', PaymentViewSet.as_view({'post': 'initiate_package'}), name='package-payment-initiate'),
#     path('<int:pk>/verify/', PaymentViewSet.as_view({'get': 'verify'}), name='payment-verify'),
#     path('enrollments/<int:pk>/cancel/', EnrollmentViewSet.as_view({'post': 'cancel'}), name='enrollment-cancel'),
#     path('webhooks/flutterwave/', flutterwave_webhook, name='flutterwave-webhook'),
# ]