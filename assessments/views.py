from rest_framework import viewsets, status
from rest_framework.permissions import AllowAny, IsAdminUser
from module.permissions import IsAdminUser, IsStudent, IsOwnerOrAdmin, CanAccessContent
from core.common.utils.progress import get_content_state
from assessments.models import SessionAttendance
from assessments.serializers import SessionAttendanceSerializer
from users.models import CustomUser
from rest_framework.response import Response
from .models import Reminder, Notification
from .serializers import ReminderSerializer, NotificationSerializer
from .services import send_reminder
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from .tasks import send_reminder_task

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

class ReminderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ReminderSerializer
    queryset = Reminder.objects.all().order_by('-sent_at')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 1. Save the reminder to the DB so the worker can find it
        reminder = serializer.save(sent_by=request.user)

        # 2. Push the ID to Redis. The worker will pick it up.
        send_reminder_task.delay(reminder.id)

        # 3. Respond to the Admin immediately
        return Response(
            {'detail': 'Reminder has been queued and is being sent in the background.'},
            status=status.HTTP_201_CREATED
        )

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

        unread = self.request.query_params.get('unread')
        if unread == 'true':
            qs = qs.filter(is_read=False)

        return qs

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()

        return Response({'unread_count': count})

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        notification = self.get_object()
        notification.is_read = True
        notification.save(update_fields=['is_read'])

        return Response({'detail': 'Notification marked as read.'})

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        Notification.objects.filter(
            user=request.user,
            is_read=False
        ).update(is_read=True)

        return Response({'detail': 'All notifications marked as read.'})

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        Notification.objects.filter(
            user=request.user
        ).delete()

        return Response({'detail': 'Notifications cleared.'})

