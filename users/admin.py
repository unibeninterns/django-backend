from django.contrib import admin
from django.contrib import admin
from .models import CustomUser
from django.contrib.auth.admin import UserAdmin


class UserAdminConfig(UserAdmin):
    model = CustomUser
    ordering = ('-start_date',)
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_active', 'is_superuser')
    search_fields = ('email', 'username', 'first_name')
    list_filter = ('email', 'username', 'first_name', 'last_name', 'is_verified', 'is_active', 'is_superuser')
    fieldsets = (
        (None, {'fields': ('email', 'username', 'first_name', 'last_name')}),
        ("Permissions", {'fields': ('is_verified', 'is_active', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, 
            {
                'classes': ('wide',),
                'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2', 'is_verified', 'is_active', 'is_superuser')
            }
        ),
    )


admin.site.register(CustomUser, UserAdminConfig)
