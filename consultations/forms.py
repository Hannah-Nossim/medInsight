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
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent',
                'rows': 10,
                'placeholder': 'Paste the full clinical case narrative here (patient history, symptoms, observations, etc.)...'
            }),
            'language': forms.Select(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent'
            }),
        }

# --- Updated Edit Form to include Patient Details ---

class ConsultationEditForm(forms.ModelForm):
    class Meta:
        model = Consultation
        fields = [
            'patient_id', 
            'patient_age', 
            'patient_gender', 
            'duration', 
            'summary', 
            'diagnosis', 
            'management'
        ]
        widgets = {
            # New Patient Fields
            'patient_id': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500'
            }),
            'patient_age': forms.NumberInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500'
            }),
            'patient_gender': forms.Select(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500'
            }),
            
            # Existing Clinical Fields
            'summary': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500',
                'rows': 5
            }),
            'diagnosis': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500',
                'rows': 5
            }),
            'management': forms.Textarea(attrs={
                'class': 'w-full rounded-md border-gray-300 shadow-sm focus:border-purple-500 focus:ring-purple-500',
                'rows': 6
            }),
        }

class SystemSettingsForm(forms.ModelForm):
    """Simplified form for local model settings"""
    
    class Meta:
        model = SystemSettings
        fields = [
            'max_input_length',
            'min_output_length',
            'max_output_length',
            'temperature',
            'repetition_penalty',
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