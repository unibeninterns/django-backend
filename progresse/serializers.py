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
    class Meta:
        model = QuizProgress
        fields = [
            'id', 'student', 'quiz', 'state', 'attempts', 'best_score',
            'latest_score', 'is_passed', 'started_at', 'completed_at',
            'last_accessed', 'completion_data'
        ]


class ProgressEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressEvent
        fields = [
            'id', 'student', 'content_type', 'content_id', 'event_type',
            'old_state', 'new_state', 'metadata', 'timestamp'
        ]