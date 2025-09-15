
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

def send_html_email(subject, template_name, context, recipient_list):
    """
    Sends an HTML email by rendering a template.
    """
    html_message = render_to_string(template_name, context)
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        html_message=html_message,
        fail_silently=False,
    )
