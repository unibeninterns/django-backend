from rest_framework.routers import DefaultRouter
from assessments.views import SessionAttendanceViewSet, NotificationViewSet, ReminderViewSet

router = DefaultRouter()
router.register(r'session-attendances', SessionAttendanceViewSet, basename='session-attendance')
router.register('notifications', NotificationViewSet, basename='notifications')
router.register('reminders', ReminderViewSet, basename='reminders')
urlpatterns = router.urls