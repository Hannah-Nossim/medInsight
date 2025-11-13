from django import forms
from .models import Consultation, SystemSettings


class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            'patient_name', 'patient_age', 'patient_gender',
            'chief_complaint', 'symptoms_description', 'duration',
            'vital_signs', 'medical_history', 'language'
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter patient name'
            }),
            'patient_age': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Age',
                'min': '0',
                'max': '150'
            }),
            'patient_gender': forms.Select(attrs={
                'class': 'form-control'
            }),
            'chief_complaint': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Main complaint...'
            }),
            'symptoms_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Describe all symptoms in detail...'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 3 days, 2 weeks'
            }),
            'vital_signs': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'BP, Temp, HR, RR (optional)'
            }),
            'medical_history': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Relevant medical history (optional)'
            }),
            'language': forms.Select(attrs={
                'class': 'form-control'
            }),
        }


class ConsultationEditForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = ['summary', 'diagnosis', 'management']
        widgets = {
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'diagnosis': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5
            }),
            'management': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6
            }),
        }


class SystemSettingsForm(forms.ModelForm):
    """Simplified form for local model settings"""
    
    class Meta:
        model = SystemSettings
        fields = [
            'max_input_length',
            'max_output_length',
            'temperature',
            'default_language',
        ]
        widgets = {
            'max_input_length': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '128',
                'max': '1024'
            }),
            'max_output_length': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '128',
                'max': '2048'
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.1',
                'min': '0',
                'max': '1'
            }),
            'default_language': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
        help_texts = {
            'temperature': 'Lower values (0.0-0.3) = more focused, Higher values (0.7-1.0) = more creative',
            'max_input_length': 'Maximum length of input text (in tokens)',
            'max_output_length': 'Maximum length of generated response (in tokens)',
        }