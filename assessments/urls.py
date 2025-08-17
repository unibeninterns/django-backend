from rest_framework.routers import DefaultRouter
from assessments.views import SessionAttendanceViewSet

router = DefaultRouter()
router.register(r'session-attendances', SessionAttendanceViewSet, basename='session-attendance')
urlpatterns = router.urls