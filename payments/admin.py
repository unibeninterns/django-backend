from django.contrib import admin
from django.utils.html import format_html
from .models import Feature, Package, AddOn, Payment, Enrollment


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active']
    readonly_fields = ['created_at']


class FeatureInline(admin.TabularInline):
    model = Package.features.through
    extra = 1
    verbose_name = "Feature"
    verbose_name_plural = "Features"


@admin.register(Package)
class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'package_type', 'price', 'duration_weeks', 'feature_count', 'is_active', 'created_at']
    list_filter = ['package_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'price']
    readonly_fields = ['created_at']
    filter_horizontal = []  # REMOVED the problematic filter_horizontal
    inlines = [FeatureInline]  # Use inline instead

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'package_type', 'description')
        }),
        ('Pricing & Duration', {
            'fields': ('price', 'duration_weeks')
        }),
        ('Inclusions', {
            'fields': (
                'includes_assessments',
                'includes_certification',
                'includes_transcript',
                'includes_support'
            )
        }),
        ('Status', {
            'fields': ('is_active', 'created_at')
        })
    )

    def feature_count(self, obj):
        return obj.features.count()

    feature_count.short_description = 'Features'


class AddOnInline(admin.TabularInline):
    model = Payment.add_ons.through
    extra = 0
    verbose_name = "Add-On"
    verbose_name_plural = "Add-Ons"


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        'transaction_id',
        'user',
        'package',
        'total_amount',
        'payment_option',
        'status',
        'created_at',
        'payment_status_color'
    ]
    list_filter = ['status', 'payment_option', 'created_at', 'package']
    search_fields = ['transaction_id', 'user__email', 'user__first_name', 'user__last_name', 'package__name']
    readonly_fields = ['transaction_id', 'flutterwave_ref', 'created_at', 'updated_at']
    inlines = [AddOnInline]

    fieldsets = (
        ('Payment Information', {
            'fields': (
                'transaction_id',
                'flutterwave_ref',
                'total_amount',
                'payment_option',
                'status'
            )
        }),
        ('User & Package', {
            'fields': ('user', 'package')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        })
    )

    def payment_status_color(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'failed': 'red',
            'abandoned': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_status_display()
        )

    payment_status_color.short_description = 'Status'


class EnrollmentAddOnInline(admin.TabularInline):
    model = Enrollment.add_ons.through
    extra = 0
    verbose_name = "Add-On"
    verbose_name_plural = "Add-Ons"


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        'user',
        'package',
        'status',
        'enrolled_at',
        'expires_at',
        'is_active_display',
        'days_remaining'
    ]
    list_filter = ['status', 'package', 'enrolled_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'package__name']
    readonly_fields = ['enrolled_at', 'expires_at']
    inlines = [EnrollmentAddOnInline]

    fieldsets = (
        ('Enrollment Information', {
            'fields': ('user', 'package', 'payment', 'status')
        }),
        ('Timestamps', {
            'fields': ('enrolled_at', 'expires_at')
        })
    )

    def is_active_display(self, obj):
        if obj.is_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        else:
            return format_html('<span style="color: red;">✗ Inactive</span>')

    is_active_display.short_description = 'Active'

    def days_remaining(self, obj):
        if obj.expires_at and obj.status == 'active':
            from django.utils import timezone
            remaining = (obj.expires_at - timezone.now()).days
            if remaining > 0:
                return f"{remaining} days"
            else:
                return "Expired"
        return "-"

    days_remaining.short_description = 'Days Remaining'


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['is_active', 'price']
    readonly_fields = ['created_at']


# Admin site configuration
admin.site.site_header = "Learning Management System Admin"
admin.site.site_title = "LMS Admin Portal"
admin.site.index_title = "Package Enrollment Management"