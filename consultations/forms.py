from django import forms
from .models import Consultation, SystemSettings

class ConsultationForm(forms.ModelForm):
    class Meta:
        model = Consultation
        # Updated fields to match the new single-input HTML structure
        fields = [
            'clinical_case', 
            'language'
        ]
        widgets = {
            'clinical_case': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 10,
                'placeholder': 'Paste the full clinical case narrative here (patient history, symptoms, observations, etc.)...'
            }),
            'language': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

# --- The forms below remain unchanged ---

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