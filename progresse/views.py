from rest_framework import viewsets
from rest_framework.permissions import AllowAny
from module.permissions import IsAdminUser, IsStudent, IsOwnerOrAdmin
from users.models import CustomUser
from progresse.models import *
from progresse.serializers import *

class ContentProgressViewSet(viewsets.ModelViewSet):
    queryset = ContentProgress.objects.all()
    serializer_class = ContentProgressSerializer

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
            return ContentProgress.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ContentProgress.objects.all()
        return ContentProgress.objects.none()


class LessonProgressViewSet(viewsets.ModelViewSet):
    queryset = LessonProgress.objects.all()
    serializer_class = LessonProgressSerializer

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
            return LessonProgress.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return LessonProgress.objects.all()
        return LessonProgress.objects.none()


class ModuleCompletionViewSet(viewsets.ModelViewSet):
    queryset = ModuleCompletion.objects.all()
    serializer_class = ModuleCompletionSerializer

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
            return ModuleCompletion.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ModuleCompletion.objects.all()
        return ModuleCompletion.objects.none()


class QuizProgressViewSet(viewsets.ModelViewSet):
    queryset = QuizProgress.objects.all()
    serializer_class = QuizProgressSerializer

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
            return QuizProgress.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return QuizProgress.objects.all()
        return QuizProgress.objects.none()


class ProjectProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectProgress
        fields = [
            'id', 'student', 'project', 'state', 'is_submitted',
            'is_instructor_approved', 'is_peer_reviewed', 'started_at',
            'submitted_at', 'approved_at', 'completed_at', 'last_accessed',
            'completion_data'
        ]


class ProjectProgressViewSet(viewsets.ModelViewSet):
    queryset = ProjectProgress.objects.all()
    serializer_class = ProjectProgressSerializer

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
            return ProjectProgress.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ProjectProgress.objects.all()
        return ProjectProgress.objects.none()


class ProgressEventViewSet(viewsets.ModelViewSet):
    queryset = ProgressEvent.objects.all()
    serializer_class = ProgressEventSerializer

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
            return ProgressEvent.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ProgressEvent.objects.all()
        return ProgressEvent.objects.none()