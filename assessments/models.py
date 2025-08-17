from django.db import models
from django.conf import settings
from django.db.models import UniqueConstraint

class SessionAttendance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_attendances'
    )
    session = models.ForeignKey(
        'module.LiveSession',
        on_delete=models.CASCADE,
        related_name='attendances'
    )
    was_present = models.BooleanField(default=False)
    attendance_duration_minutes = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Duration of attendance in minutes."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Session Attendance"
        verbose_name_plural = "Session Attendances"
        constraints = [
            UniqueConstraint(fields=['student', 'session'], name='unique_student_session')
        ] # Ensure one attendance record per student per session

    def __str__(self):
        return f"{self.student.email} - {self.session} - {'Present' if self.was_present else 'Absent'}"
