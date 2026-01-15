from module.models import Module, ContentItem, Course
from progresse.models import ContentProgress
from core.common.utils.progress_states import ContentState

def is_module_completed(user, module: Module) -> bool:
    required_items = ContentItem.objects.filter(lesson__module=module)

    completed_items = ContentProgress.objects.filter(
        student=user,
        content_item__in=required_items,
        state=ContentState.COMPLETED.value
    ).count()

    return completed_items == required_items.count()

# This logic is wrong, I think
def get_course_completion_percentage(user, course: Course) -> float:
    total_items = ContentItem.objects.filter(
        lesson__module__course=course
    ).count()

    if total_items == 0:
        return 0.0

    completed_items = ContentProgress.objects.filter(
        student=user,
        content_item__lesson__module__course_id=course.id,
        state=ContentState.COMPLETED.value
    ).count()

    return round((completed_items / total_items) * 100, 2)


def get_completed_modules_count(user, course: Course) -> int:
    modules = Module.objects.filter(course=course)
    print(modules)

    completed = 0
    for module in modules:
        if is_module_completed(user, module):
            completed += 1

    return completed