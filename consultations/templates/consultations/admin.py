from django.contrib import admin
from .models import Consultation, SystemSettings, AnalyticsSnapshot


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = [
        'patient_name', 
        'patient_age', 
        'patient_gender',
        'language',
        'is_reviewed',
        'created_at'
    ]
    list_filter = [
        'language', 
        'is_reviewed', 
        'patient_gender',
        'created_at'
    ]
    search_fields = [
        'patient_name', 
        'chief_complaint',
        'diagnosis'
    ]
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Patient Information', {
            'fields': (
                'patient_name', 
                'patient_age', 
                'patient_gender'
            )
        }),
        ('Clinical Information', {
            'fields': (
                'chief_complaint', 
                'symptoms_description', 
                'duration',
                'vital_signs', 
                'medical_history'
            )
        }),
        ('AI Analysis', {
            'fields': (
                'summary', 
                'diagnosis', 
                'management'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': (
                'language', 
                'is_reviewed', 
                'created_at', 
                'updated_at'
            )
        }),
    )
    
    actions = ['mark_as_reviewed', 'mark_as_pending']
    
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(is_reviewed=True)
        self.message_user(request, f'{updated} consultation(s) marked as reviewed.')
    mark_as_reviewed.short_description = "Mark selected as reviewed"
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(is_reviewed=False)
        self.message_user(request, f'{updated} consultation(s) marked as pending.')
    mark_as_pending.short_description = "Mark selected as pending review"


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = [
        'api_provider',
        'model_name',
        'is_configured',
        'updated_at'
    ]
    readonly_fields = ['updated_at']
    
    fieldsets = (
        ('API Configuration', {
            'fields': (
                'api_provider',
                'api_key',
                'api_url',
                'model_name',
                'custom_model_name',
                'temperature',
                'max_tokens'
            )
        }),
        ('System Preferences', {
            'fields': (
                'enable_notifications',
                'default_language'
            )
        }),
        ('Metadata', {
            'fields': (
                'updated_at',
                'updated_by'
            )
        }),
    )
    
    def has_add_permission(self, request):
        # Only allow one settings instance
        return not SystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of settings
        return False


@admin.register(AnalyticsSnapshot)
class AnalyticsSnapshotAdmin(admin.ModelAdmin):
    list_display = [
        'date',
        'total_consultations',
        'avg_processing_time'
    ]
    list_filter = ['date']
    readonly_fields = [
        'date',
        'total_consultations',
        'consultations_by_language',
        'top_diagnoses',
        'avg_processing_time'
    ]
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False