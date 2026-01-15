from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
import qrcode
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
import logging
from django.http import HttpResponse
from module.models import Certificate, CertificateRequest
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from payments.models import Enrollment

logger = logging.getLogger(__name__)


def generate_certificate_pdf(certificate):
    """
    certificate: An instance of the new Certificate model
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # CHANGE 2: Use 'certificate_number' from the new model
    serial = certificate.certificate_number
    TOP = height - 80

    # --- Title & Subtitle ---
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, TOP, "Certificate of Completion")

    p.setFont("Helvetica", 14)
    p.drawCentredString(width / 2, TOP - 70, "This is to certify that")

    # --- Student Name ---
    # Access student via the foreign key
    user = certificate.student
    # Manually combine first and last name
    full_name = f"{user.first_name} {user.last_name}".strip()

    # Use full_name if it exists, otherwise fallback to email (since username might be blank)
    student_name = full_name if full_name else user.email
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width / 2, TOP - 120, student_name.upper())

    # --- Course Title ---
    p.setFont("Helvetica", 14)
    p.drawCentredString(width / 2, TOP - 170, "has successfully completed the course")

    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width / 2, TOP - 210, certificate.course.title)

    # --- Date ---
    # CHANGE 3: Use 'issued_at' from the Certificate model
    issued_date = certificate.issued_at.strftime('%B %d, %Y')
    p.setFont("Helvetica", 12)
    p.drawCentredString(width / 2, TOP - 260, f"Issued on {issued_date}")

    # --- QR Code Verification ---
    # CHANGE 4: Use 'verification_code' (UUID) for the URL
    # Ensure to convert UUID to string
    verification_url = f"{settings.FRONTEND_URL}/verify-certificate/{str(certificate.verification_code)}/"

    qr = qrcode.make(verification_url)
    qr_buffer = BytesIO()
    # FIX 1: Explicitly specify the format
    qr.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)

    qr_image = ImageReader(qr_buffer)

    p.drawImage(qr_image, width - 50 * mm, 30 * mm, 30 * mm, 30 * mm)

    p.setFont("Helvetica", 8)
    p.drawCentredString(width - 35 * mm, 28 * mm, "Scan to verify")

    # --- Footer / Serial ---
    p.setFont("Helvetica", 10)
    # Display the official certificate number
    p.drawString(20 * mm, 30 * mm, f"Certificate No: {serial}")

    # Optional: Display the Verification Hash in small text if needed
    p.setFont("Helvetica", 6)
    p.drawString(20 * mm, 25 * mm, f"Hash: {certificate.verification_hash[:20]}...")

    p.showPage()
    p.save()
    buffer.seek(0)

    # CHANGE 5: Save to the 'pdf_file' field on the Certificate model
    filename = f"certificate_{serial}.pdf"
    certificate.pdf_file.save(
        filename,
        ContentFile(buffer.read()),
        save=True
    )
    buffer.close()


def send_certificate_email(certificate):
    """
    Sends certificate PDF to student via email.
    Fails silently (logs error but does not raise).
    """

    student = certificate.student
    email = student.email

    if not email:
        logger.warning(
            f"Certificate {certificate.id} not emailed: student has no email."
        )
        return

    subject = "Your Course Completion Certificate"

    context = {
        'student_name': student.get_full_name(),
        'course_title': certificate.course.title,
        'certificate_id': certificate.id,
        'verification_url': f"{settings.FRONTEND_URL}/verify/{certificate.verification_code}"
    }

    body = render_to_string(
        "emails/certificate_issued.txt",
        context
    )

    email_message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )

    # Attach PDF
    if certificate.pdf_file:
        email_message.attach_file(certificate.pdf_file.path)

    try:
        email_message.send(fail_silently=False)
    except Exception as e:
        logger.error(
            f"Failed to send certificate email for {certificate.id}: {str(e)}"
        )


def generate_certificate_preview_pdf(cert_request):
    """
    Generates a preview certificate PDF (NOT saved to DB)
    """

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ---- Layout ----
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 80, "Certificate of Completion")

    p.setFont("Helvetica", 14)
    p.drawCentredString(
        width / 2,
        height - 150,
        "This is to certify that"
    )

    # Student Name
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(
        width / 2,
        height - 200,
        cert_request.student.get_full_name()
    )

    p.setFont("Helvetica", 14)
    p.drawCentredString(
        width / 2,
        height - 250,
        "has successfully completed the course"
    )

    # Course Title
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(
        width / 2,
        height - 300,
        cert_request.course.title
    )

    # Issue date (preview)
    p.setFont("Helvetica", 12)
    p.drawCentredString(
        width / 2,
        height - 360,
        f"Issue Date (Preview): {timezone.now().date().strftime('%B %d, %Y')}"
    )

    # Preview watermark
    p.setFont("Helvetica-Bold", 50)
    p.setFillGray(0.9)
    p.drawCentredString(width / 2, height / 2, "PREVIEW")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = 'inline; filename="certificate_preview.pdf"'

    buffer.close()
    return response


def generate_certificate_reissue_preview_pdf(cert_request):
    """
    Generates a re-issued certificate preview PDF (NOT saved)
    """

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # ---- Layout ----
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 80, "Certificate of Completion")

    p.setFont("Helvetica", 14)
    p.drawCentredString(
        width / 2,
        height - 150,
        "This is to certify that"
    )

    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(
        width / 2,
        height - 200,
        cert_request.student.get_full_name()
    )

    p.setFont("Helvetica", 14)
    p.drawCentredString(
        width / 2,
        height - 250,
        "has successfully completed the course"
    )

    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(
        width / 2,
        height - 300,
        cert_request.course.title
    )

    p.setFont("Helvetica", 12)
    p.drawCentredString(
        width / 2,
        height - 360,
        f"Re-Issue Date (Preview): {timezone.now().date().strftime('%B %d, %Y')}"
    )

    # Watermark
    p.setFont("Helvetica-Bold", 45)
    p.setFillGray(0.85)
    p.drawCentredString(width / 2, height / 2, "RE-ISSUE PREVIEW")

    p.showPage()
    p.save()

    buffer.seek(0)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/pdf'
    )
    response['Content-Disposition'] = 'inline; filename="certificate_reissue_preview.pdf"'

    buffer.close()
    return response


def get_certificate_request_queryset(
    *,
    course_id=None,
    status=None,
    start_date=None,
    end_date=None
):
    """
    Base queryset for certificate request analytics.
    """

    qs = CertificateRequest.objects.select_related(
        'student',
        'course'
    )

    if course_id:
        qs = qs.filter(course_id=course_id)

    if status:
        qs = qs.filter(status=status)

    if start_date:
        qs = qs.filter(created_at__gte=start_date)

    if end_date:
        qs = qs.filter(created_at__lte=end_date)

    return qs


def get_certificate_overview_stats(
    *,
    course_id=None,
    start_date=None,
    end_date=None
):
    """
    Returns totals and percentages of certificate requests.
    """

    qs = get_certificate_request_queryset(
        course_id=course_id,
        start_date=start_date,
        end_date=end_date
    )

    totals = qs.aggregate(
        total_requests=Count('id'),
        issued=Count('id', filter=Q(status=CertificateRequest.STATUS_APPROVED)),
        pending=Count('id', filter=Q(status=CertificateRequest.STATUS_PENDING)),
        denied=Count('id', filter=Q(status=CertificateRequest.STATUS_DENIED)),
        revoked=Count('id', filter=Q(status=CertificateRequest.STATUS_REVOKED)),
    )

    total = totals['total_requests'] or 1  # avoid division by zero

    percentages = {
        'issued': round((totals['issued'] / total) * 100, 2),
        'pending': round((totals['pending'] / total) * 100, 2),
        'denied': round((totals['denied'] / total) * 100, 2),
        'revoked': round((totals['revoked'] / total) * 100, 2),
    }

    return {
        'totals': totals,
        'percentages': percentages,
    }

def get_certificate_requests_log(
    *,
    course_id=None,
    status=None,
    search=None,
    start_date=None,
    end_date=None
):
    """
    Searchable, filterable certificate request log.
    """

    qs = get_certificate_request_queryset(
        course_id=course_id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )

    if search:
        qs = qs.filter(
            Q(student__first_name__icontains=search) |
            Q(student__last_name__icontains=search) |
            Q(course__title__icontains=search)
        )

    return qs.order_by('-created_at')


def get_issued_certificates_queryset(
    *,
    course_id=None,
    start_date=None,
    end_date=None
):
    """
    Analytics for issued certificates.
    """

    qs = Certificate.objects.select_related(
        'student',
        'course'
    )

    if course_id:
        qs = qs.filter(course_id=course_id)

    if start_date:
        qs = qs.filter(issued_at__gte=start_date)

    if end_date:
        qs = qs.filter(issued_at__lte=end_date)

    return qs


def get_issued_vs_revoked_stats(
    *,
    course_id=None,
    start_date=None,
    end_date=None
):
    qs = get_issued_certificates_queryset(
        course_id=course_id,
        start_date=start_date,
        end_date=end_date
    )

    return qs.aggregate(
        total_issued=Count('id'),
        # Use the 'status' field instead of 'is_revoked'
        revoked=Count('id', filter=Q(status='revoked')),
        active=Count('id', filter=Q(status='issued')),
    )


def get_certificate_override_stats(
    *,
    course_id=None
):
    qs = get_certificate_request_queryset(course_id=course_id)

    return qs.aggregate(
        total_overrides=Count('id', filter=Q(overridden=True)),
        approved_overrides=Count(
            'id',
            filter=Q(overridden=True, status=CertificateRequest.STATUS_APPROVED)
        ),
        denied_overrides=Count(
            'id',
            filter=Q(overridden=True, status=CertificateRequest.STATUS_DENIED)
        ),
    )

def get_certificate_trends_by_month(
    *,
    course_id=None
):
    qs = get_certificate_request_queryset(course_id=course_id)

    return (
        qs.annotate(month=TruncMonth('created_at'))
          .values('month')
          .annotate(
              total=Count('id'),
              issued=Count('id', filter=Q(status=CertificateRequest.STATUS_APPROVED)),
              denied=Count('id', filter=Q(status=CertificateRequest.STATUS_DENIED)),
          )
          .order_by('month')
    )

def can_user_access_resource(user, resource):
    if not user.is_authenticated:
        return resource.visibility == 'public'

    if user.role == 'admin':
        return True

    if resource.visibility == 'admin':
        return False

    if user.role == 'tutor':
        if resource.visibility in ['public', 'tutors']:
            return True
        # optionally enforce tutor-course assignment here
        return False

    if user.role == 'student':
        if resource.visibility == 'public':
            return True

        if resource.visibility == 'enrolled':
            return Enrollment.objects.filter(
                user=user,
                package__course=resource.course,
                status='active'
            ).exists()

    return False

