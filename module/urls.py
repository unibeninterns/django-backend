from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'courses', CourseViewSet, basename='course')
router.register(r'modules', ModuleViewSet, basename='module')
router.register(r'lessons', LessonViewSet, basename='lesson')
router.register(r'content-item', ContentItemViewSet, basename='contentitem')
router.register(r'quizzes', QuizViewSet, basename='quiz')
router.register(r'questions', QuestionViewSet, basename='question')
router.register(r'quiz-submissions', QuizSubmissionViewSet, basename='quizsubmission')
router.register(r'answers', AnswerViewSet, basename='answer')
router.register(r'capstone-projects', CapstoneProjectViewSet, basename='capstoneproject')
router.register(r'live-sessions', LiveSessionViewSet, basename='livesession')
router.register(r'user-settings', UserSettingsViewSet, basename='usersettings')
router.register(r'activity-logs', ActivityLogViewSet, basename='activitylog')
router.register(r'certificate-requests', CertificateRequestViewSet, basename='certificate-request')

urlpatterns = [
    path('', include(router.urls)),
    path('lessons/<int:pk>/add-note/', LessonViewSet.as_view({'post': 'add_note', 'put': 'update_note', 'delete': 'delete_note'}), name='lesson-add-note'),
]