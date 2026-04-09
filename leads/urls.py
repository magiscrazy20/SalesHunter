from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('form/', views.form_filling, name='form_filling'),
    # Email section
    path('email/', views.email_outreach, name='email_outreach'),
    path('email/dashboard/', views.email_dashboard, name='email_dashboard'),
    path('email/campaigns/', views.email_campaigns, name='email_campaigns'),
    path('email/leads/', views.email_leads, name='email_leads'),
    path('email/leads/upload/', views.email_leads_upload, name='email_leads_upload'),
    path('email/leads/add-manual/', views.email_leads_add_manual, name='email_leads_add_manual'),
    path('email/leads/<int:pk>/', views.email_leads_detail, name='email_leads_detail'),
    path('email/leads/<int:pk>/delete/', views.email_leads_delete, name='email_leads_delete'),
    path('email/leads/<int:pk>/delete-selected/', views.email_leads_delete_selected, name='email_leads_delete_selected'),
    path('email/templates/', views.email_templates, name='email_templates'),
    path('email/templates/new/', views.email_template_create, name='email_template_create'),
    path('email/templates/<int:pk>/edit/', views.email_template_edit, name='email_template_edit'),
    path('email/templates/<int:pk>/delete/', views.email_template_delete, name='email_template_delete'),
    path('email/smtp/', views.email_smtp, name='email_smtp'),
    path('email/smtp/new/', views.email_smtp_create, name='email_smtp_create'),
    path('email/smtp/<int:pk>/delete/', views.email_smtp_delete, name='email_smtp_delete'),
    path('email/warmup/', views.email_warmup, name='email_warmup'),
    path('email/reports/', views.email_reports, name='email_reports'),
    path('email/replies/', views.email_replies, name='email_replies'),
    path('email/campaign/new/', views.campaign_create, name='campaign_create'),
    path('email/campaign/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('email/campaign/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('email/campaign/<int:pk>/action/', views.campaign_action, name='campaign_action'),
    # Other
    path('pipeline/', views.leads_pipeline, name='leads_pipeline'),
    path('leads/', views.lead_list, name='lead_list'),
    path('leads/<uuid:pk>/', views.lead_detail, name='lead_detail'),
    path('intelligence/', views.intelligence, name='intelligence'),
    path('exclusion/<int:pk>/toggle/', views.toggle_exclusion, name='toggle_exclusion'),
    path('api/stats/', views.api_lead_stats, name='api_lead_stats'),
    path('track/open/<int:log_id>/', views.track_open, name='track_open'),
    # Lead Master (integrated)
    path('form/master/', include('leads.urls_master')),
]
