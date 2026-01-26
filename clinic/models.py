from django.db import models

class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    # Primary Key is now patient_id
    patient_id = models.CharField(max_length=50, primary_key=True, unique=True, verbose_name="Patient ID")
    name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    phone = models.CharField(max_length=20, blank=True)
    
    def __str__(self):
        return f"{self.patient_id}"

class Visit(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    symptoms = models.TextField()
    diagnosis = models.TextField(blank=True, null=True)
    management_plan = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Visit for {self.patient.patient_id} ({self.created_at.strftime('%Y-%m-%d')})"
