from django.contrib import admin
from .models import Patient, Visit

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'phone')
    search_fields = ('name', 'phone')

@admin.register(Visit)
class VisitAdmin(admin.ModelAdmin):
    list_display = ('patient_id', 'created_at', 'diagnosis')
    list_filter = ('created_at',)
    search_fields = ('patient_id', 'diagnosis')
