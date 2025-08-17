from rest_framework import serializers
from assessments.models import SessionAttendance

class SessionAttendanceSerializer(serializers.ModelSerializer):
    session_state = serializers.CharField(read_only=True, allow_null=True)

    class Meta:
        model = SessionAttendance
        fields = [
            'id', 'student', 'session', 'was_present', 'attendance_duration_minutes',
            'created_at', 'updated_at', 'session_state'
        ]