from django.contrib import admin
from .models import *


admin.site.register(ContentProgress)
admin.site.register(LessonProgress)
admin.site.register(ModuleCompletion)
admin.site.register(QuizProgress)
admin.site.register(ProgressEvent)
admin.site.register(ProjectProgress)


