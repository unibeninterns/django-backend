from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'courses', CourseViewSet)
router.register(r'modules', ModuleViewSet)
router.register(r'lessons', LessonViewSet)
router.register(r'content-items', ContentItemViewSet)
router.register(r'quizzes', QuizViewSet)
router.register(r'questions', QuestionViewSet)
router.register(r'quiz-submissions', QuizSubmissionViewSet)
router.register(r'answers', AnswerViewSet)
router.register(r'payments', PaymentViewSet)
router.register(r'enrollments', EnrollmentViewSet)
router.register(r'capstone-projects', CapstoneProjectViewSet)
router.register(r'live-sessions', LiveSessionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]