import sys
import os
import json
import re
import requests
from datetime import timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.conf import settings as django_settings

# Import models and forms
from .models import Consultation, SystemSettings, Review
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


# ==================== AI STREAMING (FIXED) ====================

def stream_ai_response(request, pk):
    """
    Connects to the Docker Space to get the AI response.
    Uses the correct training prefix 'CLINICAL CASE:' to trigger structured output.
    """
    consultation = get_object_or_404(Consultation, pk=pk)
    
    def event_stream():
        # 1. FORCE FLUSH
        yield ': ' + (' ' * 2048) + '\n\n'
        
        try:
            print(f"DEBUG: Connecting to Docker Space for consultation {pk}", file=sys.stderr)

            # --- CONFIGURATION ---
            # Your specific Docker Space URL
            SPACE_ENDPOINT = "https://nossim-my-flan-t5-base.hf.space/predict"
            # ---------------------

            yield 'data: {"type": "start"}\n\n'
            
            # 2. Call the Docker Space
            # === CRITICAL FIX ===
            # We change "summarize:" to "CLINICAL CASE:" to match your training data.
            formatted_input = f"CLINICAL CASE: {consultation.clinical_case}"
            
            payload = {
                "inputs": formatted_input,
                "text": formatted_input
            }
            
            response = requests.post(SPACE_ENDPOINT, json=payload, timeout=120)
            response.raise_for_status()
            
            # 3. Process the Result
            data = response.json()
            print(f"DEBUG: Raw Docker Response: {data}", file=sys.stderr)

            # Extract text (Robust extraction supporting 'output' key)
            generated_text = ""
            if isinstance(data, dict):
                generated_text = (
                    data.get('output') or 
                    data.get('generated_text') or 
                    data.get('summary') or 
                    str(data)
                )
            elif isinstance(data, list) and len(data) > 0:
                if isinstance(data[0], dict):
                    generated_text = data[0].get('generated_text', str(data[0]))
                else:
                    generated_text = str(data[0])
            else:
                generated_text = str(data)

            # 4. Save to Database
            consultation.summary = generated_text
            consultation.is_reviewed = False
            
            # --- Save Original (Continuous Learning) ---
            parsed_original = {
                'summary': generated_text,
                'diagnosis': "",
                'management': ""
            }
            # Try to parse structure for original fields too if possible, 
            # or just rely on the same parsing logic if we moved logic to models/utils.
            # For now, we reuse the loose text for summary, but if the model outputs structure, we should parse it.
            # We don't have the `_parse_response` here easily accessible as it was in `MLService`.
            # Let's trust the `generated_text` is the raw full text.
            consultation.original_summary = generated_text 
            # We default diagnosis/management to empty in original if not parsed yet, or we could duplicate logic.
            # Given `parse_response` was in `ml_service.py` but `stream_ai_response` in `views.py` doesn't use it directly here...
            # Actually, `views.py` has logic to save `summary = generated_text`.
            # We will just save the full text to `original_summary` as "Raw Output".
            
            consultation.save()
            
            # 5. Send CHUNK (Critical for display)
            chunk_data = json.dumps({"type": "chunk", "content": generated_text})
            yield f'data: {chunk_data}\n\n'

            # 6. Send Complete
            parsed_data = {
                'summary': consultation.summary,
                'diagnosis': consultation.diagnosis,
                'management': consultation.management
            }
            yield f'data: {json.dumps({"type": "complete", "data": parsed_data})}\n\n'

        except Exception as e:
            print(f"CRITICAL AI ERROR: {str(e)}", file=sys.stderr)
            error_msg = json.dumps({"type": "error", "message": f"AI Error: {str(e)}"})
            yield f'data: {error_msg}\n\n'

    response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
    response['Cache-Control'] = 'no-cache'
    response['X-Accel-Buffering'] = 'no' 
    return response


# ==================== EDIT & HISTORY ====================

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


# ==================== ANALYTICS & SETTINGS ====================

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
        'language_data': language_data,
        'daily_stats': daily_stats,
        'monthly_stats': monthly_stats,
    }
    return render(request, 'consultations/analytics.html', context)


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
    
    model_info = {'loaded': True, 'type': 'Hugging Face API'}
    
    context = {
        'form': form,
        'settings': settings_obj,
        'model_info': model_info,
    }
    return render(request, 'consultations/settings.html', context)


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


# ==================== CONTINUOUS LEARNING / REVIEWS ====================

def submit_review(request, pk):
    """Handle explicit review submission"""
    consultation = get_object_or_404(Consultation, pk=pk)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        # Create or update review
        Review.objects.update_or_create(
            consultation=consultation,
            defaults={'rating': rating, 'comment': comment}
        )
        messages.success(request, 'Thank you for your feedback!')
        
    return redirect('consultation_detail', pk=pk)


def export_training_data(request):
    """
    Export reviewed consultations as JSONL for fine-tuning.
    Format: {"prompt": "...", "completion": "..."}
    """
    # Only export consultations that have been reviewed (edited or explicitly rated)
    # Filter by is_reviewed=True (which implies human edit was made)
    reviewed_consultations = Consultation.objects.filter(is_reviewed=True)
    
    response = HttpResponse(content_type='application/jsonl')
    response['Content-Disposition'] = 'attachment; filename="medinsight_training_data.jsonl"'
    
    for consult in reviewed_consultations:
        # Construct the prompt exactly as the model expects
        prompt = f"CLINICAL CASE: {consult.clinical_case}"
        
        # The completion is the FINAL edited version
        # We try to use the structured format if possible, otherwise just the summary text
        completion = ""
        if consult.diagnosis or consult.management:
            completion = f"Summary: {consult.summary} Diagnosis: {consult.diagnosis} Management: {consult.management}"
        else:
            completion = consult.summary
            
        data = {
            "prompt": prompt,
            "completion": completion,
            "original_completion": consult.original_summary, # Optional: for analysis
            "metadata": {
                "id": consult.pk,
                "rating": consult.review.rating if hasattr(consult, 'review') else None
            }
        }
        
        response.write(json.dumps(data) + '\n')
        
    return response