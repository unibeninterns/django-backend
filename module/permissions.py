from rest_framework import permissions
from core.common.utils import progress
from core.common.utils.progress_states import ContentState
from module.models import *

class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'admin'

class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.role == 'admin':
            return True
        if hasattr(obj, 'student'):
            return obj.student == request.user
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

class IsStudent(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.role == 'student'

class CanAccessContent(permissions.BasePermission):
    """Base permission for content access using state machine."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'id'):
            self.message = f"Object {obj} does not have an 'id' attribute"
            return False
        content_type = self._get_content_type(obj)
        content_id = obj.id

        current_state = progress.get_content_state(request.user, content_type, content_id)

        if current_state not in ContentState.accessible_states():
            self.message = self._get_error_message(request.user, obj, current_state)
            return False

        return True

    def _get_content_type(self, obj):
        """Determine content type from model instance."""
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
    """Permission for starting content."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'id'):
            self.message = f"Object {obj} does not have an 'id' attribute"
            return False
        content_type = self._get_content_type(obj)
        current_state = progress.get_content_state(request.user, content_type, obj.id)

        if current_state not in ContentState.startable_states():
            self.message = f"Cannot start content from {current_state.value} state"
            return False

        return True

    def _get_content_type(self, obj):
        return obj.__class__.__name__.lower()

class CanCompleteContent(permissions.BasePermission):
    """Permission for completing content."""
    def has_object_permission(self, request, view, obj):
        if not hasattr(obj, 'id'):
            self.message = f"Object {obj} does not have an 'id' attribute"
            return False
        content_type = self._get_content_type(obj)
        current_state = progress.get_content_state(request.user, content_type, obj.id)

        if current_state not in ContentState.completable_states():
            self.message = f"Cannot complete content from {current_state.value} state"
            return False

        return True

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