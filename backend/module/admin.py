from django.contrib import admin
from .models import Module, Course, Lesson, ContentItem, Quiz



admin.site.register(Module)
admin.site.register(Course)
admin.site.register(Lesson)
admin.site.register(ContentItem)
admin.site.register(Quiz)