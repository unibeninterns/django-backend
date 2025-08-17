from django.db import models
from django.conf import settings
from django.utils import timezone
from core.common.utils.progress_states import ContentState
from django.db.models import UniqueConstraint


class ContentProgress(models.Model):
    """Individual content item progresse with state tracking."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_item = models.ForeignKey('module.ContentItem', on_delete=models.CASCADE)

    state = models.CharField(
        max_length=20,
        choices=[(state.value, state.value) for state in ContentState],
        default=ContentState.LOCKED.value
    )

    # Existing fields
    is_completed = models.BooleanField(default=False)
    progress_percentage = models.FloatField(default=0.0)
    time_spent = models.IntegerField(default=0, help_text="Time spent in seconds")
    last_accessed = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # New fields for state management
    started_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)
    completion_data = models.JSONField(default=dict)  # Store scores, watch time, etc.


    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'content_item'], name='unique_student_content_item')
        ]
        indexes = [
            models.Index(fields=['student', 'state']),
            models.Index(fields=['content_item', 'state']),
        ]
        verbose_name = "ContentProgress"
        verbose_name_plural = "ContentProgresses"


    def get_state_enum(self):
        return ContentState(self.state)

    def transition_to(self, new_state: ContentState, **kwargs):
        """Safely transition to new state with timestamp tracking."""
        old_state = self.get_state_enum()

        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition from {old_state} to {new_state}")

        # Update state
        self.state = new_state.value

        # Update timestamps and boolean flags for backward compatibility
        if new_state == ContentState.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_state == ContentState.COMPLETED:
            self.completed_at = timezone.now()
            self.progress_percentage = 100.0
            self.is_completed = True  # Keep boolean flag for existing code

        # Update metadata
        if kwargs:
            self.completion_data.update(kwargs)

        self.save(update_fields=['state', 'started_at', 'completed_at', 'progress_percentage', 'is_completed',
                                 'completion_data'])

    def _is_valid_transition(self, from_state: ContentState, to_state: ContentState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            ContentState.LOCKED: [ContentState.AVAILABLE],
            ContentState.AVAILABLE: [ContentState.IN_PROGRESS],
            ContentState.IN_PROGRESS: [ContentState.COMPLETED, ContentState.FAILED],
            ContentState.FAILED: [ContentState.IN_PROGRESS],
            ContentState.COMPLETED: []  # Terminal state
        }
        return to_state in valid_transitions.get(from_state, [])

class LessonProgress(models.Model):
    """Lesson-level progresse tracking with state management."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    lesson = models.ForeignKey('module.Lesson', on_delete=models.CASCADE)

    # State tracking
    state = models.CharField(
        max_length=20,
        choices=[(state.value, state.value) for state in ContentState],
        default=ContentState.LOCKED.value
    )

    # Progress metrics
    is_completed = models.BooleanField(default=False)
    progress_percentage = models.FloatField(default=0.0)
    time_spent = models.IntegerField(default=0, help_text="Time spent in seconds")

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    # Lesson-specific data
    video_watch_percentage = models.FloatField(default=0.0)
    completion_data = models.JSONField(default=dict)


    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'lesson'], name='unique_student_lesson')
        ]
        indexes = [
            models.Index(fields=['student', 'state']),
            models.Index(fields=['lesson', 'state']),
        ]
        verbose_name = "LessonProgress"
        verbose_name_plural = "LessonProgresses"

    def get_state_enum(self):
        return ContentState(self.state)

    def transition_to(self, new_state: ContentState, **kwargs):
        """Safely transition to new state with timestamp tracking."""
        old_state = self.get_state_enum()

        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition from {old_state} to {new_state}")

        # Update state
        self.state = new_state.value

        # Update timestamps and boolean flags
        if new_state == ContentState.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_state == ContentState.COMPLETED:
            self.completed_at = timezone.now()
            self.progress_percentage = 100.0
            self.is_completed = True

        # Update metadata
        if kwargs:
            self.completion_data.update(kwargs)
            # Handle video watch percentage specifically
            if 'video_watch_percentage' in kwargs:
                self.video_watch_percentage = kwargs['video_watch_percentage']

        self.save(update_fields=['state', 'started_at', 'completed_at', 'progress_percentage', 'is_completed',
                                 'video_watch_percentage', 'completion_data'])

    def _is_valid_transition(self, from_state: ContentState, to_state: ContentState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            ContentState.LOCKED: [ContentState.AVAILABLE],
            ContentState.AVAILABLE: [ContentState.IN_PROGRESS],
            ContentState.IN_PROGRESS: [ContentState.COMPLETED, ContentState.FAILED],
            ContentState.FAILED: [ContentState.IN_PROGRESS],
            ContentState.COMPLETED: []  # Terminal state
        }
        return to_state in valid_transitions.get(from_state, [])

class ModuleCompletion(models.Model):
    """Module completion tracking with state management."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    module = models.ForeignKey('module.Module', on_delete=models.CASCADE)

    # Add state field to existing model
    state = models.CharField(
        max_length=20,
        choices=[(state.value, state.value) for state in ContentState],
        default=ContentState.LOCKED.value
    )

    # Existing fields
    is_completed = models.BooleanField(default=False)
    completion_percentage = models.FloatField(default=0.0)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent = models.IntegerField(default=0, help_text="Time spent in seconds")

    # New fields for state management
    started_at = models.DateTimeField(null=True, blank=True)
    completion_data = models.JSONField(default=dict)

    def get_state_enum(self):
        return ContentState(self.state)

    def transition_to(self, new_state: ContentState, **kwargs):
        """Safely transition to new state with timestamp tracking."""
        old_state = self.get_state_enum()

        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition from {old_state} to {new_state}")

        # Update state
        self.state = new_state.value

        # Update timestamps and boolean flags
        if new_state == ContentState.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_state == ContentState.COMPLETED:
            self.completed_at = timezone.now()
            self.completion_percentage = 100.0
            self.is_completed = True

        # Update metadata
        if kwargs:
            self.completion_data.update(kwargs)

        self.save(update_fields=['state', 'started_at', 'completed_at', 'completion_percentage', 'is_completed',
                                 'completion_data'])

    def _is_valid_transition(self, from_state: ContentState, to_state: ContentState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            ContentState.LOCKED: [ContentState.AVAILABLE],
            ContentState.AVAILABLE: [ContentState.IN_PROGRESS],
            ContentState.IN_PROGRESS: [ContentState.COMPLETED, ContentState.FAILED],
            ContentState.FAILED: [ContentState.IN_PROGRESS],
            ContentState.COMPLETED: []  # Terminal state
        }
        return to_state in valid_transitions.get(from_state, [])

    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'module'], name='unique_student_module')
        ]
        indexes = [
            models.Index(fields=['student', 'state']),
            models.Index(fields=['module', 'state']),
        ]
        verbose_name = "ModuleCompletion"
        verbose_name_plural = "ModuleCompletions"

    def __str__(self):
        return f"{self.student} - {self.module} ({self.state})"

class QuizProgress(models.Model):
    """Quiz progresse tracking with attempts and scoring."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    quiz = models.ForeignKey('module.Quiz', on_delete=models.CASCADE)

    # State tracking
    state = models.CharField(
        max_length=20,
        choices=[(state.value, state.value) for state in ContentState],
        default=ContentState.LOCKED.value
    )

    # Quiz-specific fields
    attempts = models.PositiveIntegerField(default=0)
    best_score = models.FloatField(default=0.0)
    latest_score = models.FloatField(default=0.0)
    is_passed = models.BooleanField(default=False)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    # Quiz attempt data
    completion_data = models.JSONField(default=dict)  # Store attempt history, answers, etc.

    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'quiz'], name='unique_student_quiz')
        ]
        indexes = [
            models.Index(fields=['student', 'state']),
            models.Index(fields=['quiz', 'state']),
        ]
        verbose_name = "QuizProgress"
        verbose_name_plural = "QuizProgress"

    def get_state_enum(self):
        return ContentState(self.state)

    def transition_to(self, new_state: ContentState, **kwargs):
        """Safely transition to new state with quiz-specific logic."""
        old_state = self.get_state_enum()

        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition from {old_state} to {new_state}")

        # Update state
        self.state = new_state.value

        # Update timestamps
        if new_state == ContentState.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_state == ContentState.COMPLETED:
            self.completed_at = timezone.now()
            # Check if passed based on score
            score = kwargs.get('score', 0)
            passing_score = kwargs.get('passing_score', 70)
            self.is_passed = score >= passing_score
        elif new_state == ContentState.FAILED:
            self.is_passed = False

        # Update quiz-specific data
        if 'score' in kwargs:
            self.latest_score = kwargs['score']
            self.best_score = max(self.best_score, self.latest_score)

        if 'attempt_data' in kwargs:
            self.attempts += 1
            self.completion_data.update(kwargs)

        self.save(
            update_fields=['state', 'started_at', 'completed_at', 'attempts', 'best_score', 'latest_score', 'is_passed',
                           'completion_data'])

    def _is_valid_transition(self, from_state: ContentState, to_state: ContentState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            ContentState.LOCKED: [ContentState.AVAILABLE],
            ContentState.AVAILABLE: [ContentState.IN_PROGRESS],
            ContentState.IN_PROGRESS: [ContentState.COMPLETED, ContentState.FAILED],
            ContentState.FAILED: [ContentState.IN_PROGRESS],  # Allow retries
            ContentState.COMPLETED: [ContentState.IN_PROGRESS]  # Allow retries for better score
        }
        return to_state in valid_transitions.get(from_state, [])

class ProjectProgress(models.Model):
    """Project progresse tracking with submission and approval workflow."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    project = models.ForeignKey('module.CapstoneProject', on_delete=models.CASCADE, default='')

    # State tracking
    state = models.CharField(
        max_length=20,
        choices=[(state.value, state.value) for state in ContentState],
        default=ContentState.LOCKED.value
    )

    # Project-specific fields
    is_submitted = models.BooleanField(default=False)
    is_instructor_approved = models.BooleanField(default=False)
    is_peer_reviewed = models.BooleanField(default=False)

    # Timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_accessed = models.DateTimeField(auto_now=True)

    # Project data
    completion_data = models.JSONField(default=dict)  # Store submission files, feedback, etc.

    class Meta:
        constraints = [
            UniqueConstraint(fields=['student', 'project'], name='unique_student_project')
        ]
        indexes = [
            models.Index(fields=['student', 'state']),
            models.Index(fields=['project', 'state']),
        ]
        verbose_name = "ProjectProgress"
        verbose_name_plural = "ProjectProgresses"

    def get_state_enum(self):
        return ContentState(self.state)

    def transition_to(self, new_state: ContentState, **kwargs):
        """Safely transition to new state with project-specific logic."""
        old_state = self.get_state_enum()

        # Validate transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid transition from {old_state} to {new_state}")

        # Update state
        self.state = new_state.value

        # Update timestamps and project-specific flags
        if new_state == ContentState.IN_PROGRESS and not self.started_at:
            self.started_at = timezone.now()
        elif new_state == ContentState.COMPLETED:
            self.completed_at = timezone.now()

        # Handle project-specific updates
        if 'submitted' in kwargs:
            self.is_submitted = kwargs['submitted']
            if self.is_submitted:
                self.submitted_at = timezone.now()

        if 'instructor_approved' in kwargs:
            self.is_instructor_approved = kwargs['instructor_approved']
            if self.is_instructor_approved:
                self.approved_at = timezone.now()

        if 'peer_reviewed' in kwargs:
            self.is_peer_reviewed = kwargs['peer_reviewed']

        # Update metadata
        if kwargs:
            self.completion_data.update(kwargs)

        self.save(update_fields=['state', 'started_at', 'submitted_at', 'approved_at', 'completed_at', 'is_submitted',
                                 'is_instructor_approved', 'is_peer_reviewed', 'completion_data'])

    def _is_valid_transition(self, from_state: ContentState, to_state: ContentState) -> bool:
        """Check if state transition is valid."""
        valid_transitions = {
            ContentState.LOCKED: [ContentState.AVAILABLE],
            ContentState.AVAILABLE: [ContentState.IN_PROGRESS],
            ContentState.IN_PROGRESS: [ContentState.COMPLETED, ContentState.FAILED],
            ContentState.FAILED: [ContentState.IN_PROGRESS],
            ContentState.COMPLETED: []  # Terminal state
        }
        return to_state in valid_transitions.get(from_state, [])

class ProgressEvent(models.Model):
    """Audit log of all progresse events."""
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content_type = models.CharField(max_length=20)  # 'lesson', 'module', 'quiz', 'project', 'content_item'
    content_id = models.PositiveIntegerField()

    event_type = models.CharField(max_length=30)  # 'state_change', 'unlock', 'access_denied'
    old_state = models.CharField(max_length=20, null=True)
    new_state = models.CharField(max_length=20, null=True)

    metadata = models.JSONField(default=dict)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['student', 'timestamp']),
            models.Index(fields=['content_type', 'content_id']),
        ]