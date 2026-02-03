from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import *
from core.common.utils.progress import get_content_state
from progresse.models import QuizProgress
from core.common.utils.progress_states import ContentState
from users.models import CustomUser, TutorCourse
from payments.models import Enrollment

User = get_user_model()

class ModuleSerializer(serializers.ModelSerializer):
    previous_module_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_module_id = serializers.IntegerField(read_only=True, allow_null=True)

    lesson_count = serializers.SerializerMethodField()
    quiz_count = serializers.SerializerMethodField()
    total_questions = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    completion_percentage = serializers.SerializerMethodField()
    lessons = serializers.SerializerMethodField()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        context = self.context
        # Ensure context values override default field values
        data['previous_module_id'] = context.get('previous_module_id', data.get('previous_module_id'))
        data['next_module_id'] = context.get('next_module_id', data.get('next_module_id'))
        print(f"Serializer Data - Module: {instance.id}, Previous: {data['previous_module_id']}, Next: {data['next_module_id']}")
        return data

    class Meta:
        model = Module
        fields = [
            'id', 'course', 'order', 'title', 'week_number', 'description',
            'requires_all_lessons', 'requires_all_quizzes', 'requires_project_submission',
            'requires_live_session_attendance', 'previous_module_id', 'next_module_id',
            'lesson_count', 'quiz_count', 'total_questions', 'average_score', 'completion_percentage', 'lessons'
        ]

    def get_lesson_count(self, obj):
        return obj.lessons.count()

    def get_quiz_count(self, obj):
        return Quiz.objects.filter(module=obj).count()

    def get_total_questions(self, obj):
        return Question.objects.filter(quiz__module=obj).count()

    def get_average_score(self, obj):
        progress_qs = QuizProgress.objects.filter(quiz__module=obj, state=ContentState.COMPLETED.value)
        if not progress_qs.exists():
            return 0
        return round(progress_qs.aggregate(avg_score=models.Avg('latest_score'))['avg_score'] or 0, 2)

    def get_completion_percentage(self, obj):
        # 1. Count only students enrolled in THIS course
        # (Assuming you have an Enrollment model linking User <-> Course)
        total_enrolled = Enrollment.objects.filter(
            package__course=obj.course,
            status='active'
        ).count()

        if total_enrolled == 0:
            return 0

        # 2. Count how many of THOSE students completed the module
        completed_count = QuizProgress.objects.filter(
            quiz__module=obj,
            state=ContentState.COMPLETED.value
        ).values('student').distinct().count()

        return round((completed_count / total_enrolled) * 100, 2)

    def get_lessons(self, obj):
        return LessonSerializer(obj.lessons.all(), many=True, context=self.context).data

class AdminModuleListSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    lesson_count = serializers.IntegerField(source='lessons.count', read_only=True)

    class Meta:
        model = Module
        fields = [
            'id',
            'course',
            'course_title',
            'order',
            'title',
            'week_number',
            'description',
            'lesson_count'
        ]

class CourseSerializer(serializers.ModelSerializer):
    total_quizzes = serializers.SerializerMethodField()
    published_quizzes = serializers.SerializerMethodField()
    draft_quizzes = serializers.SerializerMethodField()
    average_completion = serializers.SerializerMethodField()
    modules = ModuleSerializer(many=True, read_only=True)
    tutors = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=User.objects.filter(role='tutor'),
        required=False
    )

    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'duration_weeks', 'start_date', 'end_date',
            'total_quizzes', 'published_quizzes', 'draft_quizzes', 'average_completion',
            'modules', 'tutors'
        ]

    def create(self, validated_data):
        # 1. Remove tutors from validated_data before saving the course
        tutors = validated_data.pop('tutors', [])

        # 2. Create the course first
        course = Course.objects.create(**validated_data)

        # 3. Manually create the TutorCourse relationships
        for tutor in tutors:
            TutorCourse.objects.create(
                tutor=tutor,
                course=course,
                status='active'  # You can set default status here
            )

        return course

    def update(self, instance, validated_data):
        tutors = validated_data.pop('tutors', None)
        instance = super().update(instance, validated_data)

        if tutors is not None:
            # Sync tutors: remove old ones not in the list, add new ones
            instance.tutor_assignments.all().delete()  # Simple sync approach
            for tutor in tutors:
                TutorCourse.objects.create(tutor=tutor, course=instance)

        return instance

    def get_total_quizzes(self, obj):
        return Quiz.objects.filter(module__course=obj).count()

    def get_published_quizzes(self, obj):
        return Quiz.objects.filter(module__course=obj, is_required_for_module=True).count()

    def get_draft_quizzes(self, obj):
        return Quiz.objects.filter(module__course=obj, is_required_for_module=False).count()

    def get_average_completion(self, obj):
        # Average completion based on completed attempts
        progress_qs = QuizProgress.objects.filter(quiz__module__course=obj, state=ContentState.COMPLETED.value)
        total_attempts = progress_qs.count()
        if total_attempts == 0:
            return 0
        return round(progress_qs.aggregate(avg_score=models.Avg('latest_score'))['avg_score'] or 0, 2)

class LessonNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonNote
        fields = ['id', 'student', 'lesson', 'note', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'
        ordering = ['order']

class StudentQuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        # Explicitly exclude 'correct_answer' and 'order'
        fields = ['id', 'text', 'type', 'options']

class QuizSerializer(serializers.ModelSerializer):

    current_state = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()
    is_passed = serializers.SerializerMethodField()
    question_count = serializers.SerializerMethodField()
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Quiz
        fields = [
            'id', 'module', 'lesson', 'title', 'passing_score', 'max_attempts',
            'is_required_for_module', 'current_state', 'attempts', 'is_passed',
            'question_count', 'questions'
        ]

    def get_current_state(self, obj):
        # 1. Safely get request
        request = self.context.get('request')

        # 2. Check if request exists and user is logged in
        if request and request.user.is_authenticated:
            progress = QuizProgress.objects.filter(student=request.user, quiz=obj).first()
            return progress.state if progress else None
        return None

    def get_attempts(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = QuizProgress.objects.filter(student=request.user, quiz=obj).first()
            return progress.attempts if progress else 0
        return 0

    def get_is_passed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = QuizProgress.objects.filter(student=request.user, quiz=obj).first()
            return progress.is_passed if progress else False
        return False

    def get_question_count(self, obj):
        return obj.questions.count()

class QuizSummarySerializer(serializers.ModelSerializer):
    """
    Used when nesting inside Lessons/Modules.
    Hides questions and answers to prevent cheating and reduce payload size.
    """
    is_passed = serializers.SerializerMethodField()
    attempts = serializers.SerializerMethodField()

    question_count = serializers.SerializerMethodField()

    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'passing_score',
            'question_count',
            'is_passed',
            'attempts',
            'is_required_for_module'
        ]

    def get_attempts(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = QuizProgress.objects.filter(student=request.user, quiz=obj).first()
            return progress.attempts if progress else 0
        return 0

    def get_is_passed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            progress = QuizProgress.objects.filter(student=request.user, quiz=obj).first()
            return progress.is_passed if progress else False
        return False

    def get_question_count(self, obj):
        return obj.questions.count()

class LessonSummarySerializer(serializers.ModelSerializer):

    quiz = QuizSummarySerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'order', 'has_video', 'video_duration_minutes', 'quiz']

class ModuleStudentSerializer(serializers.ModelSerializer):
    """
    Fast, secure serializer for Students.
    Removes Admin stats and uses safe Lesson summary.
    """
    previous_module_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_module_id = serializers.IntegerField(read_only=True, allow_null=True)
    lessons = LessonSummarySerializer(many=True, read_only=True) # <--- Safe nesting
    # TODO: fetch the state of the module from module completion and pass it here

    class Meta:
        model = Module
        fields = [
            'id', 'course', 'order', 'title', 'week_number', 'description',
            'requires_all_lessons', 'requires_all_quizzes',
            'previous_module_id', 'next_module_id', 'lessons'
        ]

    def to_representation(self, instance):
        # Keep your navigation logic
        data = super().to_representation(instance)
        data['previous_module_id'] = self.context.get('previous_module_id')
        data['next_module_id'] = self.context.get('next_module_id')
        return data

class LessonSerializer(serializers.ModelSerializer):
    previous_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)
    next_lesson_id = serializers.IntegerField(read_only=True, allow_null=True)

    notes = serializers.SerializerMethodField()
    quiz = QuizSerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            'id', 'module', 'title', 'order', 'has_video', 'video_duration_minutes',
            'minimum_watch_percentage', 'previous_lesson_id', 'next_lesson_id', 'notes', 'quiz'
        ]

    def get_notes(self, obj):
        # 3. THIS LINE is why you need to pass context from the parent!
        # If the parent didn't pass context, this crashes with a KeyError or AttributeError.
        request = self.context.get('request')

        if request and request.user.is_authenticated and getattr(request.user, 'role', None) == 'student':
            # Filter: Only show notes created by THIS user
            my_notes = obj.notes.filter(student=request.user)

            # Manually serialize the filtered list
            return LessonNoteSerializer(my_notes, many=True).data

        return []

class ContentItemSerializer(serializers.ModelSerializer):
    current_state = serializers.SerializerMethodField()
    class Meta:
        model = ContentItem
        fields = '__all__'

    def get_current_state(self, obj):
        # This runs for EVERY item in a list AND for a single retrieve
        user = self.context.get('request').user
        if user and user.is_authenticated:
            # Call your central logic here
            return get_content_state(user, 'content_item', obj.id).value
        return 'locked'

class QuizSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuizSubmission
        fields = ['id', 'quiz', 'score', 'submitted_at']
        read_only_fields = ['score', 'submitted_at']

class AnswerSerializer(serializers.ModelSerializer):
    submission = serializers.PrimaryKeyRelatedField(
        queryset=QuizSubmission.objects.all(),  # Set a valid queryset here
        write_only=True
    )

    class Meta:
        model = Answer
        fields = ['id', 'submission', 'question', 'answer_text']

class CapstoneProjectSerializer(serializers.ModelSerializer):
    current_state = serializers.SerializerMethodField()

    class Meta:
        model = CapstoneProject
        fields = '__all__'

    def get_current_state(self, obj):
        if 'current_state' in self.context:
            return self.context['current_state']
        request = self.context.get('request')
        if request:
            return get_content_state(request.user, 'project', obj.id).value
        return None


class ExamQuestionAdminSerializer(serializers.ModelSerializer):
    """
    Standard serializer for Admins to CREATE/UPDATE questions.
    This accepts the full 'options' JSON including the 'correct' key.
    """
    class Meta:
        model = ExamQuestion
        fields = ['id', 'exam', 'text', 'question_type', 'points', 'order', 'options']

class ExamQuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for individual questions.
    Includes logic to HIDE the correct answer from the student.
    """
    options = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = ['id', 'text', 'question_type', 'points', 'order', 'options']

    def get_options(self, obj):
        """
        Sanitize the options JSON to remove the 'correct' key
        so students cannot see the answer in the API response.
        """
        # Create a copy so we don't modify the actual database object
        data = obj.options.copy() if obj.options else {}

        # If you store answers like: {"A": "Val", "B": "Val", "correct": "A"}
        # This removes "correct": "A"
        if 'correct' in data:
            del data['correct']

        return data


class FinalExamSerializer(serializers.ModelSerializer):
    """
    Main serializer for the Exam details.
    Nests the questions so the frontend gets everything in one call.
    """
    questions = ExamQuestionSerializer(many=True, read_only=True)

    # Optional: Add a field to show if the user has already submitted
    is_completed = serializers.SerializerMethodField()

    class Meta:
        model = FinalExam
        fields = [
            'id',
            'title',
            'course',
            'description',
            'duration_minutes',
            'passing_score',
            'questions',
            'is_completed'
        ]

    def get_is_completed(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return ExamSubmission.objects.filter(
                student=user,
                exam=obj,
                completed_at__isnull=False
            ).exists()
        return False


class ExamSubmissionSerializer(serializers.ModelSerializer):
    """
    Used when the student submits the exam or views their result.
    """

    class Meta:
        model = ExamSubmission
        fields = ['id', 'student', 'exam', 'score', 'passed', 'started_at', 'completed_at']
        read_only_fields = ['score', 'passed', 'completed_at']

class LiveSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveSession
        fields = '__all__'

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = ['id', 'notifications_enabled', 'theme', 'email_alerts']
        read_only_fields = ['id']

class ActivityLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ['id', 'activity_type', 'content_id', 'content_type', 'timestamp', 'details']
        read_only_fields = ['id', 'timestamp', 'student']  # Student is set via view

    def create(self, validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)

class CertificateRequestSerializer(serializers.ModelSerializer):
    # Make these read-only so the student can't "self-approve" or request for others
    student = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = CertificateRequest
        fields = ['id', 'course', 'student', 'status', 'requested_at', 'reason']

class AnnouncementSerializer(serializers.ModelSerializer):
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Announcement
        fields = ["id", "title", "message", "audience", "created_at", "updated_at", "created_by"]

class AdminCourseQuizStatsSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()
    course_title = serializers.CharField()

    module_count = serializers.IntegerField()
    quiz_count = serializers.IntegerField()
    total_questions = serializers.IntegerField()

    average_score = serializers.FloatField()
    completion_percentage = serializers.FloatField()

class AdminQuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = [
            'id',
            'title',
            'lesson',
            'module',
            'passing_score',
            'max_attempts',
            'is_required_for_module',
            'status',
            'published_at',
        ]

class CertificateSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='student.get_full_name',
        read_only=True
    )
    course_title = serializers.CharField(
        source='course.title',
        read_only=True
    )
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id',
            'student_name',
            'course_title',
            'issued_at',
            'is_revoked',
            'revoked_at',
            'pdf_url'
        ]

    def get_pdf_url(self, obj):
        request = self.context.get('request')
        if obj.pdf_file and request:
            return request.build_absolute_uri(obj.pdf_file.url)
        return None

class CertificateVerificationSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(
        source='student.get_full_name',
        read_only=True
    )
    course_title = serializers.CharField(
        source='course.title',
        read_only=True
    )
    status = serializers.SerializerMethodField()

    class Meta:
        model = Certificate
        fields = [
            'id',
            'verification_code',
            'student_name',
            'course_title',
            'issued_at',
            'status'
        ]

    def get_status(self, obj):
        if obj.revoked_at:
            return "revoked"
        return "valid"

class ResourceSerializer(serializers.ModelSerializer):
    title = serializers.CharField(source='content_item.title', read_only=True)
    type = serializers.CharField(source='content_item.type', read_only=True)
    file = serializers.FileField(source='content_item.file', read_only=True)
    external_url = serializers.URLField(source='content_item.external_url', read_only=True)

    class Meta:
        model = Resource
        fields = [
            'id',
            'title',
            'type',
            'file',
            'external_url',
            'visibility',
            'course',
            'module',
        ]

class CourseOverviewSerializer(serializers.ModelSerializer):
    objectives = serializers.StringRelatedField(many=True)
    tutors = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            'id',
            'title',
            'description',
            'objectives',
            'certificate_enabled',
            'certificate_request_message',
            'tutors',
        ]

    def get_tutors(self, obj):
        tutors = obj.tutor_assignments.filter(is_active=True)
        return [
            {
                'id': tc.tutor.id,
                'name': tc.tutor.get_full_name(),
                'email': tc.tutor.email
            }
            for tc in tutors
        ]


class SupportTicketSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'user',
            'subject',
            'message',
            'priority',
            'status',
            'created_at'
        ]
        read_only_fields = ['user', 'priority', 'status', 'created_at']