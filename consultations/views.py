from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Count
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from datetime import timedelta
import json
from .models import Consultation, SystemSettings, AnalyticsSnapshot
from .forms import ConsultationForm, ConsultationEditForm, SystemSettingsForm
from .services import LLMService
from .utils import generate_pdf_report


# ==================== PUBLIC PAGES ====================

def home(request):
    """Homepage/Landing page"""
    # Get some stats for the homepage
    total_consultations = Consultation.objects.count()
    languages_supported = len(Consultation.LANGUAGE_CHOICES)
    
    # Get recent activity (last 7 days)
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
    # Today's stats
    today = timezone.now().date()
    today_consultations = Consultation.objects.filter(
        created_at__date=today
    ).count()
    
    # This week's stats
    week_start = today - timedelta(days=today.weekday())
    week_consultations = Consultation.objects.filter(
        created_at__date__gte=week_start
    ).count()
    
    # This month's stats
    month_consultations = Consultation.objects.filter(
        created_at__year=today.year,
        created_at__month=today.month
    ).count()
    
    # Total stats
    total_consultations = Consultation.objects.count()
    reviewed_count = Consultation.objects.filter(is_reviewed=True).count()
    
    # Recent consultations (last 10)
    recent_consultations = Consultation.objects.all()[:10]
    
    # Language distribution
    language_stats = Consultation.objects.values('language').annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Check if model exists
    from .ml_service import LocalModelService
    import os
    from django.conf import settings as django_settings
    
    model_path = getattr(django_settings, 'LOCAL_MODEL_PATH', None)
    model_exists = os.path.exists(model_path) if model_path else False
    
    context = {
        'today_count': today_consultations,
        'week_count': week_consultations,
        'month_count': month_consultations,
        'total_count': total_consultations,
        'reviewed_count': reviewed_count,
        'recent_consultations': recent_consultations,
        'language_stats': language_stats,
        'system_configured': model_exists,  # Check if model folder exists
        'settings': SystemSettings.load(),
    }
    return render(request, 'consultations/dashboard.html', context)

# ==================== CONSULTATION FLOW ====================

def consultation_form(request):
    """Display the form for entering patient symptoms"""
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save()
            messages.success(request, 'Consultation created successfully!')
            return redirect('consultation_result', pk=consultation.pk)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        # Pre-fill with default language from settings
        settings = SystemSettings.load()
        initial = {'language': settings.default_language}
        form = ConsultationForm(initial=initial)
    
    return render(request, 'consultations/consultation_form.html', {
        'form': form
    })


def consultation_result(request, pk):
    """Display the result page with streaming"""
    consultation = get_object_or_404(Consultation, pk=pk)
    return render(request, 'consultations/consultation_result.html', {
        'consultation': consultation
    })


# def stream_ai_response(request, pk):
#     """Stream the AI response in real-time using Server-Sent Events"""
#     consultation = get_object_or_404(Consultation, pk=pk)
    
#     def event_stream():
#         settings = SystemSettings.load()
        
#         # Check if system is configured
#         if not settings.is_configured():
#             error_msg = json.dumps({
#                 "type": "error",
#                 "message": "System not configured. Please configure API settings."
#             })
#             yield f'data: {error_msg}\n\n'
#             return
        
#         llm_service = LLMService(settings)
        
#         # Start streaming
#         yield 'data: {"type": "start"}\n\n'
        
#         accumulated_response = ""
        
#         try:
#             for chunk in llm_service.stream_response(consultation):
#                 if chunk.startswith("Error:"):
#                     error_msg = json.dumps({
#                         "type": "error",
#                         "message": chunk
#                     })
#                     yield f'data: {error_msg}\n\n'
#                     return
                
#                 accumulated_response += chunk
#                 yield f'data: {json.dumps({"type": "chunk", "content": chunk})}\n\n'
            
#             # Parse the complete response
#             parsed_data = llm_service._parse_response(accumulated_response)
            
#             # Save to database
#             consultation.summary = parsed_data.get('summary', '')
#             consultation.diagnosis = parsed_data.get('diagnosis', '')
#             consultation.management = parsed_data.get('management', '')
#             consultation.save()
            
#             # Send completion signal
#             yield f'data: {json.dumps({"type": "complete", "data": parsed_data})}\n\n'
        
#         except Exception as e:
#             error_msg = json.dumps({
#                 "type": "error",
#                 "message": f"Error processing request: {str(e)}"
#             })
#             yield f'data: {error_msg}\n\n'
    
#     response = StreamingHttpResponse(
#         event_stream(),
#         content_type='text/event-stream'
#     )
#     response['Cache-Control'] = 'no-cache'
#     response['X-Accel-Buffering'] = 'no'
    
#     return response


# def stream_ai_response(request, pk):
#     """Stream the AI response using local model"""
#     consultation = get_object_or_404(Consultation, pk=pk)
    
#     def event_stream():
#         from .ml_service import LocalModelService
        
#         try:
#             ml_service = LocalModelService()
            
#             # Check if model is loaded
#             if not ml_service.is_model_loaded():
#                 yield 'data: {"type": "status", "message": "Loading model... (first time takes 10-20 seconds)"}\n\n'
#                 ml_service.load_model()
#                 yield 'data: {"type": "status", "message": "Model loaded! Generating response..."}\n\n'
            
#             # Start
#             yield 'data: {"type": "start"}\n\n'
            
#             # Generate response
#             parsed_data = ml_service.generate_response(consultation)
            
#             # Simulate streaming by sending full response in chunks
#             full_response = f"""SUMMARY: {parsed_data['summary']}

# DIAGNOSIS: {parsed_data['diagnosis']}

# MANAGEMENT: {parsed_data['management']}"""
            
#             # Send as chunks for visual effect
#             chunk_size = 50
#             for i in range(0, len(full_response), chunk_size):
#                 chunk = full_response[i:i+chunk_size]
#                 yield f'data: {json.dumps({"type": "chunk", "content": chunk})}\n\n'
            
#             # Save to database
#             consultation.summary = parsed_data['summary']
#             consultation.diagnosis = parsed_data['diagnosis']
#             consultation.management = parsed_data['management']
#             consultation.save()
            
#             # Send completion
#             yield f'data: {json.dumps({"type": "complete", "data": parsed_data})}\n\n'
            
#         except FileNotFoundError as e:
#             error_msg = json.dumps({
#                 "type": "error",
#                 "message": f"Model not found. Please check model path in settings.py. Error: {str(e)}"
#             })
#             yield f'data: {error_msg}\n\n'
#         except Exception as e:
#             error_msg = json.dumps({
#                 "type": "error",
#                 "message": f"Error: {str(e)}"
#             })
#             yield f'data: {error_msg}\n\n'
    
#     response = StreamingHttpResponse(
#         event_stream(),
#         content_type='text/event-stream'
#     )
#     response['Cache-Control'] = 'no-cache'
#     response['X-Accel-Buffering'] = 'no'
    
#     return response


def stream_ai_response(request, pk):
    """Stream the AI response using local model"""
    consultation = get_object_or_404(Consultation, pk=pk)
    
    def event_stream():
        from .ml_service import LocalModelService
        
        try:
            ml_service = LocalModelService()
            
            # Check if model is loaded
            if not ml_service.is_model_loaded():
                yield 'data: {"type": "status", "message": "Loading model... (first time takes 10-20 seconds)"}\n\n'
                ml_service.load_model()
                yield 'data: {"type": "status", "message": "Model loaded! Generating response..."}\n\n'
            
            # Start
            yield 'data: {"type": "start"}\n\n'
            
            # Generate response
            parsed_data = ml_service.generate_response(consultation)
            
            # Simulate streaming by sending full response in chunks
            full_response = f"""SUMMARY: {parsed_data['summary']}

DIAGNOSIS: {parsed_data['diagnosis']}

MANAGEMENT: {parsed_data['management']}"""
            
            # Send as chunks for visual effect
            chunk_size = 50
            for i in range(0, len(full_response), chunk_size):
                chunk = full_response[i:i+chunk_size]
                yield f'data: {json.dumps({"type": "chunk", "content": chunk})}\n\n'
            
            # Save to database
            consultation.summary = parsed_data['summary']
            consultation.diagnosis = parsed_data['diagnosis']
            consultation.management = parsed_data['management']
            consultation.save()
            
            # Send completion
            yield f'data: {json.dumps({"type": "complete", "data": parsed_data})}\n\n'
            
        except FileNotFoundError as e:
            error_msg = json.dumps({
                "type": "error",
                "message": f"Model not found. Please check model path in settings.py. Error: {str(e)}"
            })
            yield f'data: {error_msg}\n\n'
        except Exception as e:
            error_msg = json.dumps({
                "type": "error",
                "message": f"Error: {str(e)}"
            })
            yield f'data: {error_msg}\n\n'
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
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
            Q(patient_name__icontains=search_query) |
            Q(chief_complaint__icontains=search_query) |
            Q(diagnosis__icontains=search_query)
        )
    
    # Filter by language
    language_filter = request.GET.get('language', '')
    if language_filter:
        consultations = consultations.filter(language=language_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'reviewed':
        consultations = consultations.filter(is_reviewed=True)
    elif status_filter == 'pending':
        consultations = consultations.filter(is_reviewed=False)
    
    # Filter by date range
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
    # Overall stats
    total = Consultation.objects.count()
    reviewed = Consultation.objects.filter(is_reviewed=True).count()
    
    # Language breakdown
    language_data = list(Consultation.objects.values('language').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # Consultations over time (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = []
    for i in range(30):
        date = (thirty_days_ago + timedelta(days=i)).date()
        count = Consultation.objects.filter(created_at__date=date).count()
        daily_stats.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    # Monthly comparison (last 6 months)
    monthly_stats = []
    for i in range(6):
        date = timezone.now() - timedelta(days=30*i)
        count = Consultation.objects.filter(
            created_at__year=date.year,
            created_at__month=date.month
        ).count()
        monthly_stats.insert(0, {
            'month': date.strftime('%b %Y'),
            'count': count
        })
    
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

# def settings_view(request):
#     """System settings configuration"""
#     settings = SystemSettings.load()
    
#     if request.method == 'POST':
#         form = SystemSettingsForm(request.POST, instance=settings)
#         if form.is_valid():
#             form.save()
#             messages.success(request, 'Settings saved successfully!')
#             return redirect('settings')
#     else:
#         form = SystemSettingsForm(instance=settings)
    
#     context = {
#         'form': form,
#         'settings': settings,
#     }
#     return render(request, 'consultations/settings.html', context)


# def test_api_connection(request):
#     """Test API connection endpoint"""
#     if request.method == 'POST':
#         settings = SystemSettings.load()
        
#         if not settings.is_configured():
#             return JsonResponse({
#                 'success': False,
#                 'message': 'Please configure API settings first.'
#             })
        
#         try:
#             llm_service = LLMService(settings)
#             success = llm_service.test_connection()
            
#             if success:
#                 return JsonResponse({
#                     'success': True,
#                     'message': 'Connection successful! API is working correctly.'
#                 })
#             else:
#                 return JsonResponse({
#                     'success': False,
#                     'message': 'Connection failed. Please check your API key and settings.'
#                 })
        
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'message': f'Error: {str(e)}'
#             })
    
#     return JsonResponse({'success': False, 'message': 'Invalid request method'})

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
    
    # Get model info
    from .ml_service import LocalModelService
    try:
        ml_service = LocalModelService()
        model_info = ml_service.get_model_info()
    except:
        model_info = {'loaded': False, 'device': 'unknown'}
    
    context = {
        'form': form,
        'settings': settings_obj,
        'model_info': model_info,
    }
    return render(request, 'consultations/settings.html', context)


# ==================== EXPORT ====================

# def export_consultation_pdf(request, pk):
#     """Export consultation as PDF"""
#     consultation = get_object_or_404(Consultation, pk=pk)
#     pdf = generate_pdf_report(consultation)
    
#     response = HttpResponse(pdf, content_type='application/pdf')
#     filename = f"consultation_{consultation.patient_name}_{consultation.created_at.strftime('%Y%m%d')}.pdf"
#     response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
#     return response


# from django.http import JsonResponse

# def test_model(request):
#     """Test the local model"""
#     if request.method == 'POST':
#         from .ml_service import LocalModelService
        
#         try:
#             ml_service = LocalModelService()
#             success, message = ml_service.test_model()
            
#             return JsonResponse({
#                 'success': success,
#                 'message': message
#             })
#         except Exception as e:
#             return JsonResponse({
#                 'success': False,
#                 'message': f'Error: {str(e)}'
#             })
    
#     return JsonResponse({'success': False, 'message': 'Invalid request'})


# def model_info(request):
#     """Get model information"""
#     from .ml_service import LocalModelService
    
#     try:
#         ml_service = LocalModelService()
#         info = ml_service.get_model_info()
#         return JsonResponse(info)
#     except Exception as e:
#         return JsonResponse({
#             'loaded': False,
#             'error': str(e)
#         })

# Add these at the end of views.py

def test_model(request):
    """Test the local model"""
    if request.method == 'POST':
        from .ml_service import LocalModelService
        
        try:
            ml_service = LocalModelService()
            success, message = ml_service.test_model()
            
            return JsonResponse({
                'success': success,
                'message': message
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request'})


def model_info(request):
    """Get model information"""
    from .ml_service import LocalModelService
    
    try:
        ml_service = LocalModelService()
        info = ml_service.get_model_info()
        return JsonResponse(info)
    except Exception as e:
        return JsonResponse({
            'loaded': False,
            'error': str(e)
        })


def export_consultation_pdf(request, pk):
    """Export consultation as PDF"""
    consultation = get_object_or_404(Consultation, pk=pk)
    
    try:
        from .utils import generate_pdf_report
        pdf = generate_pdf_report(consultation)
        
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"consultation_{consultation.patient_name}_{consultation.created_at.strftime('%Y%m%d')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
    except Exception as e:
        messages.error(request, f'Error generating PDF: {str(e)}')
        return redirect('consultation_detail', pk=pk)