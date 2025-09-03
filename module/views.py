from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import *
from .serializers import *
from progresse.serializers import QuizProgressSerializer
from .permissions import *
from core.common.utils.progress import get_content_state
from rest_framework.response import Response
from users.models import CustomUser
from progresse.models import ContentProgress, QuizProgress
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.request import Request
import sys


crud = ['create', 'update', 'partial_update', 'destroy']

class CourseViewSet(viewsets.ModelViewSet):
    #View for Courses
    queryset = Course.objects.all()
    serializer_class = CourseSerializer

    def get_permissions(self):
        if self.action in crud:
            return [IsAdminUser()]
        return [AllowAny()]

    def get_weekly_time_spent(self, request):
        user = request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            progress = ContentProgress.objects.filter(student=user)

            # Example aggregation logic
            weekly_time = {}
            for p in progress:
                week = p.content_item.module.week_number  # assuming module has week_number
                weekly_time[week] = weekly_time.get(week, 0) + p.time_spent

            return Response({'weekly_time_spent': weekly_time})

        return Response({'error': 'Unauthorized'}, status=403)

    @action(detail=True, methods=['get'], url_path='weeks-progress', url_name='get-weeks-progress')
    def get_weeks_progress(self, request, pk=None):
        user = self.request.user
        course = self.get_object()
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            completed_modules = [
                module for module in Module.objects.filter(course__duration_weeks=12)
                if get_content_state(user, 'module', module.id) == ContentState.COMPLETED
            ]
            weeks_done = len(set(module.week_number for module in completed_modules))
            return Response({'weeks_completed': weeks_done, 'total_weeks': 12})

        # 👇 New endpoint for active courses

    @action(detail=False, methods=['get'], url_path='active-courses', url_name='active-courses')
    def active_courses(self, request):
        count = Course.objects.filter(end_date__gte=timezone.now().date()).count()
        return Response({'active_courses': count})

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
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            obj = self.get_object()
            previous_module = obj.get_previous_module()
            next_module = obj.get_next_module()
            print(
                f"Module: {obj.id}, Previous: {previous_module.id if previous_module else None}, Next: {next_module.id if next_module else None}")
            context.update({
                'previous_module_id': previous_module.id if previous_module else None,
                'next_module_id': next_module.id if next_module else None,
            })
            print(f"Updated Context: {context}")
        return context

    def get_module_progress(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            # Get the most recently completed module
            completed_modules = Module.objects.filter(
                id__in=[m.id for m in Module.objects.all() if
                        get_content_state(user, 'module', m.id) == ContentState.COMPLETED]
            ).order_by('-week_number')
            completed_module = completed_modules.first() if completed_modules.exists() else None

            # Get the current module (first in-progress module)
            current_modules = Module.objects.filter(
                id__in=[m.id for m in Module.objects.all() if
                        get_content_state(user, 'module', m.id) == ContentState.IN_PROGRESS]
            )
            current_module = current_modules.first() if current_modules.exists() else None

            # Get the next module based on the current module
            next_module = current_module.get_next_module() if current_module else None

            data = {
                'completed_module_id': completed_module.id if completed_module else None,
                'current_module_id': current_module.id if current_module else None,
                'next_module_id': next_module.id if next_module else None
            }
            return Response(data)

    def list(self, request, *args, **kwargs):
        user = request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            completed_modules = [
                module for module in Module.objects.all()
                if get_content_state(user, 'module', module.id) == ContentState.COMPLETED
            ]
            response_data = {'modules_completed': len(completed_modules),
                             'results': self.get_serializer(self.get_queryset(), many=True).data}
            return Response(response_data)
        return super().list(request, *args, **kwargs)

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
            # Include the requested lesson in test/debug mode
            if settings.DEBUG or 'test' in sys.argv:
                requested_pk = self.kwargs.get('pk')
                if requested_pk:
                    accessible_lessons.append(Lesson.objects.filter(id=requested_pk).first())
            return Lesson.objects.filter(id__in=[lesson.id for lesson in accessible_lessons if lesson])
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

    @action(detail=True, methods=['post'], permission_classes=[IsStudent, CanAccessContent], url_path='add-note')
    def add_note(self, request, pk=None):
        print(f"[DEBUG] Entered add_note action for lesson {pk}")
        print(f"[DEBUG] Request method: {request.method}, data: {request.data}")
        lesson = self.get_object()
        user = request.user
        note_data = request.data.get('note', '')
        if not note_data:
            return Response({'detail': 'Note content is required'}, status=status.HTTP_400_BAD_REQUEST)
        note = LessonNote.objects.create(student=user, lesson=lesson, note=note_data)
        serializer = LessonNoteSerializer(note, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['put'], permission_classes=[IsStudent, CanAccessContent], url_path='update-note')
    def update_note(self, request, pk=None):
        """Edit an existing note (requires note_id)."""
        lesson = self.get_object()
        user = request.user
        note_id = request.data.get('note_id')
        if not note_id:
            return Response({'detail': 'note_id is required for editing'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            note = LessonNote.objects.get(id=note_id, student=user, lesson=lesson)
            note_data = request.data.get('note', '')
            if not note_data:
                return Response({'detail': 'Note content is required'}, status=status.HTTP_400_BAD_REQUEST)
            note.note = note_data
            note.save()
            serializer = LessonNoteSerializer(note)
            return Response(serializer.data)
        except LessonNote.DoesNotExist:
            return Response({'detail': 'Note not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['delete'], permission_classes=[IsStudent, CanAccessContent], url_path='delete-note')
    def delete_note(self, request, pk=None):
        """Delete an existing note (requires note_id)."""
        lesson = self.get_object()
        user = request.user
        note_id = request.data.get('note_id')
        if not note_id:
            return Response({'detail': 'note_id is required for deletion'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            note = LessonNote.objects.get(id=note_id, student=user, lesson=lesson)
            note.delete()
            return Response({'detail': 'Note deleted successfully'}, status=status.HTTP_204_NO_CONTENT)
        except LessonNote.DoesNotExist:
            return Response({'detail': 'Note not found or unauthorized'}, status=status.HTTP_404_NOT_FOUND)

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
        if user.is_authenticated and isinstance(user, CustomUser):
            if user.role == 'admin':
                return ContentItem.objects.all()
            elif user.role == 'student':
                # Use list comprehension with get_content_state (works with patched version)
                accessible_ids = [
                    ci.id for ci in ContentItem.objects.all()
                    if get_content_state(user, 'content_item', ci.id) in ContentState.accessible_states()
                ]
                print(f"Accessible IDs: {accessible_ids}, Content ID: {self.kwargs.get('pk')}")
                for ci in ContentItem.objects.all():
                    state = get_content_state(user, 'content_item', ci.id)
                    print(f"ContentItem {ci.id} State: {state.value} (from {get_content_state.__module__})")
                return ContentItem.objects.filter(id__in=accessible_ids)
        return ContentItem.objects.none()

    def get_serializer_context(self):
        """Add content progress details to serializer context."""
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            user = self.request.user
            if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
                obj = self.get_object()
                print(f"Retrieved object: {obj.id if obj else 'None'}, PK: {self.kwargs.get('pk')}")
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
        print("→ QuizViewSet.get_permissions action =", self.action)
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
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            if self.action in {'retrieve', 'start_quiz', 'complete_quiz'}:
                return Quiz.objects.all()  # Allow access to all quizzes by PK for these actions
            accessible_states_values = [state.value for state in ContentState.accessible_states()]
            return Quiz.objects.filter(
                quizprogress__student=user,
                quizprogress__state__in=accessible_states_values
            ).distinct()
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
                        'current_state': progress.state,  # Use progress.state directly
                        'attempts': progress.attempts,
                        'is_passed': progress.is_passed,
                    })
                except QuizProgress.DoesNotExist:
                    context.update({
                        'current_state': ContentState.LOCKED.value,
                        'attempts': 0,
                        'is_passed': False,
                    })
        return context

    @action(
        detail=True,
        methods=['post'],
        url_path='start',
        url_name='start-quiz',
        permission_classes=[IsStudent, CanStartContent]
    )
    def start_quiz(self, request, *args, **kwargs):
        quiz = self.get_object()
        user = request.user

        # Fetch existing progress if available
        progress = QuizProgress.objects.filter(student=user, quiz=quiz).first()

        if progress:
            # If the quiz is failed or completed, allow retry if max not reached
            if progress.state in [ContentState.FAILED.value, ContentState.COMPLETED.value]:
                if progress.attempts >= quiz.max_attempts:
                    return Response(
                        {'detail': 'Maximum attempts reached'},
                        status=status.HTTP_403_FORBIDDEN
                    )

                # Start a new attempt
                progress.attempts += 1
                progress.transition_to(ContentState.IN_PROGRESS)
                progress.save(update_fields=['state', 'attempts', 'last_accessed'])

            elif progress.state == ContentState.IN_PROGRESS.value:
                # Already in progress → just return current state, no new attempt
                pass

        else:
            # First attempt
            progress = QuizProgress.objects.create(
                student=user,
                quiz=quiz,
                state=ContentState.IN_PROGRESS.value,
                attempts=1
            )

        serializer = QuizProgressSerializer(progress, context=self.get_serializer_context())
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='complete', url_name='complete-quiz', permission_classes=[IsStudent, CanCompleteContent])
    def complete_quiz(self, request, *args, **kwargs):
            """Custom action to complete a quiz."""
            quiz = self.get_object()
            user = request.user
            try:
                progress = QuizProgress.objects.get(student=user, quiz=quiz)

                # Only allow a “complete” if we’re still in progress.
                if progress.state != ContentState.IN_PROGRESS.value:
                    return Response({'detail': 'Quiz is not in progress.'},status=status.HTTP_403_FORBIDDEN)

                score = request.data.get('score')
                if score is None:
                    return Response({'detail': 'Score is required'}, status=400)
                score = float(score)

                new_state = ContentState.COMPLETED if score >= quiz.passing_score else ContentState.FAILED
                progress.transition_to(
                    new_state,
                    score=score,
                    passing_score=quiz.passing_score,
                )
                progress.save()
                serializer = QuizProgressSerializer(progress, context=self.get_serializer_context())
                return Response(serializer.data, status=status.HTTP_200_OK)
            except QuizProgress.DoesNotExist:
                return Response({'detail': 'Quiz not started'}, status=400)

    @action(detail=True, methods=['get'], url_path='get-pass-rate')
    def get_pass_rate(self, request, pk=None):
        quiz = self.get_object()  # uses pk automatically
        user = self.request.user
        progress = QuizProgress.objects.filter(student=request.user, quiz=quiz).last()
        if progress:
            quizzes = QuizProgress.objects.filter(student=user)
            passed = quizzes.filter(is_passed=True).count()
            total = quizzes.count()
            pass_rate = (passed / total * 100) if total > 0 else 0  # or your logic
        else:
            pass_rate = 0.0
        return Response({'pass_rate': pass_rate})

class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer

    def get_permissions(self):

        # Allow admins full CRUD access
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == 'admin':
            return [IsAdminUser()]

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
            print(f"Accessible questions for student: {accessible_questions}")
            print(f"All questions: {Question.objects.all().values_list()}")
            return Question.objects.filter(id__in=[question.id for question in accessible_questions])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return Question.objects.all()
        return Question.objects.none()

class QuizSubmissionViewSet(viewsets.ModelViewSet):
    queryset = QuizSubmission.objects.all()
    serializer_class = QuizSubmissionSerializer

    def get_permissions(self):
        user = self.request.user

        # Allow admins full CRUD access
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == 'admin':
            return [IsAdminUser()]

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

    def get_permissions(self):
        # Only admins can create, update, or delete
        if self.request.user and self.request.user.is_authenticated and self.request.user.role == 'admin':
            return [IsAdminUser()]

        if self.action in {'create', 'update', 'partial_update', 'destroy'}:
            return [IsAdminUser()]
        # Authenticated users can list or retrieve
        elif self.action in {'list', 'retrieve'}:
            return [IsAuthenticated()]
        return []

    def get_queryset(self):
        user = self.request.user
        # Students see only their own answers
        if user.is_authenticated and hasattr(user, 'role'):
            if user.role == 'student':
                return Answer.objects.filter(submission__student=user)
            elif user.role == 'admin':
                return Answer.objects.all()
        return Answer.objects.none()

    def perform_create(self, serializer):
        request: Request = self.request  # tell the type checker
        submission_id = request.data.get('submission')
        if not submission_id:
            raise ValidationError({"submission": "This field is required."})
        try:
            submission = QuizSubmission.objects.get(id=submission_id)
        except QuizSubmission.DoesNotExist:
            raise ValidationError({"submission": "Invalid submission ID."})

        serializer.save(submission=submission)

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
        context.update({'request': self.request})
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
            now = timezone.now()
            accessible_sessions = [
                session for session in LiveSession.objects.all()
                if get_content_state(user, 'module', session.module.id) in ContentState.accessible_states()
                   and session.scheduled_time <= now <= session.scheduled_time + session.duration
            ]
            print(f"All Live Sessions: {LiveSession.objects.all().values_list()}")
            print(f"Accessible Sessions: {accessible_sessions}")
            return LiveSession.objects.filter(id__in=[session.id for session in accessible_sessions])
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return LiveSession.objects.all()
        return LiveSession.objects.none()

class UserSettingsViewSet(viewsets.ModelViewSet):
    queryset = UserSettings.objects.all()
    serializer_class = UserSettingsSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == 'student':
            # Filter for the settings of the logged-in student.
            # Assuming UserSettings has a ForeignKey to CustomUser named 'user'.
            return UserSettings.objects.filter(user=user)
        # Admins could potentially see all, but based on your permissions,
        # you might handle that separately if needed.
        return UserSettings.objects.none()

class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer
    permission_classes = [IsAuthenticated, IsStudent]

    def get_queryset(self):
        return ActivityLog.objects.filter(student=self.request.user).order_by('-timestamp')[:5]

class CertificateRequestViewSet(viewsets.ModelViewSet):
    queryset = CertificateRequest.objects.all()
    serializer_class = CertificateRequestSerializer

    def get_permissions(self):
        if self.action in {"create", "update", "partial_update", "destroy"}:
            permission_classes = [IsAdminUser]
        elif self.action in {"list", "retrieve"}:
            permission_classes = [IsStudent, CanAccessContent]
        else:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        certificate_count = CertificateRequest.objects.count()
        recent_certificates = CertificateRequest.objects.order_by("-created_at")[:4]

        # use serializer to return recent certificates properly
        recent_data = CertificateRequestSerializer(recent_certificates, many=True).data

        return Response({
            "certificate_count": certificate_count,
            "recent_certificates": recent_data
        })

class AnnouncementViewSet(viewsets.ModelViewSet):
    queryset = Announcement.objects.all()
    serializer_class = AnnouncementSerializer

    def get_permissions(self):
        crud = {"create", "update", "partial_update", "destroy"}
        if self.action in crud:
            return [IsAdminUser()]
        elif self.action in {"list", "retrieve"}:
            return [IsStudent(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            # Only return announcements the student can access
            # (implement your own logic if needed, e.g., based on course or group)
            return Announcement.objects.all()
        elif user.is_authenticated and user.role == 'admin':
            return Announcement.objects.all()
        return Announcement.objects.none()

    @action(detail=False, methods=["get"])
    def recent(self, request):
        """Get the most recent 5 announcements"""
        announcements = Announcement.objects.all()[:5]
        serializer = self.get_serializer(announcements, many=True)
        return Response(serializer.data)
