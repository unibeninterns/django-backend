from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import *
from .serializers import *
from .permissions import *
from core.common.utils.progress import get_content_state
from rest_framework.response import Response
from users.models import CustomUser
from progresse.models import ContentProgress, QuizProgress


crud = ['create', 'update', 'partial_update', 'destroy']


class CourseViewSet(viewsets.ModelViewSet):
    #View for Courses
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in crud:
            return [IsAdminUser()]
        return [AllowAny()]

class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.all()
    serializer_class = ModuleSerializer

    def get_permissions(self):
        if self.action in crud:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        """Filter modules based on user access."""
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            # Only return modules the user can access (based on ContentState)
            accessible_modules = [
                module for module in Module.objects.all()
                if get_content_state(user, 'module', module.id) in ContentState.accessible_states()
            ]
            return Module.objects.filter(id__in=[module.id for module in accessible_modules])
        elif user.is_authenticated and user.role == 'admin':
            return Module.objects.all()
        return Module.objects.none()

    def get_serializer_context(self):
        """Add previous and next module IDs to serializer context."""
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            obj = self.get_object()
            previous_module = obj.get_previous_module()
            next_module = obj.get_next_module()
            context.update({
                'previous_module_id': previous_module.id if previous_module else None,
                'next_module_id': next_module.id if next_module else None,
            })
        return context

class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer

    def get_permissions(self):
        """Apply permissions based on action."""
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        """Filter lessons based on user access."""
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            accessible_lessons = [
                lesson for lesson in Lesson.objects.all()
                if get_content_state(user, 'lesson', lesson.id) in ContentState.accessible_states()
            ]
            return Lesson.objects.filter(id__in=[lesson.id for lesson in accessible_lessons])
        elif user.is_authenticated and user.role == 'admin':
            return Lesson.objects.all()
        return Lesson.objects.none()

    def get_serializer_context(self):
        """Add previous and next lesson IDs to serializer context."""
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            obj = self.get_object()
            previous_lesson = obj.get_previous_lesson()
            next_lesson = obj.get_next_lesson()
            context.update({
                'previous_lesson_id': previous_lesson.id if previous_lesson else None,
                'next_lesson_id': next_lesson.id if next_lesson else None,
            })
        return context

class ContentItemViewSet(viewsets.ModelViewSet):
    queryset = ContentItem.objects.all()
    serializer_class = ContentItemSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            accessible_content_items = [
                content_item for content_item in ContentItem.objects.all()
                if get_content_state(user, 'content_item', content_item.id) in ContentState.accessible_states()
            ]
            return ContentItem.objects.filter(id__in=[content_item.id for content_item in accessible_content_items])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ContentItem.objects.all()
        return ContentItem.objects.none()

    def get_serializer_context(self):
        """Add content progress details to serializer context."""
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            user = self.request.user
            if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
                obj = self.get_object()
                try:
                    progress = ContentProgress.objects.get(student=user, content_item=obj)
                    context.update({
                        'current_state': get_content_state(user, 'content_item', obj.id).value,
                    })
                except ContentProgress.DoesNotExist:
                    context.update({
                        'current_state': ContentState.LOCKED.value,
                    })
        return context

class QuizViewSet(viewsets.ModelViewSet):
    queryset = Quiz.objects.all()
    serializer_class = QuizSerializer

    def get_permissions(self):
        """Apply permissions based on action."""
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        elif self.action == 'start_quiz':
            return [IsStudent(), CanStartContent()]
        elif self.action == 'complete_quiz':
            return [IsStudent(), CanCompleteContent()]
        return [AllowAny()]

    def get_queryset(self):
        """Filter quizzes based on user access."""
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            accessible_quizzes = [
                quiz for quiz in Quiz.objects.all()
                if get_content_state(user, 'quiz', quiz.id) in ContentState.accessible_states()
            ]
            return Quiz.objects.filter(id__in=[quiz.id for quiz in accessible_quizzes])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Quiz.objects.all()
        return Quiz.objects.none()

    def get_serializer_context(self):
        """Add quiz progress details to serializer context."""
        context = super().get_serializer_context()
        if self.action in {'retrieve', 'start_quiz', 'complete_quiz'}:
            user = self.request.user
            if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
                obj = self.get_object()
                try:
                    progress = QuizProgress.objects.get(student=user, quiz=obj)
                    context.update({
                        'current_state': get_content_state(user, 'quiz', obj.id).value,
                        'attempts_made': progress.attempts,  # Fixed from progress.attempts
                        'is_passed': progress.is_passed,
                    })
                except QuizProgress.DoesNotExist:
                    context.update({
                        'current_state': ContentState.LOCKED.value,
                        'attempts_made': 0,
                        'is_passed': False,
                    })
        return context

    def start_quiz(self, request, *args, **kwargs):
        """Custom action to start a quiz."""
        quiz = self.get_object()
        user = request.user
        try:
            progress = QuizProgress.objects.get(student=user, quiz=quiz)
            if progress.attempts >= quiz.max_attempts:  # Fixed from progress.attempts
                return Response({'detail': 'Maximum attempts reached'}, status=400)
            progress.transition_to(ContentState.IN_PROGRESS)
        except QuizProgress.DoesNotExist:
            progress = QuizProgress.objects.create(
                student=user,
                quiz=quiz,
                state=ContentState.IN_PROGRESS.value,
                attempts_made=0
            )
        progress.attempts += 1
        progress.save()
        serializer = self.get_serializer(quiz, context=self.get_serializer_context())
        return Response(serializer.data)

    def complete_quiz(self, request, *args, **kwargs):
        """Custom action to complete a quiz."""
        quiz = self.get_object()
        user = request.user
        try:
            progress = QuizProgress.objects.get(student=user, quiz=quiz)
            score = request.data.get('score')
            if score is None:
                return Response({'detail': 'Score is required'}, status=400)
            score = float(score)
            progress.score = score
            progress.is_passed = score >= quiz.passing_score
            new_state = ContentState.COMPLETED if progress.is_passed else ContentState.FAILED
            progress.transition_to(new_state)
            progress.save()
            serializer = self.get_serializer(quiz, context=self.get_serializer_context())
            return Response(serializer.data)
        except QuizProgress.DoesNotExist:
            return Response({'detail': 'Quiz not started'}, status=400)

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            accessible_questions = [
                question for question in Question.objects.all()
                if get_content_state(user, 'quiz', question.quiz.id) in ContentState.accessible_states()
            ]
            return Question.objects.filter(id__in=[question.id for question in accessible_questions])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Question.objects.all()
        return Question.objects.none()

class QuizSubmissionViewSet(viewsets.ModelViewSet):
    queryset = QuizSubmission.objects.all()
    serializer_class = QuizSubmissionSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return QuizSubmission.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return QuizSubmission.objects.all()
        return QuizSubmission.objects.none()

class AnswerViewSet(viewsets.ModelViewSet):
    queryset = Answer.objects.all()
    serializer_class = AnswerSerializer

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return Answer.objects.filter(submission__student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Answer.objects.all()
        return Answer.objects.none()

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return Payment.objects.filter(user=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Payment.objects.all()
        return Payment.objects.none()

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return Enrollment.objects.filter(user=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Enrollment.objects.all()
        return Enrollment.objects.none()

class CapstoneProjectViewSet(viewsets.ModelViewSet):
    queryset = CapstoneProject.objects.all()
    serializer_class = CapstoneProjectSerializer

    def perform_create(self, serializer):
        serializer.save(student=self.request.user)

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return CapstoneProject.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return CapstoneProject.objects.all()
        return CapstoneProject.objects.none()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            user = self.request.user
            if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
                obj = self.get_object()
                context.update({
                    'current_state': get_content_state(user, 'project', obj.id).value,
                })
        return context

class LiveSessionViewSet(viewsets.ModelViewSet):
    queryset = LiveSession.objects.all()
    serializer_class = LiveSessionSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            accessible_sessions = [
                session for session in LiveSession.objects.all()
                if get_content_state(user, 'module', session.module.id) in ContentState.accessible_states()
            ]
            return LiveSession.objects.filter(id__in=[session.id for session in accessible_sessions])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return LiveSession.objects.all()
        return LiveSession.objects.none()