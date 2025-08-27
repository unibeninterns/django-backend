from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient, APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from users.models import CustomUser

from module.serializers import *
from datetime import timedelta

from core.common.utils.access_control import (
    can_access_module, can_access_lesson, _is_module_complete, _is_lesson_complete,
    _is_quiz_passed, _is_project_complete, _has_attended_session
)
from progresse.models import ContentProgress, LessonProgress, QuizProgress, ProjectProgress
from assessments.models import SessionAttendance
from core.common.utils.progress_states import ContentState

# Mock user
User = get_user_model()


class ModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="student@test.com", first_name="Test", last_name="User", password="testpass123", role="student"
        )
        self.admin = CustomUser.objects.create_superuser(
            email="admin@test.com", first_name="Admin", last_name="Admin", password="adminpass123",
        )
        self.course = Course.objects.create(
            title="Test Course", description="Test Description", duration_weeks=12
        )

    def test_course_creation(self):
        self.assertEqual(self.course.title, "Test Course")

    def test_module_creation(self):
        module = Module.objects.create(
            course=self.course, order=1, title="Module 1", week_number=1
        )
        self.assertEqual(module.title, "Module 1")
        with self.assertRaises(ValidationError):
            Module.objects.create(course=self.course, order=1, title="Duplicate", week_number=13)


class SerializerTests(TestCase):
    def setUp(self):
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.content = ContentItem.objects.create(lesson=self.lesson, type="video", title="Video 1")
        self.quiz = Quiz.objects.create(module=self.module, title="Quiz 1", passing_score=70.0)

    def test_course_serializer(self):
        serializer = CourseSerializer(self.course)
        data = serializer.data
        self.assertEqual(data['title'], "Test Course")

    def test_module_serializer(self):
        serializer = ModuleSerializer(self.module)
        data = serializer.data
        self.assertEqual(data['title'], "Module 1")
        self.assertIn('previous_module_id', data)
        self.assertIn('next_module_id', data)

    def test_lesson_serializer(self):
        serializer = LessonSerializer(self.lesson)
        data = serializer.data
        self.assertEqual(data['title'], "Lesson 1")
        self.assertIn('previous_lesson_id', data)
        self.assertIn('next_lesson_id', data)

    def test_quiz_serializer(self):
        serializer = QuizSerializer(self.quiz)
        data = serializer.data
        self.assertEqual(data['title'], "Quiz 1")
        self.assertIn('current_state', data)
        self.assertIn('attempts', data)
        self.assertIn('is_passed', data)


class ViewSetTests(APITestCase):
    def setUp(self):
        self.client: APIClient = APIClient()
        self.student = CustomUser.objects.create_user(
            email="student@test.com", first_name="Test", last_name="User", password="testpass123", role="student"
        )
        self.admin = CustomUser.objects.create_superuser(
            email="admin@test.com", first_name="Admin", last_name="Admin", password="adminpass123",
        )
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.content = ContentItem.objects.create(lesson=self.lesson, type="video", title="Video 1")
        self.quiz = Quiz.objects.create(module=self.module, title="Quiz 1", passing_score=70.0)
        self.project = CapstoneProject.objects.create(student=self.student, title="Project 1", module=self.module)
        # Mock progress for access
        ContentProgress.objects.create(student=self.student, content_item=self.content, state=ContentState.AVAILABLE.value)
        LessonProgress.objects.create(student=self.student, lesson=self.lesson, state=ContentState.AVAILABLE.value)
        QuizProgress.objects.create(student=self.student, quiz=self.quiz, state=ContentState.AVAILABLE.value)
        ProjectProgress.objects.create(student=self.student, project=self.project, state=ContentState.AVAILABLE.value)
        SessionAttendance.objects.create(student=self.student, session=LiveSession.objects.create(
            module=self.module, title="Session 1", meeting_url="http://example.com", scheduled_time=timezone.now()
        ), was_present=True)

    def test_course_viewset_admin_create(self):
        self.client.force_authenticate(self.admin)  # Now valid with APIClient
        data = {"title": "New Course", "description": "New Desc", "duration_weeks": 12}
        response = self.client.post(reverse('course-list'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_module_viewset_student_retrieve(self):
        self.client.force_authenticate(self.student)
        response = self.client.get(reverse('module-detail', args=[self.module.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "Module 1")

    def test_lesson_viewset_admin_update(self):
        self.client.force_authenticate(self.admin)
        data = {"title": "Updated Lesson"}
        response = self.client.patch(reverse('lesson-detail', args=[self.lesson.id]), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, "Updated Lesson")

    def test_quiz_viewset_start_quiz(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse('quiz-start-quiz', args=[self.quiz.id]), format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('current_state', response.data)
        self.assertEqual(response.data['current_state'], ContentState.IN_PROGRESS.value)

    def test_quiz_viewset_complete_quiz(self):
        self.client.force_authenticate(self.student)
        response = self.client.post(reverse('quiz-complete-quiz', args=[self.quiz.id]), {"score": 80}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('is_passed', response.data)
        self.assertTrue(response.data['is_passed'])


class AccessControlTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="student@test.com", first_name="Test", last_name="User", password="testpass123", role="student"
        )
        self.admin = CustomUser.objects.create_superuser(
            email="admin@test.com", first_name="Admin", last_name="Admin", password="adminpass123",
        )
        self.course = Course.objects.create(title="Test Course")
        self.module = Module.objects.create(course=self.course, order=1, title="Module 1", week_number=1)
        self.lesson = Lesson.objects.create(module=self.module, title="Lesson 1", order=1)
        self.quiz = Quiz.objects.create(module=self.module, title="Quiz 1", passing_score=70.0)
        self.project = CapstoneProject.objects.create(student=self.user, title="Project 1", module=self.module)
        self.session = LiveSession.objects.create(
            module=self.module, title="Session 1", meeting_url="http://example.com",
            scheduled_time=timezone.now(), duration = timedelta(hours=1)
        )
        Payment.objects.create(user=self.user, amount=99.99, payment_option="Card", transaction_id="TX123", status="completed")
        LessonProgress.objects.create(student=self.user, lesson=self.lesson, state=ContentState.COMPLETED.value)
        QuizProgress.objects.create(student=self.user, quiz=self.quiz, state=ContentState.COMPLETED.value, completion_data={"score": 80})
        ProjectProgress.objects.create(student=self.user, project=self.project, state=ContentState.COMPLETED.value)
        SessionAttendance.objects.create(student=self.user, session=self.session, was_present=True)

    def test_can_access_module(self):
        can_access, reason = can_access_module(self.user, self.module)
        self.assertTrue(can_access)
        self.assertEqual(reason, "")

    def test_can_access_lesson(self):
        can_access, reason = can_access_lesson(self.user, self.lesson)
        self.assertTrue(can_access)
        self.assertEqual(reason, "")

    def test_is_module_complete(self):
        self.assertTrue(_is_module_complete(self.user, self.module))

    def test_is_lesson_complete(self):
        self.assertTrue(_is_lesson_complete(self.user, self.lesson))

    def test_is_quiz_passed(self):
        self.assertTrue(_is_quiz_passed(self.user, self.quiz))

    def test_is_project_complete(self):
        self.assertTrue(_is_project_complete(self.user, self.project))

    def test_has_attended_session(self):
        self.assertTrue(_has_attended_session(self.user, self.session))