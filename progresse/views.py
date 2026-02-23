from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from module.permissions import IsAdminUser, IsStudent, IsOwnerOrAdmin
from users.models import CustomUser
from progresse.models import *
from progresse.serializers import *
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models.functions import ExtractWeek, ExtractYear
from django.db.models import Avg


class ContentProgressViewSet(viewsets.ModelViewSet):
    queryset = ContentProgress.objects.all()
    serializer_class = ContentProgressSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}

        if self.action in crud_actions:
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

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
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

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
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return ModuleCompletion.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ModuleCompletion.objects.all()
        return ModuleCompletion.objects.none()

    @action(detail=False, methods=['get'])
    def weekly_completion(self, request):
        """Return weekly average completion stats grouped by module."""
        qs = self.get_queryset().filter(is_completed=True)
        data = (
            qs.annotate(
                week=ExtractWeek("completed_at"),
                year=ExtractYear("completed_at")
            )
            .values("week", "year", "module__title")
            .annotate(avg_completion=Avg("completion_percentage"))
            .order_by("-year", "-week")
        )
        return Response(data)


class QuizProgressViewSet(viewsets.ModelViewSet):
    queryset = QuizProgress.objects.all()
    serializer_class = QuizProgressSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}

        if self.action in crud_actions:
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return QuizProgress.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return QuizProgress.objects.all()
        return QuizProgress.objects.none()


class ProjectProgressViewSet(viewsets.ModelViewSet):
    queryset = ProjectProgress.objects.all()
    serializer_class = ProjectProgressSerializer

    def get_permissions(self):
        crud_actions = {'create', 'update', 'partial_update', 'destroy'}

        if self.action in crud_actions:
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

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
            # Keep your admin lock here for editing/deleting
            return [IsAdminUser()]

        elif self.action in {'list', 'retrieve'}:
            # FIX: Just require them to be logged in.
            # Your get_queryset() will automatically protect the data.
            return [IsAuthenticated()]

        return [AllowAny()]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return ProgressEvent.objects.filter(student=user)
        elif user.is_authenticated and isinstance(user, CustomUser) and user.role == 'admin':
            return ProgressEvent.objects.all()
        return ProgressEvent.objects.none()