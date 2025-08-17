from rest_framework.routers import DefaultRouter
from progresse.views import *

router = DefaultRouter()
router.register(r'content-progress', ContentProgressViewSet, basename='content-progress')
router.register(r'lesson-progress', LessonProgressViewSet, basename='lesson-progress')
router.register(r'module-completions', ModuleCompletionViewSet, basename='module-completion')
router.register(r'quiz-progress', QuizProgressViewSet, basename='quiz-progress')
router.register(r'project-progress', ProjectProgressViewSet, basename='project-progress')
router.register(r'progress-events', ProgressEventViewSet, basename='progress-event')
urlpatterns = router.urls