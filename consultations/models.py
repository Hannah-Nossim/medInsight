from django.db import models
from django.utils import timezone

class Consultation(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        
    ]
    
    # --- Patient Details (Added to fix the crash) ---
    patient_id = models.CharField(max_length=50, blank=True, null=True, verbose_name="Patient ID")
    patient_age = models.PositiveIntegerField(blank=True, null=True, verbose_name="Age")
    patient_gender = models.CharField(max_length=20, blank=True, null=True, verbose_name="Gender", choices=[
        ('Male', 'Male'),
        ('Female', 'Female'),
        ('Other', 'Other'),
    ])
    duration = models.CharField(max_length=100, blank=True, null=True, verbose_name="Duration of Symptoms")

    # --- Clinical Input ---
    clinical_case = models.TextField(
        help_text="Full clinical case narrative including symptoms, history, and observations."
    )
    
    # --- AI Generated Output ---
    summary = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    management = models.TextField(blank=True, null=True)
    
    # --- Metadata ---
    language = models.CharField(
        max_length=10, 
        choices=LANGUAGE_CHOICES, 
        default='en'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_reviewed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"Consultation #{self.pk} - {self.created_at.strftime('%Y-%m-%d')}"
    
    @property
    def status(self):
        if self.is_reviewed:
            return 'Reviewed'
        elif self.summary and self.diagnosis and self.management:
            return 'Completed'
        else:
            return 'Pending'


class SystemSettings(models.Model):
    """System-wide settings for local model"""
    
    # Model Configuration
    model_loaded = models.BooleanField(default=False)
    model_path = models.CharField(max_length=500, blank=True)
    
    # Generation Parameters
    max_input_length = models.IntegerField(default=512)
    max_output_length = models.IntegerField(default=1024)
    temperature = models.FloatField(default=0.7)
    
    # System preferences
    default_language = models.CharField(
        max_length=10,
        choices=Consultation.LANGUAGE_CHOICES,
        default='en'
    )
    
    # Metadata
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'System Settings'
        verbose_name_plural = 'System Settings'
    
    def __str__(self):
        return f"System Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        pass
    
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class AnalyticsSnapshot(models.Model):
    """Daily analytics snapshots"""
    date = models.DateField(default=timezone.now, unique=True)
    total_consultations = models.IntegerField(default=0)
    consultations_by_language = models.JSONField(default=dict)
    
    class Meta:
        ordering = ['-date']
        indexes = [models.Index(fields=['-date'])]
    
    def __str__(self):
        return f"Analytics for {self.date}"