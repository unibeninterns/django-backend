


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


print(f"Response status: {response.status_code}, data: {response.data}")


@action(detail=True, methods=['post'], url_path='complete')
    def complete_content(self, request, pk=None):
        user = request.user
        content_item = self.get_object()

        # 1. Get or Create the progress record for the item
        progress, _ = ContentProgress.objects.get_or_create(
            student=user,
            content_item=content_item
        )

        # 2. Transition to COMPLETED
        try:
            progress.transition_to(ContentState.COMPLETED)
        except ValueError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Update the Lesson Progress
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            student=user,
            lesson=content_item.lesson
        )

        # Run the check we just added to the model
        lesson_was_completed = lesson_progress.check_and_update_status()

        # 4. Optional: If lesson is done, check if Module is done
        module_was_completed = False
        if lesson_was_completed:
            module_progress, _ = ModuleCompletion.objects.get_or_create(
                student=user,
                module=content_item.lesson.module
            )
            # You can implement a similar check_and_update_status on ModuleCompletion!
            module_was_completed = module_progress.check_and_update_status()

        return Response({
            "item_status": progress.state,
            "lesson_completed": lesson_was_completed,
            "module_completed": module_was_completed
        })