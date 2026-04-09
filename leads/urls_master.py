from django.urls import path
from . import views_master as views

urlpatterns = [
    # Pages
    path('', views.master_page, name='master_master'),
    path('history/', views.lead_history_page, name='master_lead_history'),
    path('process/', views.process_leads_page, name='master_process_leads'),
    path('process/cat/<str:category>/', views.process_leads_category, name='master_process_leads_category'),
    path('process/<str:country>/', views.process_leads_country, name='master_process_leads_country'),
    path('process/<str:country>/all/', views.process_leads_country_all, name='master_process_leads_country_all'),
    path('process/<str:country>/<str:region>/', views.process_leads_region, name='master_process_leads_region'),

    # Find all emails for process leads (by country or region)
    path('api/find-all-emails-country/<str:country>/', views.find_all_emails_country, name='master_find_all_emails_country'),
    path('api/find-all-emails-region/<str:country>/<str:region>/', views.find_all_emails_region, name='master_find_all_emails_region'),
    path('session/<uuid:session_id>/', views.session_detail, name='master_session_detail'),

    # Master search (server-side background)
    path('api/start-search/', views.start_search, name='master_start_search'),
    path('api/session/<uuid:session_id>/progress/', views.session_progress, name='master_session_progress'),

    # Location API
    path('api/countries/', views.api_countries, name='master_api_countries'),
    path('api/states/<str:country_code>/', views.api_states, name='master_api_states'),
    path('api/cities/<str:country_code>/<str:state_name>/', views.api_cities, name='master_api_cities'),

    # Apollo API
    path('api/search/', views.apollo_search, name='master_apollo_search'),

    # Email scraper
    path('api/find-emails/', views.find_emails, name='master_find_emails'),

    # Sessions & leads
    path('api/create-session/', views.create_session, name='master_create_session'),
    path('api/update-session/', views.update_session, name='master_update_session'),
    path('api/sessions/', views.session_list, name='master_session_list'),
    path('api/lead/<int:lead_id>/edit/', views.edit_lead, name='master_edit_lead'),
    path('api/lead/<int:lead_id>/find-missing/', views.find_missing, name='master_find_missing'),
    path('api/session/<uuid:session_id>/find-all-emails/', views.find_all_missing, name='master_find_all_missing'),
    path('api/session/<uuid:session_id>/delete/', views.delete_session, name='master_delete_session'),

    # In Progress
    path('in-progress/', views.in_progress_page, name='master_in_progress'),
    path('api/in-progress/stop-all/', views.in_progress_stop_all, name='master_in_progress_stop_all'),
    path('api/in-progress/live/', views.in_progress_live, name='master_in_progress_live'),

    # Form Automation
    path('form-automation/', views.form_automation_page, name='master_form_automation'),
    path('form-automation/<str:entity_name>/', views.form_automation_entity, name='master_form_automation_entity'),
    path('form-automation/<str:entity_name>/cat/<str:category>/', views.form_automation_category, name='master_form_automation_cat'),
    path('form-automation/<str:entity_name>/<str:country>/', views.form_automation_country, name='master_form_automation_country'),
    path('form-automation/<str:entity_name>/<str:country>/all/', views.form_automation_country_all, name='master_form_automation_country_all'),
    path('form-automation/<str:entity_name>/<str:country>/<str:region>/', views.form_automation_region, name='master_form_automation_region'),
    path('api/form-automation/run/', views.form_automation_run, name='master_form_automation_run'),
    path('api/form-automation/run-batch/', views.form_automation_run_batch, name='master_form_automation_run_batch'),
    path('api/form-automation/cancel/<int:task_id>/', views.form_automation_cancel, name='master_form_automation_cancel'),
    path('api/form-automation/cancel-all/', views.form_automation_cancel_all, name='master_form_automation_cancel_all'),
    path('api/form-automation/logs/', views.form_automation_logs, name='master_form_automation_logs'),
    path('api/form-automation/status/', views.form_automation_status, name='master_form_automation_status'),

    # Apify Google Maps
    path('api/google-maps/start/', views.apify_start, name='master_apify_start'),
    path('api/google-maps/status/<str:run_id>/', views.apify_status, name='master_apify_status'),
    path('api/google-maps/results/<str:run_id>/', views.apify_results, name='master_apify_results'),

    # LinkedIn
    path('api/linkedin/start/', views.linkedin_start, name='master_linkedin_start'),
    path('api/linkedin/status/<str:run_id>/', views.linkedin_status, name='master_linkedin_status'),
    path('api/linkedin/results/<str:run_id>/', views.linkedin_results, name='master_linkedin_results'),
]
