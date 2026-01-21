from django.contrib import admin
from .models import (Module, Course, Lesson, ContentItem, Quiz, Question, CertificateRequest, CertificatePayment,
                     Resource, LessonNote, Certificate, Answer, CapstoneInstructions, CapstoneProject, SupportTicket,
                     QuizSubmission, UserSettings)


admin.site.register(Module)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(ContentItem)
admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(CertificateRequest)
admin.site.register(CertificatePayment)
admin.site.register(Resource)
admin.site.register(LessonNote)
admin.site.register(Certificate)
admin.site.register(Answer)
admin.site.register(CapstoneInstructions)
admin.site.register(CapstoneProject)
admin.site.register(QuizSubmission)
admin.site.register(UserSettings)


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['priority', 'subject', 'user', 'created_at', 'status']
    list_filter = ['priority', 'status'] # Filter by "High" to see Premium users first
    ordering = ['-priority', '-created_at'] # High priority appears at the top