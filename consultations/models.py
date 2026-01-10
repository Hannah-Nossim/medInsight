# from django.db import models
# from django.utils import timezone

# class Consultation(models.Model):
#     LANGUAGE_CHOICES = [
#         ('en', 'English'),
#         ('sw', 'Swahili'),
#         ('luo', 'Dholuo (Luo)'),
#         ('kam', 'Kikamba'),
#         ('kik', 'Kikuyu'),
#         ('luh', 'Luhya'),
#         ('ma',  'Maasai'),
#     ]
    
#     # Input
#     patient_name = models.CharField(max_length=200)
#     patient_age = models.IntegerField()
#     patient_gender = models.CharField(
#         max_length=10, 
#         choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')]
#     )
#     chief_complaint = models.TextField()
#     symptoms_description = models.TextField()
#     duration = models.CharField(max_length=100)
#     vital_signs = models.TextField(blank=True, null=True)
#     medical_history = models.TextField(blank=True, null=True)
    
#     # AI Generated Output
#     summary = models.TextField(blank=True, null=True)
#     diagnosis = models.TextField(blank=True, null=True)
#     management = models.TextField(blank=True, null=True)
    
#     # Metadata
#     language = models.CharField(
#         max_length=10, 
#         choices=LANGUAGE_CHOICES, 
#         default='en'
#     )
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#     is_reviewed = models.BooleanField(default=False)
    
#     class Meta:
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['-created_at']),
#             models.Index(fields=['patient_name']),
#         ]
    
#     def __str__(self):
#         return f"Consultation for {self.patient_name} - {self.created_at.strftime('%Y-%m-%d')}"
    
#     @property
#     def status(self):
#         if self.is_reviewed:
#             return 'Reviewed'
#         elif self.summary and self.diagnosis and self.management:
#             return 'Completed'
#         else:
#             return 'Pending'


# class SystemSettings(models.Model):
#     """Single row table for system-wide settings"""
    
#     MODEL_CHOICES = [
#         ('gpt-4o-mini', 'OpenAI GPT-4o Mini'),
#         ('gpt-4o', 'OpenAI GPT-4o'),
#         ('claude-3-5-haiku-20241022', 'Claude 3.5 Haiku'),
#         ('claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet'),
#         ('llama-3.1-8b-instant', 'Groq Llama 3.1 8B'),
#         ('llama-3.1-70b-versatile', 'Groq Llama 3.1 70B'),
#         ('mixtral-8x7b-32768', 'Groq Mixtral 8x7B'),
#         ('custom', 'Custom Model'),
#     ]
    
#     API_PROVIDER_CHOICES = [
#         ('openai', 'OpenAI'),
#         ('anthropic', 'Anthropic (Claude)'),
#         ('groq', 'Groq'),
#         ('together', 'Together AI'),
#         ('custom', 'Custom Provider'),
#     ]
    
#     # LLM Configuration
#     api_provider = models.CharField(
#         max_length=50,
#         choices=API_PROVIDER_CHOICES,
#         default='groq'
#     )
#     api_key = models.CharField(max_length=500, blank=True)
#     api_url = models.URLField(
#         max_length=500,
#         default='https://api.groq.com/openai/v1/chat/completions',
#         help_text='API endpoint URL'
#     )
#     model_name = models.CharField(
#         max_length=100,
#         choices=MODEL_CHOICES,
#         default='llama-3.1-8b-instant'
#     )
#     custom_model_name = models.CharField(
#         max_length=100,
#         blank=True,
#         help_text='Used when model_name is "custom"'
#     )
#     temperature = models.FloatField(
#         default=0.3,
#         help_text='Model temperature (0.0 - 1.0). Lower = more focused'
#     )
#     max_tokens = models.IntegerField(
#         default=2000,
#         help_text='Maximum tokens in response'
#     )
    
#     # System preferences
#     enable_notifications = models.BooleanField(default=True)
#     default_language = models.CharField(
#         max_length=10,
#         choices=Consultation.LANGUAGE_CHOICES,
#         default='en'
#     )
    
#     # Metadata
#     updated_at = models.DateTimeField(auto_now=True)
#     updated_by = models.CharField(max_length=100, blank=True)
    
#     class Meta:
#         verbose_name = 'System Settings'
#         verbose_name_plural = 'System Settings'
    
#     def __str__(self):
#         return f"System Settings (Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')})"
    
#     def save(self, *args, **kwargs):
#         # Ensure only one settings instance exists
#         self.pk = 1
#         super().save(*args, **kwargs)
    
#     def delete(self, *args, **kwargs):
#         pass  # Prevent deletion
    
#     @classmethod
#     def load(cls):
#         obj, created = cls.objects.get_or_create(pk=1)
#         return obj
    
#     def get_model_display_name(self):
#         if self.model_name == 'custom':
#             return self.custom_model_name or 'Custom Model'
#         return dict(self.MODEL_CHOICES).get(self.model_name, self.model_name)
    
#     def is_configured(self):
#         """Check if API is properly configured"""
#         return bool(self.api_key and self.api_url and 
#                    (self.model_name != 'custom' or self.custom_model_name))


# class AnalyticsSnapshot(models.Model):
#     """Daily analytics snapshots for trending"""
#     date = models.DateField(default=timezone.now, unique=True)
#     total_consultations = models.IntegerField(default=0)
#     consultations_by_language = models.JSONField(default=dict)
#     top_diagnoses = models.JSONField(default=list)
#     avg_processing_time = models.FloatField(default=0.0)
    
#     class Meta:
#         ordering = ['-date']
#         indexes = [models.Index(fields=['-date'])]
    
#     def __str__(self):
#         return f"Analytics for {self.date}"


from django.db import models
from django.utils import timezone

class Consultation(models.Model):
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('sw', 'Swahili'),
        ('luo', 'Dholuo (Luo)'),
        ('kam', 'Kikamba'),
        ('kik', 'Kikuyu'),
        ('luh', 'Luhya'),
        ('ma',  'Maasai'),
    ]
    
    # Input
    # Replaced detailed fields with a single clinical case text field
    clinical_case = models.TextField(
        help_text="Full clinical case narrative including symptoms, history, and observations."
    )
    
    # AI Generated Output
    summary = models.TextField(blank=True, null=True)
    diagnosis = models.TextField(blank=True, null=True)
    management = models.TextField(blank=True, null=True)
    
    # Metadata
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
            # Removed index on patient_name since the field was deleted
        ]
    
    def __str__(self):
        # Updated to use ID instead of Name
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