from django.contrib import admin
from django.contrib import admin
from .models import CustomUser, EmailOTP, TutorCourseAssignment
from django.contrib.auth.admin import UserAdmin


class UserAdminConfig(UserAdmin):
    model = CustomUser
    ordering = ('-start_date',)
    list_display = ('id', 'email', 'username', 'first_name', 'last_name', 'role', 'cohort', 'is_verified', 'is_active', 'is_superuser')
    search_fields = ('email', 'username', 'first_name')
    list_filter = ('email', 'username', 'first_name', 'last_name', 'role', 'cohort', 'is_verified', 'is_active', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'cohort')}),
        ("Permissions", {'fields': ('is_verified', 'is_active', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, 
            {
                'classes': ('wide',),
                'fields': ('email', 'username', 'first_name', 'last_name', 'role', 'cohort', 'password1', 'password2', 'is_verified', 'is_active', 'is_superuser')
            }
        ),
    )


admin.site.register(CustomUser, UserAdminConfig)
admin.site.register(EmailOTP)
admin.site.register(TutorCourseAssignment)
