from rest_framework import serializers
from progresse.models import *

class ContentProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentProgress
        fields = [
            'id', 'student', 'content_item', 'state', 'is_completed',
            'progress_percentage', 'time_spent', 'last_accessed',
            'completed_at', 'started_at', 'attempts', 'completion_data'
        ]

class LessonProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonProgress
        fields = [
            'id', 'student', 'lesson', 'state', 'is_completed',
            'progress_percentage', 'time_spent', 'started_at',
            'completed_at', 'last_accessed', 'video_watch_percentage',
            'completion_data'
        ]

class ModuleCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ModuleCompletion
        fields = [
            'id', 'student', 'module', 'state', 'is_completed',
            'completion_percentage', 'completed_at', 'time_spent',
            'started_at', 'completion_data'
        ]

class QuizProgressSerializer(serializers.ModelSerializer):
    current_state = serializers.CharField(source='state', read_only=True)

    class Meta:
        model = QuizProgress
        fields = [
            'id', 'student', 'quiz', 'state', 'attempts', 'best_score',
            'latest_score', 'is_passed', 'started_at', 'completed_at',
            'last_accessed', 'completion_data', 'current_state', 'state'
        ]
        extra_kwargs = {
            'state': {'write_only': True}  # optional: keep `state` for input only
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        # If the user is a student, remove the sensitive score/internal fields
        if request and request.user.role == 'student':
            hidden_fields = [
                'id', 'student', 'best_score', 'latest_score',
                'is_passed', 'started_at', 'completed_at',
                'completion_data', 'quiz', 'state'
            ]
            for field in hidden_fields:
                data.pop(field, None)
        return data


class ProgressEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressEvent
        fields = [
            'id', 'student', 'content_type', 'content_id', 'event_type',
            'old_state', 'new_state', 'metadata', 'timestamp'
        ]


class ProjectProgressSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectProgress
        fields = [
            'id', 'student', 'instructions', 'state', 'is_submitted',
            'is_instructor_approved', 'is_peer_reviewed', 'started_at',
            'submitted_at', 'approved_at', 'completed_at', 'last_accessed',
            'completion_data'
        ]