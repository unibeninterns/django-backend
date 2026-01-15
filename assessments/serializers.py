from rest_framework import serializers
from .models import SessionAttendance, Reminder, Notification

class SessionAttendanceSerializer(serializers.ModelSerializer):
    session_state = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = SessionAttendance
        fields = [
            'id', 'student', 'session', 'was_present', 'attendance_duration_minutes',
            'created_at', 'updated_at', 'session_state'
        ]

class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = [
            'id',
            'reminder_type',
            'audience',
            'course',
            'message',
            'sent_at'
        ]

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id',
            'message',
            'is_read',
            'created_at'
        ]