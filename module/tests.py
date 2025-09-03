from django.core.exceptions import ValidationError
import datetime
from django.test import TestCase, RequestFactory
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from django.utils import timezone
from unittest.mock import patch, Mock
from .models import (
    Course, Module, Lesson, LessonNote, ContentItem, Quiz, Question,
    QuizSubmission, Answer, Payment, CapstoneProject, LiveSession,
    UserSettings, ActivityLog, CustomUser
)
from progresse.models import QuizProgress
from core.common.utils.progress_states import ContentState
from core.common.utils import progress
from .views import ModuleViewSet
from allauth.account.signals import user_signed_up
from django.db import IntegrityError


class ViewTestBase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = RequestFactory()
        self.admin = CustomUser.objects.create_user(
            email="admin@test.com",
            password="adminpass",
            role="admin",
            is_staff=True,
            is_superuser=True
        )
        self.student = CustomUser.objects.create_user(email="student@test.com", password="studentpass", role="student")
        self.course = Course.objects.create(title="Test Course", duration_weeks=12)
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.content = ContentItem.objects.create(
            lesson=self.lesson,  # link to the Lesson
            type='video',  # matches your TYPE_CHOICES
            title="Test Content",
            # optionally, add other fields if needed:
            # file=some_file,
            # external_url="https://example.com",
            # duration=datetime.timedelta(minutes=10),
            # content="Some text content"
        )
        self.quiz = Quiz.objects.create(module=self.module, title="Test Quiz", passing_score=70.0, max_attempts=2)
        self.payment = Payment.objects.create(
            user=self.student,
            amount=100.00,  # Base amount
            payment_option="card",
            transaction_id="TX123",
            status="Completed"
        )
        self.project = CapstoneProject.objects.create(student=self.student, title="Test Project", module=self.module)
        self.session = LiveSession.objects.create(module=self.module, title="Test Session", meeting_url="https://zoom.us", scheduled_time=timezone.now(), duration=timezone.timedelta(minutes=60))
        self.settings = UserSettings.objects.create(user=self.student, notifications_enabled=True, theme="dark")
        self.activity = ActivityLog.objects.create(student=self.student, activity_type="completed_module")
        older_activity = ActivityLog.objects.create(
            student=self.student, activity_type="downloaded_item",
            timestamp=timezone.now() - datetime.timedelta(days=1)
        )

    def authenticate_as(self, user):
        self.client.force_authenticate(user=user)

class QuizViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()


        self.quiz = Quiz.objects.create(module=self.module, title="Test Quiz", passing_score=70.0, max_attempts=3)

        # Define URLs using the pk from the created object.
        self.url = reverse('quiz-list')
        self.start_url = reverse('quiz-start-quiz', kwargs={'pk': self.quiz.pk})
        self.complete_url = reverse('quiz-complete-quiz', kwargs={'pk': self.quiz.pk})

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

    @patch("progresse.models.QuizProgress._is_valid_transition", return_value=True)
    def test_complete_quiz_pass_then_fail_scenario(self, mock_transition):
        """Completing a quiz and then attempting a subsequent completion."""

        # 1. Start the quiz
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_state'], ContentState.IN_PROGRESS.value)
        self.assertEqual(response.data['attempts'], 1)

        # 2. First submission → PASS
        resp1 = self.client.post(self.complete_url, {"score": 80.0}, format='json')
        print(f"resp1 status is :{resp1.status_code}")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        print(f"resp1 is_passed is :{resp1.data['is_passed']}")
        self.assertTrue(resp1.data['is_passed'])
        self.assertEqual(resp1.data['current_state'], ContentState.COMPLETED.value)
        self.assertEqual(resp1.data['attempts'], 1)

        # 3. Subsequent attempt should be forbidden
        resp2 = self.client.post(self.complete_url, {"score": 60.0}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_403_FORBIDDEN)

        # Verify patch applied
        self.assertTrue(mock_transition.called)

    @patch("progresse.models.QuizProgress._is_valid_transition", return_value=True)
    def test_complete_quiz_fail_scenario(self, mock_transition):
        """Test completing a quiz with a score that results in a failed state."""

        # 1. Start the quiz
        response = self.client.post(self.start_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_state'], ContentState.IN_PROGRESS.value)
        self.assertEqual(response.data['attempts'], 1)

        # 2. First submission → FAIL
        resp1 = self.client.post(self.complete_url, {"score": 60.0}, format='json')
        print(f"First Response data: {resp1.data}")
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertFalse(resp1.data['is_passed'])
        self.assertEqual(resp1.data['current_state'], ContentState.FAILED.value)
        self.assertEqual(resp1.data['attempts'], 1)

        # 3. Retry: start again
        response = self.client.post(self.start_url)
        print(f" retry response data is {response.data}")
        print(f" retry response status is {response.status_code}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_state'], ContentState.IN_PROGRESS.value)
        print(f"response attempts is {response.data['attempts']}")
        self.assertEqual(response.data['attempts'], 2)

        # 4. Second submission → PASS
        resp2 = self.client.post(self.complete_url, {"score": 80.0}, format='json')
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertTrue(resp2.data['is_passed'])
        self.assertEqual(resp2.data['current_state'], ContentState.COMPLETED.value)
        self.assertEqual(resp2.data['attempts'], 2)

        # Verify patch applied
        self.assertTrue(mock_transition.called)

class CourseModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(
            title="Test Course",
            description="A test course description",
            duration_weeks=12
        )

    def test_course_creation(self):
        """Test that a Course can be created successfully."""
        self.assertEqual(self.course.title, "Test Course")
        self.assertEqual(self.course.duration_weeks, 12)
        self.assertIsNone(self.course.start_date)
        self.assertIsNone(self.course.end_date)

    def test_course_string_representation(self):
        """Test the string representation of a Course."""
        self.assertEqual(str(self.course), "Test Course")

class ModuleModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(
            course=self.course,
            order=1,
            title="Module 1",
            week_number=1,
            description="Module description"
        )

    def test_module_creation(self):
        """Test that a Module can be created successfully."""
        self.assertEqual(self.module.title, "Module 1")
        self.assertEqual(self.module.week_number, 1)
        self.assertEqual(self.module.order, 1)

    def test_get_previous_module(self):
        """Test get_previous_module returns None for the first module."""
        prev_module = self.module.get_previous_module()
        self.assertIsNone(prev_module)

    def test_get_next_module(self):
        """Test get_next_module returns None when no next module exists."""
        next_module = self.module.get_next_module()
        self.assertIsNone(next_module)

    def test_module_constraints(self):
        """Test unique constraint on course and order."""
        with self.assertRaises(IntegrityError):
            Module.objects.create(course=self.course, order=1, title="Duplicate", week_number=2)

    def test_module_string_representation(self):
        """Test the string representation of a Module."""
        self.assertEqual(str(self.module), "Module 1 (Course: Test Course, Order: 1, Week 1)")

class LessonModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(
            module=self.module,
            title="Lesson 1",
            order=1,
            has_video=True,
            video_duration_minutes=30,
            minimum_watch_percentage=80.0
        )

    def test_lesson_creation(self):
        """Test that a Lesson can be created successfully."""
        self.assertEqual(self.lesson.title, "Lesson 1")
        self.assertTrue(self.lesson.has_video)
        self.assertEqual(self.lesson.video_duration_minutes, 30)

    def test_get_previous_lesson(self):
        """Test get_previous_lesson returns None for the first lesson."""
        prev_lesson = self.lesson.get_previous_lesson()
        self.assertIsNone(prev_lesson)

    def test_get_next_lesson(self):
        """Test get_next_lesson returns None when no next lesson exists."""
        next_lesson = self.lesson.get_next_lesson()
        self.assertIsNone(next_lesson)

    def test_lesson_constraints(self):
        """Test unique constraint on module and order."""
        with self.assertRaises(IntegrityError):
            Lesson.objects.create(module=self.module, title="Duplicate", order=1)

    def test_lesson_string_representation(self):
        """Test the string representation of a Lesson."""
        self.assertEqual(str(self.lesson), "Week: 1| (Title Lesson 1)")

class LessonNoteModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.note = LessonNote.objects.create(
            student=self.user,
            lesson=self.lesson,
            note="Test note"
        )

    def test_lesson_note_creation(self):
        """Test that a LessonNote can be created successfully."""
        self.assertEqual(self.note.student.email, "user@test.com")
        self.assertEqual(self.note.lesson.title, "Lesson 1")
        self.assertTrue(self.note.note, "Test note")

    def test_lesson_note_string_representation(self):
        """Test the string representation of a LessonNote."""
        expected = f"{self.user.email} - {self.lesson.title} - {self.note.created_at}"
        self.assertEqual(str(self.note), expected)

class ContentItemModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.content = ContentItem.objects.create(
            lesson=self.lesson,
            type="video",
            title="Test Video"
        )

    def test_content_item_creation(self):
        """Test that a ContentItem can be created successfully."""
        self.assertEqual(self.content.type, "video")
        self.assertEqual(self.content.title, "Test Video")

    def test_content_item_string_representation(self):
        """Test the string representation of a ContentItem."""
        self.assertEqual(str(self.content), "Test Video")

class QuizModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.quiz_module = Quiz.objects.create(
            module=self.module,
            title="Module Quiz",
            passing_score=70.0,
            max_attempts=2
        )
        self.quiz_lesson = Quiz.objects.create(
            lesson=self.lesson,
            title="Lesson Quiz",
            passing_score=70.0,
            max_attempts=2
        )

    def test_quiz_creation(self):
        """Test that a Quiz can be created successfully."""
        self.assertEqual(self.quiz_module.title, "Module Quiz")
        self.assertEqual(self.quiz_lesson.title, "Lesson Quiz")

    def test_quiz_validation(self):
        """Test that a Quiz must be tied to either lesson or module, not both."""
        with self.assertRaises(ValidationError):
            Quiz.objects.create(
                module=self.module,
                lesson=self.lesson,
                title="Invalid Quiz",
                passing_score=70.0,
                max_attempts=2
            )

    def test_quiz_score_bounds(self):
        """Test passing_score bounds validation."""
        with self.assertRaises(ValidationError):
            Quiz.objects.create(
                module=self.module,
                title="Invalid Score Quiz",
                passing_score=101.0,
                max_attempts=2
            )

    def test_quiz_attempts_bounds(self):
        """Test max_attempts bounds validation."""
        with self.assertRaises(ValidationError):
            Quiz.objects.create(
                module=self.module,
                title="Invalid Attempts Quiz",
                passing_score=70.0,
                max_attempts=4
            )

    def test_quiz_string_representation(self):
        """Test the string representation of a Quiz."""
        expected_module = f"Quiz: Module Quiz for Lesson N/A | Module 1"
        expected_lesson = f"Quiz: Lesson Quiz for Lesson 1 | Module N/A"
        self.assertEqual(str(self.quiz_module), expected_module)
        self.assertEqual(str(self.quiz_lesson), expected_lesson)

class CapstoneProjectModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.project = CapstoneProject.objects.create(
            student=self.user,
            title="Test Project",
            description="Test description",
            module=self.module
        )

    def test_capstone_project_creation(self):
        """Test that a CapstoneProject can be created successfully."""
        self.assertEqual(self.project.title, "Test Project")
        self.assertEqual(self.project.grade, "N/A")
        self.assertEqual(self.project.grade2, "N/A")

    def test_capstone_project_default_grade_states(self):
        """Test default grade states."""
        self.assertEqual(self.project.grade, "N/A")
        self.assertEqual(self.project.grade2, "N/A")

    def test_capstone_project_string_representation(self):
        """Test the string representation of a CapstoneProject."""
        expected = f"Project done by {self.user.username} - {self.user.email}"
        self.assertEqual(str(self.project), expected)

class ActivityLogModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.activity = ActivityLog.objects.create(
            student=self.user,
            activity_type="completed_module",
            content_id=1,
            content_type="module"
        )

    def test_activity_log_creation(self):
        """Test that an ActivityLog can be created successfully."""
        self.assertEqual(self.activity.student.email, "user@test.com")
        self.assertEqual(self.activity.activity_type, "completed_module")

    def test_activity_log_ordering(self):
        """Test that ActivityLog is ordered by timestamp descending."""
        older_activity = ActivityLog.objects.create(
            student=self.user,
            activity_type="downloaded_item",
            timestamp=timezone.now() - datetime.timedelta(days=1)
        )
        logs = ActivityLog.objects.all()
        # The latest activity should be first
        self.assertGreater(logs[0].timestamp, logs[1].timestamp)

    def test_activity_log_string_representation(self):
        """Test the string representation of an ActivityLog."""
        expected = f"{self.user.email} - completed_module at {self.activity.timestamp}"
        self.assertEqual(str(self.activity), expected)

class PaymentModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.payment = Payment.objects.create(
            user=self.user,
            amount=100.00,
            payment_option="Credit Card",
            transaction_id="TX123456",
            status="completed"
        )

    def test_payment_creation(self):
        """Test that a Payment can be created successfully."""
        self.assertEqual(self.payment.amount, 100.00)
        self.assertEqual(self.payment.status, "completed")

    def test_payment_string_representation(self):
        """Test the string representation of a Payment."""
        expected = f"{self.user.username} - Credit Card"
        self.assertEqual(str(self.payment), expected)

class LiveSessionModelTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.session = LiveSession.objects.create(
            module=self.module,
            title="Test Session",
            meeting_url="https://zoom.us/test",
            scheduled_time=timezone.now(),
            duration=datetime.timedelta(minutes=60)
        )

    def test_live_session_creation(self):
        """Test that a LiveSession can be created successfully."""
        self.assertEqual(self.session.title, "Test Session")
        self.assertEqual(self.session.minimum_attendance_minutes, 0)

    def test_live_session_string_representation(self):
        """Test the string representation of a LiveSession."""
        expected = f"Live session held in  Week: 1 for Module: 1"
        self.assertEqual(str(self.session), expected)

class UserSettingsModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(email="user@test.com", password="testpass123")
        self.settings = UserSettings.objects.create(
            user=self.user,
            notifications_enabled=True,
            theme="dark",
            email_alerts=False
        )

    def test_user_settings_creation(self):
        """Test that UserSettings can be created successfully."""
        self.assertEqual(self.settings.user.email, "user@test.com")
        self.assertEqual(self.settings.theme, "dark")

    def test_user_settings_string_representation(self):
        """Test the string representation of UserSettings."""
        expected = f"Settings for {self.user.email}"
        self.assertEqual(str(self.settings), expected)

class ActivityLogViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('activitylog-list')
        for i in range(6):  # Create 6 logs to test limit of 5
            ActivityLog.objects.create(student=self.student, activity_type="completed_module")

    def test_returns_latest_5_logs(self):
        """Test returns latest 5 logs for student."""
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        print(f"Response status: {response.status_code}, data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 5)

class UserSettingsViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('usersettings-list')

    def test_student_can_edit_own_settings(self):
        """Test student can see/edit only their settings."""
        self.authenticate_as(self.student)
        data = {"theme": "light"}
        response = self.client.patch(reverse('usersettings-detail', kwargs={'pk': self.settings.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['theme'], "light")

    def test_admin_cannot_edit_other_settings(self):
        """Test admin cannot edit another student's settings."""
        self.authenticate_as(self.admin)
        other_student = CustomUser.objects.create_user(email="other@test.com", password="otherpass", role="student")
        other_settings = UserSettings.objects.create(user=other_student, notifications_enabled=True)
        data = {"theme": "light"}
        response = self.client.patch(reverse('usersettings-detail', kwargs={'pk': other_settings.id}), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

class LiveSessionViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('livesession-list')

    @patch('module.views.get_content_state')
    def test_student_sees_active_sessions(self, mock_get_content_state):
        """Test student sees only currently active, accessible sessions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class CapstoneProjectViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('capstoneproject-list')

    @patch('core.common.utils.progress.get_content_state')
    def test_student_sees_own_projects(self, mock_get_content_state):
        """Test students see only their projects."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('core.common.utils.progress.get_content_state')
    def test_context_includes_current_state(self, mock_get_content_state):
        """Test context includes current_state."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)
        url = reverse('capstoneproject-detail', kwargs={'pk': self.project.id})
        response = self.client.get(url)
        print(f"Response status: {response.status_code}, data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_state', response.data)

class AnswerViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.submission = QuizSubmission.objects.create(student=self.student, quiz=self.quiz, score=80.0)
        self.question = Question.objects.create(quiz=self.quiz, text="Test Question", type="multiple_choice")
        self.answer = Answer.objects.create(submission=self.submission, question=self.question, answer_text="Test Answer")
        self.url = reverse('answer-list')

    def test_student_sees_own_data(self):
        """Test students see only their answers."""
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('core.common.utils.progress.get_content_state')
    def test_admin_sees_all(self, mock_get_content_state):
        """Test admins see all questions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class QuizSubmissionViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.submission = QuizSubmission.objects.create(student=self.student, quiz=self.quiz, score=80.0)
        self.url = reverse('quizsubmission-list')

    def test_student_sees_own_data(self):
        """Test students see only their submissions."""
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    @patch('core.common.utils.progress.get_content_state')
    def test_admin_sees_all(self, mock_get_content_state):
        """Test admins see all questions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class QuestionViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.test_quiz = Quiz.objects.create(module=self.module, title="Test Quiz", passing_score=70.0, max_attempts=2)
        self.question = Question.objects.create(quiz=self.test_quiz, text="Test Question", type="multiple_choice")
        self.url = reverse('question-list')

    @patch('module.views.get_content_state')
    def test_student_sees_own_data(self, mock_get_content_state):
        """Test students see only their quiz-related questions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS

        # Add a print statement to confirm the mock is working as expected
        print(f"Mocked get_content_state returns: {mock_get_content_state(None, None, None)}")

        self.authenticate_as(self.student)
        response = self.client.get(self.url)

        # Add a print statement to see the response data
        print(f"Response status: {response.status_code}, data: {response.data}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


    @patch('core.common.utils.progress.get_content_state')
    def test_admin_sees_all(self, mock_get_content_state):
        """Test admins see all questions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.admin)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

class ContentItemViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('contentitem-list')

    def test_serializer_context_progress(self):
        self.authenticate_as(self.student)

        # create a content item for this test
        self.content = ContentItem.objects.create(
            lesson=self.lesson,
            type='video',
            title="Test Content",
        )

        url = reverse('contentitem-detail', kwargs={'pk': self.content.id})

        # patch the direct import in your view …
        p1 = patch('module.views.get_content_state',
                   return_value=ContentState.AVAILABLE)

        # … and patch the progress.get_content_state used in your permission class
        p2 = patch('module.permissions.progress.get_content_state',
                   return_value=ContentState.AVAILABLE)

        with p1, p2:
            response = self.client.get(url)


        print(f"Response status: {response.status_code}, Data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_state', response.data)

    def test_student_sees_accessible_content(self):
        """Test student only sees accessible content."""
        # patch the function *inside* your view module
        with patch('module.views.get_content_state',
                   return_value=ContentState.IN_PROGRESS):
            self.authenticate_as(self.student)
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # now the list should contain 1 item
        self.assertEqual(len(response.data), 1)

class AuthenticationAndPermissionsTests(ViewTestBase):

    def test_is_admin_user_permission(self):
        """Test that only admins can create a Course."""
        self.authenticate_as(self.student)
        data = {
            "title": "Admin Created Course",
            "description": "Test description",  # required
            "duration_weeks": 12,
            "instructor": self.admin.id  # if instructor must be provided
        }
        url = reverse('course-list')
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate_as(self.admin)
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_is_student_permission(self):
        """Test that students can access Module list but not create."""
        self.authenticate_as(self.student)
        url = reverse('module-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = {"course": self.course.id, "order": 2, "title": "New Module", "week_number": 2}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_is_owner_or_admin_permission(self):
        """Test that only owner or admin can view their Payment."""
        self.authenticate_as(self.student)
        url = reverse('payment-detail', kwargs={'pk': self.payment.id})
        print(f"URL: {url}")  # Should be /api/module/payments/1/
        print(f"Payment PK: {self.payment.id}, User: {self.student.email}")
        response = self.client.get(url)
        print(f"Response Status: {response.status_code}, Data: {response.data}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Owner should get 200

        # Test non-owner access
        other_student = CustomUser.objects.create_user(email="other@test.com", password="otherpass", role="student")
        self.authenticate_as(other_student)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Test admin access
        self.authenticate_as(self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class CourseViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('course-list')

    @patch('core.common.utils.progress.get_content_state')
    def test_list_open(self, mock_get_content_state):
        """Test that Course list is open to all."""
        mock_get_content_state.return_value = ContentState.COMPLETED
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('core.common.utils.progress.get_content_state')
    def test_create_requires_admin(self, mock_get_content_state):
        """Test that only admin can create a Course."""
        mock_get_content_state.return_value = ContentState.COMPLETED
        self.authenticate_as(self.student)
        data = {"title": "Student Course", "description": "Test desc", "duration_weeks": 12}
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.authenticate_as(self.admin)
        response = self.client.post(self.url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.common.utils.progress.get_content_state')
    def test_get_weeks_progress(self, mock_get_content_state):
        """Test get_weeks_progress with mocked content state."""
        mock_get_content_state.return_value = ContentState.COMPLETED
        self.authenticate_as(self.student)
        url = reverse('course-get-weeks-progress', kwargs={'pk': self.course.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('weeks_completed', response.data)

class ModuleViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('module-list')

    @patch('module.views.get_content_state')
    def test_student_sees_accessible_modules(self, mock_get_content_state):
        """Test student only sees accessible modules."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)  # Only accessible module

    @patch('module.views.progress.get_content_state')
    def test_serializer_context_prev_next(self, mock_get_content_state):
        mock_get_content_state.return_value = ContentState.IN_PROGRESS

        module1 = self.module
        module2 = Module.objects.create(course=self.course, order=2, title="Module 2", week_number=2)
        module2.save()
        module2.refresh_from_db()
        self.assertEqual(module2.order, 2)
        module3 = Module.objects.create(course=self.course, order=3, title="Module 3", week_number=3)
        module3.save()
        module3.refresh_from_db()
        self.assertEqual(module3.order, 3)

        self.authenticate_as(self.student)

        # Override get_queryset for the entire test
        original_get_queryset = ModuleViewSet.get_queryset
        ModuleViewSet.get_queryset = lambda self: Module.objects.all()

        try:
            url = reverse('module-detail', kwargs={'pk': module1.id})
            print(f"Generated URL: {url}")
            response = self.client.get(url)
            print(f"Status Code: {response.status_code}")
            print(f"Module Exists: {Module.objects.filter(id=module1.id).exists()}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            self.assertIn('previous_module_id', response.data)
            self.assertIn('next_module_id', response.data)
            self.assertIsNone(response.data['previous_module_id'])
            self.assertEqual(response.data['next_module_id'], module2.id)

            url2 = reverse('module-detail', kwargs={'pk': module2.id})
            print(f"Generated URL 2: {url2}")
            response2 = self.client.get(url2)
            print(f"Status Code 2: {response2.status_code}")
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            self.assertEqual(response2.data['previous_module_id'], module1.id)
            self.assertEqual(response2.data['next_module_id'], module3.id)

            url3 = reverse('module-detail', kwargs={'pk': module3.id})
            print(f"Generated URL 3: {url3}")
            response3 = self.client.get(url3)
            print(f"Status Code 3: {response3.status_code}")
            self.assertEqual(response3.status_code, status.HTTP_200_OK)
            self.assertEqual(response3.data['previous_module_id'], module2.id)
            self.assertIsNone(response3.data['next_module_id'])
        finally:
            ModuleViewSet.get_queryset = original_get_queryset

    @patch('module.views.get_content_state')
    def test_list_returns_modules_completed(self, mock_get_content_state):
        """Test list returns modules_completed count for students."""
        mock_get_content_state.return_value = ContentState.COMPLETED
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('modules_completed', response.data)
        self.assertEqual(response.data['modules_completed'], 1)

class LessonViewSetTests(ViewTestBase):
    def setUp(self):
        super().setUp()
        self.url = reverse('lesson-list')

    @patch('core.common.utils.progress.get_content_state')
    def test_access_control(self, mock_get_content_state):
        """Test access control similar to module."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.authenticate_as(self.admin)
        response = self.client.post(self.url, {
            "module": self.module.id,
            "title": "New Lesson",
            "order": 2,  # must not conflict with existing lesson order
            "has_video": False,
            "video_duration_minutes": 0,
            "minimum_watch_percentage": 80.0
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('core.common.utils.progress.get_content_state')
    def test_add_note(self, mock_get_content_state):
        lesson = Lesson.objects.create(module=self.module, title="Debug Lesson", order=99)
        """Test add_note POST, PUT, DELETE actions."""
        mock_get_content_state.return_value = ContentState.IN_PROGRESS
        self.authenticate_as(self.student)

        url_post = reverse('lesson-add-note', kwargs={'pk': self.lesson.id})
        print(f"[DEBUG] Test hitting URL: {url_post}")
        url_put = reverse('lesson-update-note', kwargs={'pk': self.lesson.id})
        url_delete = reverse('lesson-delete-note', kwargs={'pk': self.lesson.id})

        # POST
        response = self.client.post(url_post, {"note": "Test note"}, format='json')
        print(f"[DEBUG] Response status: {response.status_code}")
        print(f"[DEBUG] Response data: {getattr(response, 'data', response.content)}")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        note_id = response.data['id']

        # PUT
        response = self.client.put(url_put, {"note_id": note_id, "note": "Updated note"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # DELETE
        response = self.client.delete(url_delete, {"note_id": note_id}, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

