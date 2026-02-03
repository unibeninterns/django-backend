# utils.py
from django.template.loader import render_to_string
from django.utils import timezone
from django.db.models import Avg
from weasyprint import HTML
import io

from .models import CapstoneProject, ExamSubmission, QuizSubmission
from payments.models import Enrollment
from progresse.models import ModuleCompletion


def generate_transcript_pdf(user, course):
    """
    Generates a PDF transcript for a specific user and course.
    Returns the PDF bytes.
    """

    # 1. Get Enrollment Info
    enrollment = Enrollment.objects.filter(user=user, package__course=course).first()

    # 2. Get Capstone Info
    # Note: We traverse backwards from user -> CapstoneProject -> Instructions -> Course
    capstone = CapstoneProject.objects.filter(
        student=user,
        instructions__course=course
    ).first()

    final_exam_sub = ExamSubmission.objects.filter(
        student=user,
        exam__course=course
    ).first()

    # 3. Compile Module Data
    # This loop gathers quiz scores for every module in the course
    modules_data = []

    for module in course.modules.all().order_by('order'):

        score = QuizSubmission.objects.filter(
            student=user,
            quiz__lesson__module=module
        ).aggregate(Avg('score'))['score__avg'] or 0

        completion_record = ModuleCompletion.objects.filter(student=user, module=module).first()

        # Placeholder logic if you don't have QuizSubmission handy yet:
        avg_score = score  # Replace with actual query

        modules_data.append({
            'title': module.title,
            'completed_at': completion_record.completed_at,
            'score': round(avg_score, 1)
        })

    # 4. Prepare Context for Template
    context = {
        'student': user,
        'course': course,
        'enrollment': enrollment,
        'capstone': capstone,
        'final_exam': final_exam_sub,
        'modules_data': modules_data,
    }

    # 5. Render HTML
    html_string = render_to_string('pdf/transcript.html', context)

    # 6. Convert to PDF using WeasyPrint
    # We use BytesIO to hold the PDF in memory instead of saving a file
    pdf_file = io.BytesIO()
    HTML(string=html_string).write_pdf(target=pdf_file)

    # Reset pointer to start of file
    pdf_file.seek(0)

    return pdf_file.getvalue()