from typing import Optional, List
from django.contrib.auth.models import User
from progresse.models import *
from core.common.utils.progress_states import ContentState
from core.common.utils.access_control import can_access_module, can_access_lesson
from django.core.exceptions import ObjectDoesNotExist


def get_lesson_state(user: User, lesson_id: int) -> ContentState:
    """Get current state of lesson for user."""
    try:
        progress = LessonProgress.objects.get(student=user, lesson_id=lesson_id)
        return progress.get_state_enum()
    except LessonProgress.DoesNotExist:
        # Check if lesson should be available using sequential access control
        from module.models import Lesson
        lesson = Lesson.objects.get(id=lesson_id)
        can_access, _ = can_access_lesson(user, lesson)

        if can_access:
            # Create progresse record in AVAILABLE state
            progress = LessonProgress.objects.create(
                student=user,
                lesson=lesson,
                state=ContentState.AVAILABLE.value
            )
            return ContentState.AVAILABLE

        return ContentState.LOCKED


def get_module_state(user: User, module_id: int) -> ContentState:
    """Get current state of module for user."""
    try:
        progress = ModuleCompletion.objects.get(student=user, module_id=module_id)
        return progress.get_state_enum()
    except ModuleCompletion.DoesNotExist:
        # Check if module should be available
        from module.models import Module
        module = Module.objects.get(id=module_id)
        can_access, _ = can_access_module(user, module)

        if can_access:
            # Create progresse record in AVAILABLE state
            progress = ModuleCompletion.objects.create(
                student=user,
                module=module,
                state=ContentState.AVAILABLE.value
            )
            return ContentState.AVAILABLE

        return ContentState.LOCKED


def get_quiz_state(user: User, quiz_id: int) -> ContentState:
    """Get current state of quiz for user."""
    try:
        progress = QuizProgress.objects.get(student=user, quiz_id=quiz_id)
        return progress.get_state_enum()
    except QuizProgress.DoesNotExist:
        # Check if quiz should be available
        from module.models import Quiz
        quiz = Quiz.objects.get(id=quiz_id)

        if quiz.lesson:
            # Lesson-level quiz - check lesson access
            can_access, _ = can_access_lesson(user, quiz.lesson)
        else:
            # Module-level quiz - check module access
            can_access, _ = can_access_module(user, quiz.module)

        if can_access:
            progress = QuizProgress.objects.create(
                student=user,
                quiz=quiz,
                state=ContentState.AVAILABLE.value
            )
            return ContentState.AVAILABLE

        return ContentState.LOCKED


def get_content_item_state(user: User, content_item_id: int) -> ContentState:
    """Get current state of content item for user."""
    try:
        progress = ContentProgress.objects.get(student=user, content_item_id=content_item_id)
        return progress.get_state_enum()
    except ContentProgress.DoesNotExist:
        # Check if content item should be available (based on lesson access)
        from module.models import ContentItem
        content_item = ContentItem.objects.select_related('lesson').get(id=content_item_id)
        can_access, _ = can_access_lesson(user, content_item.lesson)

        if can_access:
            progress = ContentProgress.objects.create(
                student=user,
                content_item=content_item,
                state=ContentState.AVAILABLE.value
            )
            return ContentState.AVAILABLE

        return ContentState.LOCKED


# Content starting functions
def start_lesson(user: User, lesson_id: int) -> ContentState:
    """Start lesson - transition to IN_PROGRESS."""
    current_state = get_lesson_state(user, lesson_id)

    if current_state not in ContentState.startable_states():
        raise ValueError(f"Cannot start lesson from {current_state} state")

    progress = LessonProgress.objects.get(student=user, lesson_id=lesson_id)
    progress.transition_to(ContentState.IN_PROGRESS)

    # Log event
    _log_progress_event(user, 'lesson', lesson_id, 'lesson_started',
                        old_state=current_state.value, new_state=ContentState.IN_PROGRESS.value)

    return ContentState.IN_PROGRESS


def start_quiz(user: User, quiz_id: int) -> ContentState:
    """Start quiz - transition to IN_PROGRESS."""
    current_state = get_quiz_state(user, quiz_id)

    if current_state not in ContentState.startable_states():
        raise ValueError(f"Cannot start quiz from {current_state} state")

    progress = QuizProgress.objects.get(student=user, quiz_id=quiz_id)
    progress.transition_to(ContentState.IN_PROGRESS)

    # Log event
    _log_progress_event(user, 'quiz', quiz_id, 'quiz_started',
                        old_state=current_state.value, new_state=ContentState.IN_PROGRESS.value)

    return ContentState.IN_PROGRESS


# Content completion functions
def complete_lesson(user: User, lesson_id: int, **completion_data) -> dict:
    """Complete lesson and check what gets unlocked."""
    current_state = get_lesson_state(user, lesson_id)

    if current_state not in ContentState.completable_states():
        raise ValueError(f"Cannot complete lesson from {current_state} state")

    progress = LessonProgress.objects.get(student=user, lesson_id=lesson_id)

    # Transition to completed
    progress.transition_to(ContentState.COMPLETED, **completion_data)

    # Check what gets unlocked
    newly_unlocked = _check_unlocked_after_lesson_completion(user, lesson_id)

    # Check if module is now complete
    from module.models import Lesson
    lesson = Lesson.objects.get(id=lesson_id)
    module_completed = _check_and_complete_module(user, lesson.module)

    # Log completion event
    _log_progress_event(user, 'lesson', lesson_id, 'lesson_completed',
                        old_state=current_state.value, new_state=ContentState.COMPLETED.value,
                        metadata={'unlocked': newly_unlocked, 'module_completed': module_completed})

    return {
        'completed_content': {'lesson': lesson_id},
        'newly_unlocked': newly_unlocked,
        'module_completed': module_completed,
        'next_recommended': _get_next_recommended_after_lesson(user, lesson_id)
    }


def complete_quiz(user: User, quiz_id: int, score: float, **completion_data) -> dict:
    """Complete quiz attempt with score."""
    current_state = get_quiz_state(user, quiz_id)

    if current_state not in ContentState.completable_states():
        raise ValueError(f"Cannot complete quiz from {current_state} state")

    from module.models import Quiz
    quiz = Quiz.objects.get(id=quiz_id)
    progress = QuizProgress.objects.get(student=user, quiz_id=quiz_id)

    # Determine if passed or failed
    passed = score >= quiz.passing_score
    new_state = ContentState.COMPLETED if passed else ContentState.FAILED

    # Transition to new state
    progress.transition_to(new_state, score=score, passing_score=quiz.passing_score,
                           attempt_data=completion_data)

    result = {
        'completed_content': {'quiz': quiz_id},
        'score': score,
        'passed': passed,
        'attempts': progress.attempts,
        'newly_unlocked': []
    }

    # Only unlock content if quiz was passed
    if passed:
        newly_unlocked = _check_unlocked_after_quiz_completion(user, quiz_id)
        result['newly_unlocked'] = newly_unlocked

        # Check if module is now complete
        module_completed = _check_and_complete_module(user, quiz.module)
        result['module_completed'] = module_completed

    # Log completion event
    _log_progress_event(user, 'quiz', quiz_id, 'quiz_completed',
                        old_state=current_state.value, new_state=new_state.value,
                        metadata={'score': score, 'passed': passed})

    return result


def complete_module(user: User, module_id: int, **completion_data) -> dict:
    """Mark module as complete and unlock next module."""
    from module.models import Module
    module = Module.objects.get(id=module_id)

    progress, created = ModuleCompletion.objects.get_or_create(
        student=user,
        module=module,
        defaults={'state': ContentState.COMPLETED.value}
    )

    if not created and progress.state != ContentState.COMPLETED.value:
        progress.transition_to(ContentState.COMPLETED, **completion_data)

    # Check what gets unlocked
    newly_unlocked = _check_unlocked_after_module_completion(user, module_id)

    # Log completion event
    _log_progress_event(user, 'module', module_id, 'module_completed',
                        new_state=ContentState.COMPLETED.value,
                        metadata={'unlocked': newly_unlocked})

    return {
        'completed_content': {'module': module_id},
        'newly_unlocked': newly_unlocked,
        'next_recommended': _get_next_recommended_after_module(user, module_id)
    }


# Helper functions for checking completion and unlocking
def _check_and_complete_module(user: User, module) -> bool:
    """Check if module is complete and mark it if so."""
    from core.common.utils.access_control import _is_module_complete

    if _is_module_complete(user, module):
        progress, created = ModuleCompletion.objects.get_or_create(
            student=user,
            module=module,
            defaults={'state': ContentState.COMPLETED.value, 'is_completed': True}
        )

        if not created and not progress.is_completed:
            progress.transition_to(ContentState.COMPLETED)

        return True

    return False


def _check_unlocked_after_lesson_completion(user: User, lesson_id: int) -> List[dict]:
    """Check what content becomes available after lesson completion."""
    newly_unlocked = []

    from module.models import Lesson
    lesson = Lesson.objects.get(id=lesson_id)
    next_lesson = lesson.get_next_lesson()

    if next_lesson:
        # Check if next lesson should be available
        can_access, _ = can_access_lesson(user, next_lesson)
        if can_access:
            progress, created = LessonProgress.objects.get_or_create(
                student=user,
                lesson=next_lesson,
                defaults={'state': ContentState.AVAILABLE.value}
            )
            if created:
                newly_unlocked.append({'lesson': next_lesson.id})

    return newly_unlocked


def _check_unlocked_after_quiz_completion(user: User, quiz_id: int) -> List[dict]:
    """Check what content becomes available after quiz completion."""
    newly_unlocked = []

    from module.models import Quiz
    quiz = Quiz.objects.get(id=quiz_id)

    # Quiz completion might unlock next lesson or module content
    if quiz.lesson:
        # Lesson-level quiz - check if next lesson becomes available
        next_lesson = quiz.lesson.get_next_lesson()
        if next_lesson:
            can_access, _ = can_access_lesson(user, next_lesson)
            if can_access:
                progress, created = LessonProgress.objects.get_or_create(
                    student=user,
                    lesson=next_lesson,
                    defaults={'state': ContentState.AVAILABLE.value}
                )
                if created:
                    newly_unlocked.append({'lesson': next_lesson.id})

    return newly_unlocked


def _check_unlocked_after_module_completion(user: User, module_id: int) -> List[dict]:
    """Check what content becomes available after module completion."""
    newly_unlocked = []

    from module.models import Module
    module = Module.objects.get(id=module_id)
    next_module = module.get_next_module()

    if next_module:
        can_access, _ = can_access_module(user, next_module)
        if can_access:
            # Unlock the module
            progress, created = ModuleCompletion.objects.get_or_create(
                student=user,
                module=next_module,
                defaults={'state': ContentState.AVAILABLE.value}
            )
            if created:
                newly_unlocked.append({'module': next_module.id})

            # Unlock first lesson of next module
            first_lesson = next_module.lessons.order_by('order').first()
            if first_lesson:
                lesson_progress, lesson_created = LessonProgress.objects.get_or_create(
                    student=user,
                    lesson=first_lesson,
                    defaults={'state': ContentState.AVAILABLE.value}
                )
                if lesson_created:
                    newly_unlocked.append({'lesson': first_lesson.id})

    return newly_unlocked


# Next recommended content functions
def _get_next_recommended_after_lesson(user: User, lesson_id: int) -> Optional[dict]:
    """Get next recommended content after lesson completion."""
    from module.models import Lesson
    lesson = Lesson.objects.get(id=lesson_id)

    # Check for next lesson first
    next_lesson = lesson.get_next_lesson()
    if next_lesson:
        return {'lesson': next_lesson.id}

    # Check if module is complete and suggest next module
    if _check_and_complete_module(user, lesson.module):
        next_module = lesson.module.get_next_module()
        if next_module:
            return {'module': next_module.id}

    return None


def _get_next_recommended_after_module(user: User, module_id: int) -> Optional[dict]:
    """Get next recommended content after module completion."""
    from module.models import Module
    module = Module.objects.get(id=module_id)
    next_module = module.get_next_module()

    if next_module:
        return {'module': next_module.id}

    return None


def _log_progress_event(user: User, content_type: str, content_id: int, event_type: str, **kwargs):
    """Log progresse event for analytics and debugging."""
    ProgressEvent.objects.create(
        student=user,
        content_type=content_type,
        content_id=content_id,
        event_type=event_type,
        old_state=kwargs.get('old_state'),
        new_state=kwargs.get('new_state'),
        metadata=kwargs.get('metadata', {})
    )


def get_content_state(user, content_type: str, content_id: int):
    """Retrieve the current state of a content item for a user."""
    content_type = content_type.lower()
    try:
        if content_type == 'lesson':
            progress = LessonProgress.objects.get(student=user, lesson_id=content_id)
        elif content_type == 'quiz':
            progress = QuizProgress.objects.get(student=user, quiz_id=content_id)
        elif content_type == 'project':
            progress = ProjectProgress.objects.get(student=user, project_id=content_id)
        elif content_type == 'module':
            progress = ModuleCompletion.objects.get(student=user, module_id=content_id)
        else:
            progress = ContentProgress.objects.get(
                student=user,
                content_item__content_type=content_type,
                content_item_id=content_id
            )
        return ContentState(progress.state)
    except ObjectDoesNotExist:
        return ContentState.LOCKED