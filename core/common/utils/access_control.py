from typing import Tuple
from progresse.models import *
from core.common.utils.progress_states import ContentState


def can_access_module(user, module) -> Tuple[bool, str]:
    """Check if user can access a module based on sequential order."""

    # Check payment first
    if not _has_paid_for_course(user, module.course):
        return False, "Course payment required"

    # Check if previous module is complete
    previous_module = module.get_previous_module()
    if previous_module:
        if not _is_module_complete(user, previous_module):
            return False, f"Complete '{previous_module.title}' first"

    return True, ""


def can_access_lesson(user, lesson) -> Tuple[bool, str]:
    """Check if user can access a lesson."""

    # Check module access first
    can_access, reason = can_access_module(user, lesson.module)
    if not can_access:
        return can_access, reason

    # Check if previous lesson is complete
    previous_lesson = lesson.get_previous_lesson()
    if previous_lesson:
        if not _is_lesson_complete(user, previous_lesson):
            return False, f"Complete previous lesson '{previous_lesson.title}' first"

    return True, ""


def _has_paid_for_course(user, course) -> bool:
    """Check if user has paid for course access."""
    from payments.models import Payment

    return Payment.objects.filter(
        user=user,
        course=course,
        status='completed'
    ).exists()


def _is_module_complete(user, module) -> bool:
    """Check if user has completed all module requirements."""

    # Check lessons
    if module.requires_all_lessons:
        for lesson in module.lessons.all():
            if not _is_lesson_complete(user, lesson):
                return False

    # Check quizzes
    if module.requires_all_quizzes:
        for quiz in module.quizzes.filter(is_required_for_module=True):
            if not _is_quiz_passed(user, quiz):
                return False

    # Check project submission
    if module.requires_project_submission:
        for project in module.projects.all():
            if not _is_project_complete(user, project):
                return False

    # Check live session attendance
    if module.requires_live_session_attendance:
        for session in module.live_sessions.filter(is_mandatory=True):
            if not _has_attended_session(user, session):
                return False

    return True


def _is_lesson_complete(user, lesson) -> bool:
    try:
        progress = LessonProgress.objects.get(
            student=user,
            lesson=lesson
        )
        if progress.state != ContentState.COMPLETED.value:
            return False
        if lesson.has_video:
            watch_percentage = progress.video_watch_percentage
            if watch_percentage < lesson.minimum_watch_percentage:
                return False
        return True
    except LessonProgress.DoesNotExist:
        return False


def _is_quiz_passed(user, quiz) -> bool:
    try:
        progress = QuizProgress.objects.get(
            student=user,
            quiz=quiz
        )
        if progress.state != ContentState.COMPLETED.value:
            return False
        score = progress.completion_data.get('score', 0)
        return score >= quiz.passing_score and progress.is_passed
    except QuizProgress.DoesNotExist:
        return False


def _is_project_complete(user, project) -> bool:
    """Check if project requirements are met."""
    try:
        progress = ProjectProgress.objects.get(
            student=user,
            project=project
        )

        if progress.state != ContentState.COMPLETED.value:
            return False
        if project.requires_submission and not progress.is_submitted:
            return False
        if project.requires_instructor_approval and not progress.is_instructor_approved:
            return False
        return True

    except ProjectProgress.DoesNotExist:
        return False


def _has_attended_session(user, session) -> bool:
    from assessments.models import SessionAttendance
    try:
        attendance = SessionAttendance.objects.get(
            student=user,
            session=session
        )
        if not attendance.was_present:
            return False
        if session.minimum_attendance_minutes > 0:
            attended_minutes = attendance.attendance_duration_minutes or 0
            if attended_minutes < session.minimum_attendance_minutes:
                return False
        return True
    except SessionAttendance.DoesNotExist:
        return False