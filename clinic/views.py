from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from .models import Patient, Visit
from .forms import VisitForm, PatientForm

def welcome(request):
    """Landing page for unauthenticated users"""
    if request.user.is_authenticated:
        return redirect('clinician_dashboard')
    return render(request, 'clinic/welcome.html')

def register_clinician(request):
    """Register a new clinician (User)"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('clinician_dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'clinic/register.html', {'form': form})

def login_view(request):
    """Login view"""
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('clinician_dashboard')
    else:
        form = AuthenticationForm()
    return render(request, 'clinic/login.html', {'form': form})

def logout_view(request):
    """Logout view"""
    logout(request)
    return redirect('welcome')

@login_required
def clinician_dashboard(request):
    """
    Dashboard view:
    1. List of recent patients
    2. Form to Add New Visit
    3. Form to Add New Patient
    """
    
    # Handle Forms
    visit_form = VisitForm(prefix='visit')
    patient_form = PatientForm(prefix='patient')

    if request.method == 'POST':
        if 'submit_visit' in request.POST:
            visit_form = VisitForm(request.POST, prefix='visit')
            if visit_form.is_valid():
                visit_form.save()
                return redirect('clinician_dashboard')
        
        elif 'submit_patient' in request.POST:
            patient_form = PatientForm(request.POST, prefix='patient')
            if patient_form.is_valid():
                patient_form.save()
                return redirect('clinician_dashboard')
    
    # Get recent patients
    recent_patients = Patient.objects.all().order_by('-pk')[:10]
    
    context = {
        'recent_patients': recent_patients,
        'visit_form': visit_form,
        'patient_form': patient_form
    }
    return render(request, 'clinic/dashboard.html', context)
