from django.contrib import admin
from .models import (Module, Course, Lesson, ContentItem, Quiz, Question, CertificateRequest, CertificatePayment,
                     Resource, LessonNote, Certificate, Answer, CapstoneInstructions, CapstoneProject)


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