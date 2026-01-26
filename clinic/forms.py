from django import forms
from .models import Visit, Patient

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = ['patient_id', 'name', 'age', 'gender', 'phone']
        widgets = {
            'patient_id': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'PID-1234'}),
            'name': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Full Name'}),
            'age': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded'}),
            'gender': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Optional'}),
        }

class VisitForm(forms.ModelForm):
    class Meta:
        model = Visit
        fields = ['patient', 'symptoms', 'diagnosis', 'management_plan']
        widgets = {
            'patient': forms.Select(attrs={'class': 'w-full p-2 border rounded'}),
            'symptoms': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3, 'id': 'id_symptoms'}),
            'diagnosis': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
            'management_plan': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'rows': 3}),
        }
