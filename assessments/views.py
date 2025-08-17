from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from module.permissions import IsAdminUser, IsStudent, IsOwnerOrAdmin, CanAccessContent
from core.common.utils.progress import get_content_state
from assessments.models import SessionAttendance
from assessments.serializers import SessionAttendanceSerializer
from users.models import CustomUser

class SessionAttendanceViewSet(viewsets.ModelViewSet):
    queryset = SessionAttendance.objects.all()
    serializer_class = SessionAttendanceSerializer

    def get_permissions(self):
        """Apply permissions based on action."""
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}
        if self.action in crud_actions:
            return [IsAdminUser()]
        elif self.action in {'list', 'retrieve'}:
            return [IsStudent(), IsOwnerOrAdmin(), CanAccessContent()]
        return [AllowAny()]

    def get_queryset(self):
        """Filter attendance records based on user access."""
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return SessionAttendance.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return SessionAttendance.objects.all()
        return SessionAttendance.objects.none()

    def get_serializer_context(self):
        """Add session accessibility details to serializer context."""
        context = super().get_serializer_context()
        if self.action == 'retrieve':
            user = self.request.user
            if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
                obj = self.get_object()
                context.update({
                    'session_state': get_content_state(user, 'module', obj.session.module.id).value
                })
        return context