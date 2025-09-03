from rest_framework import serializers
from .models import *
from core.common.utils.progress import get_content_state
from progresse.models import QuizProgress

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
    previous_module_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_module_id = serializers.IntegerField(read_only=True, allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        context = self.context
        # Ensure context values override default field values
        data['previous_module_id'] = context.get('previous_module_id', data.get('previous_module_id'))
        data['next_module_id'] = context.get('next_module_id', data.get('next_module_id'))
        print(f"Serializer Data - Module: {instance.id}, Previous: {data['previous_module_id']}, Next: {data['next_module_id']}")
        return data

    class Meta:
        model = Module
        fields = [
            'id', 'course', 'order', 'title', 'week_number', 'description',
            'requires_all_lessons', 'requires_all_quizzes', 'requires_project_submission',
            'requires_live_session_attendance', 'previous_module_id', 'next_module_id'
        ]

class LessonNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonNote
        fields = ['id', 'student', 'lesson', 'note', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class LessonSerializer(serializers.ModelSerializer):
    previous_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)
    notes = LessonNoteSerializer(read_only=True, many=True)  # List of all notes for the user

    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'order', 'has_video', 'video_duration_minutes',
            'minimum_watch_percentage', 'previous_lesson_id', 'next_lesson_id', 'notes'
        ]

    def get_notes(self, obj):
        user = self.context['request'].user
        if user.is_authenticated and isinstance(user, CustomUser) and user.role == 'student':
            return obj.notes.filter(student=user)
        return []

class ContentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        context = self.context
        data['current_state'] = context.get('current_state', data.get('current_state', 'locked'))
        return data

class QuizSerializer(serializers.ModelSerializer):
    current_state = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    is_passed = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id', 'module', 'lesson', 'title', 'passing_score', 'max_attempts',
            'is_required_for_module', 'current_state', 'attempts', 'is_passed'
        ]

    def get_current_state(self, obj):
        user = self.context['request'].user
        progress = QuizProgress.objects.filter(student=user, quiz=obj).first()
        return progress.state if progress else None

    def get_attempts(self, obj):
        user = self.context['request'].user
        progress = QuizProgress.objects.filter(student=user, quiz=obj).first()
        return progress.attempts if progress else 0

    def get_is_passed(self, obj):
        user = self.context['request'].user
        progress = QuizProgress.objects.filter(student=user, quiz=obj).first()
        return progress.is_passed if progress else False

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class QuizSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSubmission
        fields = '__all__'

class AnswerSerializer(serializers.ModelSerializer):
    submission = serializers.PrimaryKeyRelatedField(
        queryset=QuizSubmission.objects.all(),  # Set a valid queryset here
        write_only=True
    )

    class Meta:
        model = Answer
        fields = ['id', 'submission', 'question', 'answer_text']

class CapstoneProjectSerializer(serializers.ModelSerializer):
    current_state = serializers.SerializerMethodField()

    class Meta:
        model = CapstoneProject
        fields = '__all__'

    def get_current_state(self, obj):
        if 'current_state' in self.context:
            return self.context['current_state']
        request = self.context.get('request')
        if request:
            return get_content_state(request.user, 'project', obj.id).value
        return None

class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = '__all__'

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['id', 'notifications_enabled', 'theme', 'email_alerts']
        read_only_fields = ['id']

    def create(self, validated_data):
        user = self.context['request'].user
        settings, created = UserSettings.objects.get_or_create(user=user, defaults=validated_data)
        return settings

    def update(self, instance, validated_data):
        instance.notifications_enabled = validated_data.get('notifications_enabled', instance.notifications_enabled)
        instance.theme = validated_data.get('theme', instance.theme)
        instance.email_alerts = validated_data.get('email_alerts', instance.email_alerts)
        instance.save()
        return instance

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'activity_type', 'content_id', 'content_type', 'timestamp', 'details']
        read_only_fields = ['id', 'timestamp', 'student']  # Student is set via view

    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)

class CertificateRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CertificateRequest
        fields = '__all__'

class AnnouncementSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Announcement
        fields = ["id", "title", "message", "created_at", "updated_at", "created_by"]