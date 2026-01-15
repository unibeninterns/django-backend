from rest_framework import permissions
from core.common.utils import progress
from core.common.utils.progress_states import ContentState
from progresse.models import QuizProgress
from module.models import *
import logging
from users.models import CustomUser

logger = logging.getLogger(__name__)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        print(f"[IsStudent] has_permission? user={request.user!r}")
        allowed = (
                request.user.is_authenticated and
                isinstance(request.user, CustomUser) and
                request.user.role == 'student'
        )
        print(f"[IsStudent] → {allowed}")
        return allowed

class IsTutor(permissions.BasePermission):
    def has_permission(self, request, view):
        print(f"[IsTutor] has_permission? user={request.user!r}")

        allowed = (
            request.user.is_authenticated and
            isinstance(request.user, CustomUser) and
            request.user.role == 'tutor'
        )

        print(f"[IsTutor] → {allowed}")
        return allowed

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        print(f"Checking permission for user: {request.user.email}, obj.user: {getattr(obj, 'user', None)}")
        if request.user.role == 'admin':
            return True
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

class CanAccessContent(permissions.BasePermission):
    """Base permission for content access using state machine."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'id'):
            self.message = f"Object {obj} does not have an 'id' attribute"
            return False
        content_type = self._get_content_type(obj)

        if content_type == 'course':
            from payments.models import Enrollment  # Ensure correct path
            from django.utils import timezone

            # Check for any active enrollment linked to a package of this course
            is_enrolled = Enrollment.objects.filter(
                user=request.user,
                package__course=obj,
                status='active'
            ).filter(
                models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=timezone.now())
            ).exists()

            if not is_enrolled:
                self.message = "You do not have an active enrollment for this course."
                return False
            return True

        content_id = obj.id

        logger.debug(f"Using get_content_state from: {progress.get_content_state.__module__}")

        # Debug: what arguments?
        logger.debug(f"Checking permission for user={request.user} "
                     f"type={content_type} id={content_id}")

        state = progress.get_content_state(request.user, content_type, content_id)

        # Debug: what state was returned?
        logger.debug(f"→ get_content_state returned {state}")

        current_state = progress.get_content_state(request.user, content_type, content_id)
        # print(f"Content Type: {content_type}, State: {current_state.value}")

        if current_state not in ContentState.accessible_states():
            self.message = self._get_error_message(request.user, obj, current_state)
            return False

        return True

    def _get_content_type(self, obj):
        """Determine content type from model instance."""
        # for ContentItem, use the declared `type` (video, article, etc.)
        if isinstance(obj, ContentItem):
            return obj.type

        # fallback to class name for other models (Lesson, Module, Quiz…)
        return obj.__class__.__name__.lower()


    def _get_error_message(self, user, obj, state):
        """Get specific error message based on content and state."""
        content_type = self._get_content_type(obj)

        if state == ContentState.LOCKED:
            if content_type == 'module':
                from core.common.utils.access_control import can_access_module
                _, reason = can_access_module(user, obj)
                return reason
            elif content_type == 'lesson':
                from core.common.utils.access_control import can_access_lesson
                _, reason = can_access_lesson(user, obj)
                return reason

        return f"Content not accessible in {state.value} state"

class CanStartContent(permissions.BasePermission):
    def has_permission(self, request, view):
        if view.action == 'start_quiz' and request.method == 'POST':
            return True
        return True

    def has_object_permission(self, request, view, obj):
        if view.action == 'start_quiz' and request.method == 'POST':
            user = request.user
            try:
                progress_obj = QuizProgress.objects.get(student=user, quiz=obj)
                if progress_obj.attempts >= obj.max_attempts:
                    self.message = "Maximum attempts reached."
                    return False
            except QuizProgress.DoesNotExist:
                return True
            return True

        content_type = self._get_content_type(obj)
        current_state = progress.get_content_state(request.user, content_type, obj.id)
        if current_state not in ContentState.startable_states():
            self.message = f"Cannot start content from {current_state.value} state"
            return False
        return True

    def _get_content_type(self, obj):
        return obj.__class__.__name__.lower()

class CanCompleteContent(permissions.BasePermission):
    """Only ensure the user is authenticated and has a QuizProgress record."""

    def has_permission(self, request, view):
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        return QuizProgress.objects.filter(student=request.user, quiz=obj).exists()

    def _get_content_type(self, obj):
        return obj.__class__.__name__.lower()


# class CanAccessLesson(CanAccessContent):
#     """Lesson-specific access permission."""
#     def has_object_permission(self, request, view, obj):
#         if not isinstance(obj, Lesson):  # Ensure obj is a Lesson
#             return False
#         return super().has_object_permission(request, view, obj)
#
# class CanAccessModule(CanAccessContent):
#     """Module-specific access permission."""
#     def has_object_permission(self, request, view, obj):
#         if not isinstance(obj, Module):
#             self.message = f"Expected Module object, got {type(obj).__name__}"
#             return False
#         return super().has_object_permission(request, view, obj)
#
# class CanAccessQuiz(CanAccessContent):
#     """Quiz-specific access permission."""
#     def has_object_permission(self, request, view, obj):
#         if not isinstance(obj, Quiz):
#             self.message = f"Expected Quiz object, got {type(obj).__name__}"
#             return False
#         return super().has_object_permission(request, view, obj)