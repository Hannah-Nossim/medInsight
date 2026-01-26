from django.db import models
from django.utils import timezone

class Consultation(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        
    ]
    
    # --- Link to Clinic App ---
    patient_id = models.CharField(max_length=50, blank=True, null=True, help_text="Linked Patient ID from Clinic App")

    # --- Patient Details (Added to fix the crash) ---
    # patient_id was already here, but let's make sure it's used correctly or merged.
    # The previous code had `patient_id` as "Patient ID" verbose name.
    # Let's keep it but clarify it's the link.
    # Actually, looking at previous file content, it HAD patient_id.
    # I will just ensure it is there and used for this purpose.
    # Wait, in the very first turn I tried to revert? Let's check the file content first.
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
    
    # --- Original AI Output (For training comparison) ---
    original_summary = models.TextField(blank=True, null=True)
    original_diagnosis = models.TextField(blank=True, null=True)
    original_management = models.TextField(blank=True, null=True)
    
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


class Review(models.Model):
    """Explicit user feedback for continuous learning"""
    consultation = models.OneToOneField(Consultation, on_delete=models.CASCADE, related_name='review')
    rating = models.IntegerField(choices=[(i, f"{i} Stars") for i in range(1, 6)], default=5)
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for #{self.consultation.pk}: {self.rating} Stars"


class SystemSettings(models.Model):
    """System-wide settings for local model"""
    
    # Model Configuration
    model_loaded = models.BooleanField(default=False)
    model_path = models.CharField(max_length=500, blank=True)
    
    # Generation Parameters
    max_input_length = models.IntegerField(default=512)
    max_output_length = models.IntegerField(default=450)
    min_output_length = models.IntegerField(default=150, help_text="Forces model to write long enough to include management steps")
    temperature = models.FloatField(default=0.6)
    repetition_penalty = models.FloatField(default=1.3)
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