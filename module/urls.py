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
router.register(r'announcements', AnnouncementViewSet, basename='announcements')
router.register(r'resources', ResourceViewSet, basename='resources')

router.register(
    r'admin-courses-quiz-stats',
    AdminCourseQuizStatsViewSet,
    basename='admin-courses-quiz-stats'
)

router.register(r'admin-courses', AdminCourseViewSet, basename='admin-courses')

router.register(r'admin-modules', AdminModuleViewSet, basename='admin-modules')

router.register(r'admin-quizzes', AdminQuizViewSet, basename='admin-quizzes')

router.register(r'live-session-stats', AdminLiveSessionStatsViewSet, basename='live-stats')

router.register(r'admin-quiz-overview', AdminQuizOverviewViewSet, basename='admin-quiz-overview')

router.register(r'admin-questions', AdminQuestionViewSet, basename='admin-questions')

router.register(r'admin-courses-stats', AdminCourseStatsViewSet, basename='admin-courses-stats')

router.register(r'admin/certificates/analytics', AdminCertificateAnalyticsViewSet, basename='admin-certificate-analytics')

# router.register(r'certificate-analytics', AdminCertificateAnalyticsViewSet, basename='cert-analytics')

router.register(r'admin-resources', AdminResourceViewSet, basename='admin-resources')


# router.register(
#     r'quiz-manage',
#     AdminQuizManageViewSet,
#     basename='admin-quiz-manage'
# )
#
# router.register(
#     r'admin-questions',
#     AdminQuestionManageViewSet,
#     basename='admin-questions'
# )

urlpatterns = [
    path('', include(router.urls)),
    path('lessons/<int:pk>/add-note/', LessonViewSet.as_view({'post': 'add_note', 'put': 'update_note', 'delete': 'delete_note'}), name='lesson-add-note'),
    path('tutors/search/', TutorSearchView.as_view(), name='tutor-search'),
    path('certificates/verify/<str:identifier>/', PublicCertificateVerificationView.as_view(), name='certificate-verify'),
    path('certificates/export/csv/', CertificateRequestsCSVExportView.as_view(), name='certificate-export-csv'),
    path('notifications/analytics/', NotificationAnalyticsView.as_view(), name='notification-analytics'),
    path('announcements-analytics/', AnnouncementAnalyticsView.as_view(), name='announcements-analytics'),
]