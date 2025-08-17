from rest_framework import serializers
from .models import *

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = '__all__'

class ModuleSerializer(serializers.ModelSerializer):
    previous_module_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_module_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Module
        fields = [
            'id', 'course', 'order', 'title', 'week_number', 'description',
            'requires_all_lessons', 'requires_all_quizzes', 'requires_project_submission',
            'requires_live_session_attendance', 'previous_module_id', 'next_module_id'
        ]

class LessonSerializer(serializers.ModelSerializer):
    previous_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'order', 'has_video', 'video_duration_minutes',
            'minimum_watch_percentage', 'previous_lesson_id', 'next_lesson_id'
        ]

class ContentItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContentItem
        fields = '__all__'

class QuizSerializer(serializers.ModelSerializer):
    current_state = serializers.CharField(read_only=True, allow_null=True)
    attempts = serializers.IntegerField(read_only=True, allow_null=True)
    is_passed = serializers.BooleanField(read_only=True, allow_null=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'module', 'lesson', 'title', 'passing_score', 'max_attempts',
            'is_required_for_module', 'current_state', 'attempts', 'is_passed'
        ]

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'

class QuizSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSubmission
        fields = '__all__'

class AnswerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Answer
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'

class EnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = '__all__'

class CapstoneProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CapstoneProject
        fields = '__all__'

class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = '__all__'