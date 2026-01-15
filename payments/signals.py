from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Enrollment
from module.models import Module, Lesson, ContentItem, Quiz, CapstoneProject  # Adjust import path
from core.common.utils.progress_states import ContentState
from progresse.models import (
    ModuleCompletion, LessonProgress, ContentProgress,
    QuizProgress, ProjectProgress
)


@receiver(post_save, sender=Enrollment)
def initialize_course_progress(sender, instance, created, **kwargs):
    """
    When Enrollment becomes active, initialize progress records
    and unlock the first module/lesson/content.
    """
    if instance.status != 'active':
        return

    # Use atomic transaction to ensure partial data isn't saved if something fails
    with transaction.atomic():
        user = instance.user
        # Navigate up to the course: Enrollment -> Package -> Course
        if not instance.package or not instance.package.course:
            return

        course = instance.package.course
        print(f"DEBUG: Initializing progress for user {user} in course {course}")

        # --- 1. Fetch Course Structure ---
        # We need these ordered to know which is "First"
        modules = Module.objects.filter(course=course).order_by('order', 'id')

        if not modules.exists():
            return

        first_module = modules.first()

        # --- 2. Initialize Modules ---
        for module in modules:
            mc, _ = ModuleCompletion.objects.get_or_create(
                student=user,
                module=module,
                defaults={'state': ContentState.LOCKED.value}
            )
            # Unlock ONLY the first module
            if module == first_module:
                mc.transition_to(ContentState.AVAILABLE)

        # --- 3. Initialize Lessons (Unlock first lesson of first module) ---
        lessons = Lesson.objects.filter(module__in=modules).order_by('order', 'id')
        first_lesson = lessons.filter(module=first_module).first()

        for lesson in lessons:
            lp, _ = LessonProgress.objects.get_or_create(
                student=user,
                lesson=lesson,
                defaults={'state': ContentState.LOCKED.value}
            )
            if lesson == first_lesson:
                lp.transition_to(ContentState.AVAILABLE)

        # --- 4. Initialize Content Items (Unlock first item of first lesson) ---
        content_items = ContentItem.objects.filter(lesson__in=lessons)
        first_content = None
        if first_lesson:
            first_content = content_items.filter(lesson=first_lesson).order_by('order', 'id').first()

        for item in content_items:
            cp, _ = ContentProgress.objects.get_or_create(
                student=user,
                content_item=item,
                defaults={'state': ContentState.LOCKED.value}
            )
            if item == first_content:
                cp.transition_to(ContentState.AVAILABLE)

        # --- 5. Initialize Quizzes & Projects (Keep LOCKED) ---
        # Quizzes usually unlock after lessons are done
        quizzes = Quiz.objects.filter(module__in=modules)
        for quiz in quizzes:
            QuizProgress.objects.get_or_create(
                student=user,
                quiz=quiz,
                defaults={'state': ContentState.LOCKED.value}
            )

        projects = CapstoneProject.objects.filter(module__in=modules)
        for project in projects:
            ProjectProgress.objects.get_or_create(
                student=user,
                project=project,
                defaults={'state': ContentState.LOCKED.value}
            )