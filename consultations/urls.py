# from django.urls import path
# from . import views

# urlpatterns = [
#     # Public pages
#     path('', views.home, name='home'),
#     path('about/', views.about, name='about'),
#     path('help/', views.help_page, name='help'),
    
#     # Dashboard
#     path('dashboard/', views.dashboard, name='dashboard'),
    
#     # Consultation flow
#     path('consultation/new/', views.consultation_form, name='consultation_form'),
#     path('consultation/<int:pk>/result/', views.consultation_result, name='consultation_result'),
#     path('consultation/<int:pk>/stream/', views.stream_ai_response, name='stream_ai_response'),
#     path('consultation/<int:pk>/edit/', views.consultation_edit, name='consultation_edit'),
#     path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
#     path('consultation/<int:pk>/delete/', views.consultation_delete, name='consultation_delete'),
#     path('consultation/<int:pk>/export/', views.export_consultation_pdf, name='export_consultation_pdf'),
    
#     # History
#     path('consultations/', views.consultation_history, name='consultation_history'),
    
#     # Analytics
#     path('analytics/', views.analytics, name='analytics'),
    
#     # Settings
#     path('settings/', views.settings_view, name='settings'),
#     path('settings/test-api/', views.test_api_connection, name='test_api_connection'),
#     path('model/test/', views.test_model, name='test_model'),
# path('model/info/', views.model_info, name='model_info'),
# ]



from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.home, name='home'),
    path('about/', views.about, name='about'),
    path('help/', views.help_page, name='help'),
    
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Consultation flow
    path('consultation/new/', views.consultation_form, name='consultation_form'),
    path('consultation/<int:pk>/result/', views.consultation_result, name='consultation_result'),
    path('consultation/<int:pk>/stream/', views.stream_ai_response, name='stream_ai_response'),
    path('consultation/<int:pk>/edit/', views.consultation_edit, name='consultation_edit'),
    path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultation/<int:pk>/delete/', views.consultation_delete, name='consultation_delete'),
    path('consultation/<int:pk>/export/', views.export_consultation_pdf, name='export_consultation_pdf'),
    
    # History
    path('consultations/', views.consultation_history, name='consultation_history'),
    
    # Analytics
    path('analytics/', views.analytics, name='analytics'),
    
    # Settings - LOCAL MODEL
    path('settings/', views.settings_view, name='settings'),
    path('model/test/', views.test_model, name='test_model'),
    path('model/info/', views.model_info, name='model_info'),
]