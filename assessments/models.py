from django.db import models
from django.conf import settings
from django.db.models import UniqueConstraint
from module.models import Course

class SessionAttendance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='session_attendances'
    )
    session = models.ForeignKey(
        'module.LiveSession',
        on_delete=models.CASCADE,
        related_name='assessments_attendances'
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


class Reminder(models.Model):
    REMINDER_TYPE = (
        ('email', 'Email'),
        ('in_app', 'In App'),
    )

    AUDIENCE = (
        ('students', 'Students'),
        ('tutors', 'Tutors'),
        ('course', 'Course'),
    )

    reminder_type = models.CharField(max_length=20, choices=REMINDER_TYPE)
    audience = models.CharField(max_length=20, choices=AUDIENCE)

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    message = models.TextField()
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    sent_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    title = models.CharField(max_length=255, null=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )

    message = models.TextField()
    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title