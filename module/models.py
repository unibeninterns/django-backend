from django.db import models
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db.models import Q, CheckConstraint, UniqueConstraint

class Course(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    duration_weeks = models.IntegerField(default=12)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.title

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

    constraints = [
        UniqueConstraint(fields=['course', 'order'], name='unique_course_order')
    ]
    ordering = ['course', 'order']
    verbose_name = "Module"
    verbose_name_plural = "Modules"

    # suggestions say I should use

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
        return f"{self.title} |Course: {self.order}| (Week {self.week_number})"

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
        return self.title

class Quiz(models.Model):
    id = models.AutoField(primary_key=True)
    module = models.ForeignKey('module.Module', on_delete=models.CASCADE, related_name='quizzes')
    lesson = models.ForeignKey('module.Lesson', on_delete=models.CASCADE, related_name='quizzes', null=True, blank=True)
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
        default=3,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3)
        ],
        help_text="Maximum number of attempts allowed (1 to 3)."
    )
    is_required_for_module = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Validate associations: Quiz must be associated with exactly one of lesson or module
        associations = [self.lesson, self.module]
        if sum(1 for assoc in associations if assoc) != 1:
            raise ValueError("A quiz must be associated with exactly one of: lesson, module.")

        # Additional validation for new fields
        if self.passing_score < 0.0 or self.passing_score > 100.0:
            raise ValueError("Passing score must be between 0.0 and 100.0.")
        if self.max_attempts < 1:
            raise ValueError("Maximum attempts must be at least 1.")

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Quiz: {self.title} for Lesson {self.lesson.order if self.lesson else 'N/A'} | Module {self.module.week_number if self.module else 'N/A'}"

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
                check=Q(max_attempts__gte=1) & Q(max_attempts__lte=3),
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

    def __str__(self):
        return self.text

class QuizSubmission(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.FloatField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student.username} - {self.quiz.title}"

class Answer(models.Model):
    submission = models.ForeignKey(QuizSubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    answer_text = models.TextField()

    def __str__(self):
        return f"Answer to {self.question.text}"

class Payment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_option = models.CharField(max_length=50) #might set this to a choice field
    transaction_id = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=(('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed')))
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.payment_option}"

class Enrollment(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    payment = models.OneToOneField(Payment, on_delete=models.SET_NULL, null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=(('active', 'Active'), ('completed', 'Completed'), ('dropped', 'Dropped')))

    def __str__(self):
        return f"{self.user.username} - {self.course.title}"

class CapstoneProject(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField()
    submission_file = models.FileField(upload_to='capstone_projects/')
    submitted_at = models.DateTimeField(auto_now_add=True)
    module = models.ForeignKey(Module, on_delete=models.CASCADE, related_name='projects')
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
        return f"Project done by {self.student.username} - {self.student.email}"

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
