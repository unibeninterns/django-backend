from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q, CheckConstraint, UniqueConstraint
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid


class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_weeks = models.IntegerField(default=12)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    tutors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='users.TutorCourse',  # explicit through model
        related_name='courses_as_tutor',
        blank=True,
        limit_choices_to={'role': 'tutor'}
    )

    certificate_request_message = models.TextField(
        blank=True,
        help_text="Message shown to students when requesting a certificate"
    )
    certificate_enabled = models.BooleanField(default=True)

    syllabus_published = models.BooleanField(default=False)
    syllabus_published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.title

class CourseObjective(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='objectives'
    )
    text = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ('course', 'order')

    def __str__(self):
        return f"{self.course.title} – {self.text}"

class Module(models.Model):
    id = models.AutoField(primary_key=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    order = models.PositiveIntegerField()  # 1, 2, 3, 4...
    title = models.CharField(max_length=200)
    week_number = models.PositiveIntegerField(
        validators=[
            MaxValueValidator(12),
            MinValueValidator(1)
        ],
        help_text="A value between 1 and 12."
    )
    description = models.TextField()

    # Module completion requirements
    requires_all_lessons = models.BooleanField(default=True)
    requires_all_quizzes = models.BooleanField(default=True)
    requires_project_submission = models.BooleanField(default=False)
    requires_live_session_attendance = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['course', 'order'], name='unique_course_order')
        ]
        ordering = ['course', 'order']
        verbose_name = "Module"
        verbose_name_plural = "Modules"

    def save(self, *args, **kwargs):
        # If order is not set, assign the next number
        if self.order is None:
            last_order = Module.objects.filter(course=self.course).aggregate(
                models.Max('order')
            )['order__max']
            self.order = 1 if last_order is None else last_order + 1

        super().save(*args, **kwargs)

    def get_previous_module(self):
        """Get the module that comes before this one."""
        return Module.objects.filter(
            course=self.course,
            order__lt=self.order
        ).order_by('-order').first()

    def get_next_module(self):
        """Get the module that comes after this one."""
        return Module.objects.filter(
            course=self.course,
            order__gt=self.order
        ).order_by('order').first()

    def __str__(self):
        return f"{self.id} | {self.title} (Course: {self.course.title}, Order: {self.order}, Week {self.week_number})"

class Lesson(models.Model):
    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='lessons')
    title = models.CharField(max_length=200)
    order = models.PositiveIntegerField()  # Sequential ordering within module

    # Video requirements
    has_video = models.BooleanField(default=False)
    video_duration_minutes = models.PositiveIntegerField(default=0)
    minimum_watch_percentage = models.FloatField(default=80.0)  # Must watch 80% of video

    class Meta:
        constraints = [
            UniqueConstraint(fields=['module', 'order'], name='unique_module_order')
        ]
        ordering = ['module', 'order']

    def get_previous_lesson(self):
        """Get the previous lesson in sequence."""
        return Lesson.objects.filter(
            module=self.module,
            order__lt=self.order
        ).order_by('-order').first()

    def get_next_lesson(self):
        """Get the next lesson in sequence."""
        return Lesson.objects.filter(
            module=self.module,
            order__gt=self.order
        ).order_by('order').first()

    def __str__(self):
        return f"Week: {self.module.week_number}| (Title {self.title})"

class LessonNote(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lesson_notes')
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()  # Individual note content
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.student.email} - {self.lesson.title} - {self.created_at}"

class ContentItem(models.Model):
    TYPE_CHOICES = (
        ('video', 'Video'),
        ('pdf', 'PDF'),
        ('quiz', 'Quiz'),
        ('text', 'Text'),
    )
    id = models.AutoField(primary_key=True)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='content_items')
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='content_files/', null=True, blank=True)
    external_url = models.URLField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    content = models.TextField(null=True, blank=True)

    def __str__(self):
        try:
            course_title = self.lesson.module.course.title
        except AttributeError:
            course_title = "No Course Assigned"

        return f"{self.title} (ID: {self.id}) | {course_title}"

class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    #  change the null and blank fields both to False in production
    lesson = models.OneToOneField(
        Lesson, on_delete=models.CASCADE, null=True, blank=True, related_name="quiz"
    )
    module = models.ForeignKey(
        Module, on_delete=models.CASCADE, null=True, blank=True, related_name="quizzes"
    )
    title = models.CharField(max_length=200)

    # Quiz requirements
    passing_score = models.FloatField(
        default=70.0,
        validators=[
            MinValueValidator(0.0),
            MaxValueValidator(100.0)
        ],
        help_text="Passing score percentage (0.0 to 100.0)."
    )
    max_attempts = models.PositiveIntegerField(
        default=5,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5)
        ],
        help_text="Maximum number of attempts allowed (1 to 5)."
    )
    is_required_for_module = models.BooleanField(default=True)

    is_published = models.BooleanField(default=False)

    status = models.CharField(
        max_length=10,
        choices=(
            ('draft', 'Draft'),
            ('published', 'Published'),
        ),
        default='draft',
        db_index = True
    )

    def save(self, *args, **kwargs):
        # Ensure quiz is linked to either lesson OR module (not both)
        if self.lesson and self.module:
            raise ValidationError("A quiz can only be linked to either a lesson OR a module, not both.")
        if not self.lesson and not self.module:
            raise ValidationError("A quiz must be linked to either a lesson OR a module.")

        # Fix: only include associations that actually exist
        associations = [a for a in [self.lesson, self.module] if a is not None]

        for assoc in associations:
            if hasattr(assoc, "course") and assoc.course != getattr(self, "course", None):
                self.course = assoc.course  # keep course consistent

        # Validate passing_score and max_attempts
        if not (0 <= self.passing_score <= 100):
            raise ValidationError("Passing score must be between 0 and 100.")
        if not (1 <= self.max_attempts <= 5):
            raise ValidationError("Max attempts must be between 1 and 3.")

        super().save(*args, **kwargs)

    def __str__(self):
        lesson_order = self.lesson.order if self.lesson else 'N/A'
        module_week = self.module.week_number if self.module else 'N/A'
        return f"Quiz: {self.id} | {self.title} for Lesson {lesson_order} | Module {module_week}"

    class Meta:
        verbose_name = "Quiz"
        verbose_name_plural = "Quizzes"
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['lesson']),
        ]
        constraints = [
            CheckConstraint(
                check=Q(passing_score__gte=0.0) & Q(passing_score__lte=100.0),
                name='quiz_passing_score_range'
            ),
            CheckConstraint(
                check=Q(max_attempts__gte=1) & Q(max_attempts__lte=5),
                name='quiz_max_attempts_range'
            ),
        ]

class Question(models.Model):
    TYPE_CHOICES = (
        ('multiple_choice', 'Multiple Choice'),
        ('true_false', 'True/False'),
        ('essay', 'Essay'),
    )
    id = models.AutoField(primary_key=True)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    text = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    options = models.JSONField(null=True, blank=True)  # e.g., {'A': 'option1', 'B': 'option2'}
    correct_answer = models.CharField(max_length=255, null=True, blank=True)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.text} (ID: {self.id})"

class QuizSubmission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField()
    is_finalized = models.BooleanField(
        default=True,
        help_text="False if manual grading is required and not yet completed."
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Logic: If the quiz has essays, it's not finalized by default
        # (This is just one way to automate it)
        if not self.pk and self.quiz.questions.filter(type='essay').exists():
            self.is_finalized = False
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"

class Answer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()
    points_earned = models.FloatField(null=True, blank=True)  # null means "not yet graded"
    teacher_feedback = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Answer to {self.question.text}"

class CapstoneInstructions(models.Model):
    """
    THE ASSIGNMENT (Static).
    Created by Admin. One per Course.
    Contains the prompt, resources, and requirements.
    """
    course = models.ForeignKey('Course', on_delete=models.CASCADE, related_name='capstone_instructions')

    title = models.CharField(max_length=200)
    description = models.TextField(help_text="The prompt the student must answer.")
    instruction_file = models.FileField(upload_to='capstone_resources/', null=True, blank=True)

    # Requirements
    requires_peer_review = models.BooleanField(default=False)

    def __str__(self):
        return f"Instructions for {self.course.title}"

class CapstoneProject(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    instructions = models.ForeignKey(CapstoneInstructions, on_delete=models.CASCADE, related_name='submissions', default='')
    title = models.CharField(max_length=200)
    description = models.TextField()
    submission_file = models.FileField(upload_to='capstone_projects/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    grade = models.CharField(
        max_length=10,
        choices=[
            ('A+', 'A+'),
            ('A', 'A'),
            ('A-', 'A-'),
            ('B+', 'B+'),
            ('B', 'B'),
            ('B-', 'B-'),
            ('C+', 'C+'),
            ('C', 'C'),
            ('C-', 'C-'),
            ('D+', 'D+'),
            ('D', 'D'),
            ('F', 'F'),
            ('N/A', 'Not Graded')
        ],
        null=True,
        blank=True,
        default='N/A',
        help_text="Grade assigned to the capstone project."
    )

    grade2 = models.CharField(
        max_length=10,
        choices=[
            ('PASS', 'Pass'),
            ('FAIL', 'Fail'),
            ('N/A', 'Not Graded')
        ],
        null=True,
        blank=True,
        default='N/A',
        help_text="Pass or Fail grade for the capstone project."
    )

    class Meta:
        verbose_name = "Capstone Project"
        verbose_name_plural = "Capstone Projects"

    # Project requirements
    requires_submission = models.BooleanField(default=True)
    requires_peer_review = models.BooleanField(default=False)
    requires_instructor_approval = models.BooleanField(default=False)



    def __str__(self):
        return f"Project done by {self.student.username} - {self.student.email} for {self.instructions.title}"

class LiveSession(models.Model):
    id = models.AutoField(primary_key=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='live_sessions')
    title = models.CharField(max_length=200)
    meeting_url = models.URLField()
    scheduled_time = models.DateTimeField()
    duration = models.DurationField()
    is_mandatory = models.BooleanField(default=False)
    minimum_attendance_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Live Session"
        verbose_name_plural = "Live Sessions"

    def __str__(self):
        return f"Live session held in  Week: {self.module.week_number} for Module: {self.module.order}"

    @property
    def status(self):
        now = timezone.now()
        end_time = self.scheduled_time + self.duration

        if now < self.scheduled_time:
            return "upcoming"
        elif self.scheduled_time <= now <= end_time:
            return "ongoing"
        elif now > end_time:
            return "completed"

class LiveSessionAttendance(models.Model):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='live_attendances'
    )
    live_session = models.ForeignKey(
        LiveSession,
        on_delete=models.CASCADE,
        related_name='module_attendances'
    )
    joined_at = models.DateTimeField()
    left_at = models.DateTimeField(null=True, blank=True)
    attended_minutes = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ('student', 'live_session')
        verbose_name = "Live Session Attendance"
        verbose_name_plural = "Live Session Attendances"

    def __str__(self):
        return f"{self.student} → {self.live_session}"

class UserSettings(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='settings')
    notifications_enabled = models.BooleanField(default=True)  # Example setting
    theme = models.CharField(max_length=20, choices=[('light', 'Light'), ('dark', 'Dark')], default='light')  # Example setting
    email_alerts = models.BooleanField(default=True)  # Another example

    def __str__(self):
        return f"Settings for {self.user.email}"

class ActivityLog(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='activity_logs')
    activity_type = models.CharField(max_length=50, choices=[
        ('completed_module', 'Completed Module'),
        ('downloaded_item', 'Downloaded Item'),
        ('started_quiz', 'Started Quiz'),
        ('completed_quiz', 'Completed Quiz'),
    ])  # Define common activity types
    content_id = models.PositiveIntegerField(null=True, blank=True)  # Links to Module or ContentItem ID
    content_type = models.CharField(max_length=20, choices=[
        ('module', 'Module'),
        ('content_item', 'ContentItem'),
        ('quiz', 'Quiz'),
    ], null=True, blank=True)  # Type of content
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True)  # Optional additional info (e.g., score)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.student.email} - {self.activity_type} at {self.timestamp}"

class Certificate(models.Model):
    STATUS_CHOICES = (
        ('issued', 'Issued'),
        ('revoked', 'Revoked'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificates'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='course_certificates'
    )

    certificate_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='issued'
    )

    verification_code = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='issued_certificates'
    )

    verification_hash = models.CharField(
        max_length=255,
        unique=True,
        db_index=True
    )

    pdf_file = models.FileField(
        upload_to='certificates/pdfs/',
        null=True,
        blank=True
    )
    image_file = models.ImageField(
        upload_to='certificates/images/',
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ('student', 'course')
        ordering = ['-issued_at']
        verbose_name = "Certificate"
        verbose_name_plural = "Certificates"

    def __str__(self):
        return f"{self.student} - {self.course} ({self.status})"

class CertificateRequest(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_ISSUED = 'issued'
    STATUS_DENIED = 'denied'
    STATUS_REVOKED = 'revoked'
    STATUS_PAYMENT_PENDING = 'payment_pending'
    STATUS_PAYMENT_FAILED = 'payment_failed'

    STATUS_CHOICES = (
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_DENIED, 'Denied'),
        (STATUS_REVOKED, 'Revoked'),
        (STATUS_PAYMENT_PENDING, 'Payment Pending'),
        (STATUS_PAYMENT_FAILED, 'Payment Failed'),
        (STATUS_ISSUED, 'issued'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificate_requests'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificate_requests'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    requested_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_certificate_requests'
    )
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    reason = models.TextField(blank=True)

    last_previewed_at = models.DateTimeField(null=True, blank=True)
    last_previewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='certificate_previews'
    )

    serial_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    class Meta:
        ordering = ['-requested_at']
        verbose_name = "Certificate Request"
        verbose_name_plural = "Certificate Requests"
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                name='unique_certificate_request'
            )
        ]

    def generate_serial(self):
        """Generates a unique ID: QN-2026-A1B2-77"""
        year = timezone.now().year
        short_uuid = uuid.uuid4().hex[:4].upper()
        return f"QN-{year}-{short_uuid}-{self.id}"

    def __str__(self):
        return f"{self.student} → {self.course} ({self.status})"

class CertificatePayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    )

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificate_payments'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='certificate_payments'
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    reference = models.CharField(
        max_length=100,
        unique=True,
        db_index=True
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    manually_marked = models.BooleanField(default=False)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='manually_marked_certificate_payments'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Certificate Payment"
        verbose_name_plural = "Certificate Payments"
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course'],
                name='unique_certificate_payment'
            )
        ]

    def __str__(self):
        return f"{self.student} → {self.course} ({self.status}) | {self.id}"

class CertificateRevocationLog(models.Model):
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='revocation_logs'
    )

    revoked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )

    reason = models.TextField()
    revoked_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-revoked_at']
        verbose_name = "Certificate Revocation Log"
        verbose_name_plural = "Certificate Revocation Logs"

    def __str__(self):
        return f"Revoked {self.certificate.certificate_number}"

class Announcement(models.Model):
    ALL = 'all'
    STUDENTS = 'students'
    TUTORS = 'tutors'

    AUDIENCE_CHOICES = [
        (ALL, 'All'),
        (STUDENTS, 'Students'),
        (TUTORS, 'Tutors'),
    ]

    title = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="announcements"
    )
    audience = models.CharField(
        max_length=10,
        choices=AUDIENCE_CHOICES,
        default=ALL
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

class Resource(models.Model):
    content_item = models.OneToOneField(
        ContentItem,
        on_delete=models.CASCADE,
        related_name='resource',
        null=True # set this to False in production
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='resources'
    )

    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name='resources',
        null=True,
        blank=True
    )

    RESOURCE_VISIBILITY = (
        ('public', 'Public'),
        ('enrolled', 'Enrolled Students'),
        ('tutors', 'Tutors Only'),
        ('admin', 'Admin Only'),
    )

    visibility = models.CharField(
        max_length=20,
        choices=RESOURCE_VISIBILITY,
        default='enrolled'
    )

    is_active = models.BooleanField(default=True)

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_resources'
    )

    created_at = models.DateTimeField(auto_now_add=True)

class ResourceActivity(models.Model):
    ACTION_CHOICES = (
        ('view', 'View'),
        ('download', 'Download'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='activities'
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['resource', 'action']),
            models.Index(fields=['user']),
            models.Index(fields=['created_at']),
        ]