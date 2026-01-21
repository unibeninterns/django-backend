from django.db.models.signals import post_save
from django.dispatch import receiver
from core.common.utils.progress_states import ContentState
from .models import ContentProgress, LessonProgress, ModuleCompletion, QuizProgress, ProjectProgress
from module.models import ContentItem, Lesson, Module, CapstoneInstructions, FinalExam

@receiver(post_save, sender=ContentProgress)
def unlock_next_content_item(sender, instance, **kwargs):
    # Only act if the item was just marked COMPLETED
    if instance.state == ContentState.COMPLETED.value:
        user = instance.student
        current_item = instance.content_item

        # Find the next item in the same lesson
        next_item = ContentItem.objects.filter(
            lesson=current_item.lesson,
            order__gt=current_item.order
        ).order_by('order').first()
        print(current_item.lesson.id)

        if next_item:
            print(f"Next item found: {next_item.id}")
            progress, _ = ContentProgress.objects.get_or_create(
                student=user,
                content_item=next_item
            )
            # Only unlock if it's currently LOCKED
            if progress.state == ContentState.LOCKED.value:
                progress.transition_to(ContentState.AVAILABLE)
        else:
            # 2. No Next Item? -> Lesson is Complete
            from progresse.models import LessonProgress

            lesson_progress, _ = LessonProgress.objects.get_or_create(
                student=user,
                lesson=current_item.lesson
            )

            # Only update if not already completed
            if lesson_progress.state != ContentState.COMPLETED.value:
                lesson_progress.transition_to(ContentState.IN_PROGRESS)
                lesson_progress.transition_to(ContentState.COMPLETED)


@receiver(post_save, sender=LessonProgress)
def unlock_next_lesson(sender, instance, **kwargs):
    if instance.state == ContentState.COMPLETED.value:
        user = instance.student
        current_lesson = instance.lesson

        # Find the next lesson in the same module
        next_lesson = Lesson.objects.filter(
            module=current_lesson.module,
            order__gt=current_lesson.order
        ).order_by('order').first()

        if next_lesson:
            progress, _ = LessonProgress.objects.get_or_create(
                student=user,
                lesson=next_lesson
            )
            if progress.state == ContentState.LOCKED.value:
                progress.transition_to(ContentState.AVAILABLE)

                # IMPORTANT: Also unlock the FIRST ContentItem of this new lesson
                first_item = next_lesson.content_items.order_by('order').first()
                if first_item:
                    cp, _ = ContentProgress.objects.get_or_create(student=user, content_item=first_item)
                    if cp.state == ContentState.LOCKED.value:
                        cp.transition_to(ContentState.AVAILABLE)

                # If there's no video/article, check if there's a quiz to unlock
                elif hasattr(next_lesson, 'quiz'):
                    qp, _ = QuizProgress.objects.get_or_create(student=user, quiz=next_lesson.quiz)
                    if qp.state == ContentState.LOCKED.value:qp.transition_to(ContentState.AVAILABLE)

        else:
            # 2. No Next Lesson? -> Module is Complete
            from progresse.models import ModuleCompletion

            module_progress, _ = ModuleCompletion.objects.get_or_create(
                student=user,
                module=current_lesson.module
            )

            # Only update if not already completed
            if module_progress.state != ContentState.COMPLETED.value:
                module_progress.transition_to(ContentState.COMPLETED)


@receiver(post_save, sender=ModuleCompletion)
def unlock_next_module(sender, instance, **kwargs):
    if instance.state == ContentState.COMPLETED.value:
        user = instance.student
        course = instance.module.course
        current_module = instance.module

        # Find the next module in the course
        next_module = Module.objects.filter(
            course=current_module.course,
            order__gt=current_module.order
        ).order_by('order').first()

        if next_module:
            progress, _ = ModuleCompletion.objects.get_or_create(
                student=user,
                module=next_module
            )
            if progress.state == ContentState.LOCKED.value:
                progress.transition_to(ContentState.AVAILABLE)

                # Find the FIRST Lesson of this new module
                first_lesson = next_module.lessons.order_by('order').first()
                if first_lesson:
                    lp, _ = LessonProgress.objects.get_or_create(
                        student=user,
                        lesson=first_lesson
                    )
                    if lp.state == ContentState.LOCKED.value:
                        lp.transition_to(ContentState.AVAILABLE)

                    # --- NEW QUIZ LOGIC FOR MODULES ---
                    # Check if the first lesson has content items
                    first_item = first_lesson.content_items.order_by('order').first()
                    if first_item:
                        cp, _ = ContentProgress.objects.get_or_create(
                            student=user,
                            content_item=first_item
                        )
                        if cp.state == ContentState.LOCKED.value:
                            cp.transition_to(ContentState.AVAILABLE)

                    # If the lesson only contains a quiz (no videos/text)
                    elif hasattr(first_lesson, 'quiz'):
                        qp, _ = QuizProgress.objects.get_or_create(
                            student=user,
                            quiz=first_lesson.quiz
                        )
                        if qp.state == ContentState.LOCKED.value:
                            qp.transition_to(ContentState.AVAILABLE)

        else:
            # 🏁 NO NEXT MODULE: This was the last module.
            # 1. Double check all modules in this course are completed for this user
            total_modules = Module.objects.filter(course=course).count()
            completed_modules_count = ModuleCompletion.objects.filter(
                student=user,
                module__course=course,
                state=ContentState.COMPLETED.value
            ).count()

            if completed_modules_count >= total_modules:
                # 2. Update Enrollment status
                from payments.models import Enrollment  # Import inside to avoid circular imports
                enrollment = Enrollment.objects.filter(student=user, course=course).first()

                if enrollment and enrollment.status != 'completed':
                    enrollment.status = 'completed'
                    enrollment.save(update_fields=['status'])
                    print(f"🎉 Course {course.title} marked as COMPLETED for {user.email}")

                capstone_instr = CapstoneInstructions.objects.filter(course=course).first()

                if capstone_instr:
                    # 2. Find or Create the tracker
                    # FIX: Link to 'instructions', not 'project'
                    progress, created = ProjectProgress.objects.get_or_create(
                        student=user,
                        instructions=capstone_instr
                    )

                    # 3. UNLOCK IT
                    if progress.state == ContentState.LOCKED.value:
                        progress.transition_to(ContentState.AVAILABLE)

                        # REMOVED: progress.transition_to(ContentState.IN_PROGRESS)
                        # Why? Let the user click "Start" on the dashboard manually.
                        # It feels more natural than auto-starting a timer.

                        print(f"Capstone unlocked for {user.email}")