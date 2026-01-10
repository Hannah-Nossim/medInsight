import os
import json
import re
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings as django_settings

# Import the new service we created
from .services import LLMService 
from .models import Consultation, SystemSettings, AnalyticsSnapshot
from .forms import ConsultationForm, ConsultationEditForm, SystemSettingsForm
from .utils import generate_pdf_report

# ==================== PUBLIC PAGES ====================

def home(request):
    """Homepage/Landing page"""
    total_consultations = Consultation.objects.count()
    languages_supported = len(Consultation.LANGUAGE_CHOICES)
    
    week_ago = timezone.now() - timedelta(days=7)
    recent_consultations = Consultation.objects.filter(
        created_at__gte=week_ago
    ).count()
    
    context = {
        'total_consultations': total_consultations,
        'languages_supported': languages_supported,
        'recent_consultations': recent_consultations,
    }
    return render(request, 'consultations/home.html', context)


def about(request):
    """About MedInsight page"""
    return render(request, 'consultations/about.html')


def help_page(request):
    """Help & Documentation page"""
    return render(request, 'consultations/help.html')


# ==================== DASHBOARD ====================

def dashboard(request):
    """Main dashboard with stats and recent consultations"""
    today = timezone.now().date()
    today_consultations = Consultation.objects.filter(created_at__date=today).count()
    
    week_start = today - timedelta(days=today.weekday())
    week_consultations = Consultation.objects.filter(created_at__date__gte=week_start).count()
    
    month_consultations = Consultation.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    
    total_consultations = Consultation.objects.count()
    reviewed_count = Consultation.objects.filter(is_reviewed=True).count()
    recent_consultations = Consultation.objects.all()[:10]
    
    language_stats = Consultation.objects.values('language').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Check configuration
    settings = SystemSettings.load()
    hf_token_configured = bool(os.environ.get("HF_TOKEN") or getattr(settings, 'hf_api_token', None))
    
    context = {
        'today_count': today_consultations,
        'week_count': week_consultations,
        'month_count': month_consultations,
        'total_count': total_consultations,
        'reviewed_count': reviewed_count,
        'recent_consultations': recent_consultations,
        'language_stats': language_stats,
        'system_configured': hf_token_configured,
        'settings': settings,
    }
    return render(request, 'consultations/dashboard.html', context)


# ==================== CONSULTATION FLOW ====================

def consultation_form(request):
    """Display the form for entering clinical case"""
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save()
            messages.success(request, 'Clinical case recorded successfully!')
            return redirect('consultation_result', pk=consultation.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        settings = SystemSettings.load()
        initial = {'language': settings.default_language}
        form = ConsultationForm(initial=initial)
    
    return render(request, 'consultations/consultation_form.html', {'form': form})


def consultation_result(request, pk):
    """Display the result page with streaming"""
    consultation = get_object_or_404(Consultation, pk=pk)
    return render(request, 'consultations/consultation_result.html', {
        'consultation': consultation
    })


def stream_ai_response(request, pk):
    """
    Stream the AI response using the LLMService.
    """
    consultation = get_object_or_404(Consultation, pk=pk)
    
    def event_stream():
        try:
            # Initialize the service
            llm_service = LLMService()
            yield 'data: {"type": "start"}\n\n'
            
            full_text_buffer = ""
            
            # Use the service's stream generator
            # This handles prompting, API calls, and DB saving internally
            for token_content in llm_service.stream_response(consultation):
                yield f'data: {json.dumps({"type": "chunk", "content": token_content})}\n\n'
                full_text_buffer += token_content
            
            # Re-fetch the saved consultation to get the parsed fields
            # (The service saves them before finishing the stream)
            consultation.refresh_from_db()
            
            parsed_data = {
                'summary': consultation.summary,
                'diagnosis': consultation.diagnosis,
                'management': consultation.management
            }
            
            yield f'data: {json.dumps({"type": "complete", "data": parsed_data})}\n\n'

        except Exception as e:
            error_msg = json.dumps({"type": "error", "message": f"AI Service Error: {str(e)}"})
            yield f'data: {error_msg}\n\n'

    stream_generator = event_stream()

    # Return the stream
    response = StreamingHttpResponse(stream_generator, content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no' 
    return response


def consultation_edit(request, pk):
    """Allow clinicians to edit the AI-generated results"""
    consultation = get_object_or_404(Consultation, pk=pk)
    
    if request.method == 'POST':
        form = ConsultationEditForm(request.POST, instance=consultation)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.is_reviewed = True
            consultation.save()
            messages.success(request, 'Consultation updated successfully!')
            return redirect('consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationEditForm(instance=consultation)
    
    return render(request, 'consultations/consultation_edit.html', {
        'form': form,
        'consultation': consultation
    })


def consultation_detail(request, pk):
    """View the final consultation details"""
    consultation = get_object_or_404(Consultation, pk=pk)
    return render(request, 'consultations/consultation_detail.html', {
        'consultation': consultation
    })


# ==================== CONSULTATION HISTORY ====================

def consultation_history(request):
    """Display all consultations with search and filters"""
    consultations = Consultation.objects.all()
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        consultations = consultations.filter(
            Q(clinical_case__icontains=search_query) |
            Q(diagnosis__icontains=search_query) |
            Q(management__icontains=search_query)
        )
    
    # Filters
    language_filter = request.GET.get('language', '')
    if language_filter:
        consultations = consultations.filter(language=language_filter)
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'reviewed':
        consultations = consultations.filter(is_reviewed=True)
    elif status_filter == 'pending':
        consultations = consultations.filter(is_reviewed=False)
    
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        consultations = consultations.filter(created_at__date__gte=date_from)
    if date_to:
        consultations = consultations.filter(created_at__date__lte=date_to)
    
    # Pagination
    paginator = Paginator(consultations, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'language_filter': language_filter,
        'status_filter': status_filter,
        'date_from': date_from,
        'date_to': date_to,
        'languages': Consultation.LANGUAGE_CHOICES,
    }
    return render(request, 'consultations/consultation_history.html', context)


def consultation_delete(request, pk):
    """Delete a consultation"""
    consultation = get_object_or_404(Consultation, pk=pk)
    if request.method == 'POST':
        consultation.delete()
        messages.success(request, 'Consultation deleted successfully!')
        return redirect('consultation_history')
    return redirect('consultation_detail', pk=pk)


# ==================== ANALYTICS ====================

def analytics(request):
    """Analytics and insights page"""
    total = Consultation.objects.count()
    reviewed = Consultation.objects.filter(is_reviewed=True).count()
    
    language_data = list(Consultation.objects.values('language').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = []
    for i in range(30):
        date = (thirty_days_ago + timedelta(days=i)).date()
        count = Consultation.objects.filter(created_at__date=date).count()
        daily_stats.append({'date': date.strftime('%Y-%m-%d'), 'count': count})
    
    monthly_stats = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30*i)
        count = Consultation.objects.filter(
            created_at__year=date.year,
            created_at__month=date.month
        ).count()
        monthly_stats.insert(0, {'month': date.strftime('%b %Y'), 'count': count})
    
    context = {
        'total': total,
        'reviewed': reviewed,
        'pending': total - reviewed,
        'language_data': json.dumps(language_data),
        'daily_stats': json.dumps(daily_stats),
        'monthly_stats': json.dumps(monthly_stats),
    }
    return render(request, 'consultations/analytics.html', context)


# ==================== SETTINGS ====================

def settings_view(request):
    """System settings configuration"""
    settings_obj = SystemSettings.load()
    
    if request.method == 'POST':
        form = SystemSettingsForm(request.POST, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved successfully!')
            return redirect('settings')
    else:
        form = SystemSettingsForm(instance=settings_obj)
    
    # We simplified this since we don't have a local model
    model_info = {'loaded': True, 'type': 'Hugging Face API'}
    
    context = {
        'form': form,
        'settings': settings_obj,
        'model_info': model_info,
    }
    return render(request, 'consultations/settings.html', context)


# ==================== UTILS ====================

def export_consultation_pdf(request, pk):
    """Export consultation as PDF"""
    consultation = get_object_or_404(Consultation, pk=pk)
    try:
        pdf = generate_pdf_report(consultation)
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"consultation_{consultation.pk}_{consultation.created_at.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('consultation_detail', pk=pk)