from django.contrib import admin
from .models import (
    Lead, SourceExhaustionTracker, ExclusionRule, OutreachLog, WeeklyReport,
    EmailCampaign, SmtpConnection, EmailTemplate, LeadList,
)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = [
        'company_name', 'company_domain', 'country', 'city', 'lead_type',
        'source', 'score', 'email_sent', 'form_filled', 'replied',
        'interested', 'closed', 'revenue_monthly', 'sequence_stage',
    ]
    list_filter = [
        'lead_type', 'source', 'country', 'email_sent', 'form_filled',
        'replied', 'interested', 'closed', 'company_size',
    ]
    search_fields = ['company_name', 'company_domain', 'contact_name', 'contact_email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_editable = ['interested', 'closed', 'revenue_monthly']
    list_per_page = 50

    fieldsets = (
        ('Company Info', {
            'fields': ('id', 'company_domain', 'company_name', 'website_url', 'has_contact_form')
        }),
        ('Contact', {
            'fields': ('contact_name', 'contact_email', 'contact_phone')
        }),
        ('Classification', {
            'fields': ('country', 'city', 'lead_type', 'source', 'keyword_used', 'company_size', 'score')
        }),
        ('Outreach Status', {
            'fields': (
                'email_sent', 'form_filled', 'email_opened', 'replied',
                'interested', 'closed', 'revenue_monthly',
            )
        }),
        ('Sequence', {
            'fields': ('sequence_stage', 'last_contacted_at', 'next_followup_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['mark_interested', 'mark_closed', 'reset_sequence']

    @admin.action(description='Mark selected leads as interested')
    def mark_interested(self, request, queryset):
        queryset.update(interested=True)

    @admin.action(description='Mark selected leads as closed')
    def mark_closed(self, request, queryset):
        queryset.update(closed=True, interested=True)

    @admin.action(description='Reset sequence stage to 0')
    def reset_sequence(self, request, queryset):
        queryset.update(sequence_stage=0, next_followup_at=None)


@admin.register(SourceExhaustionTracker)
class SourceExhaustionTrackerAdmin(admin.ModelAdmin):
    list_display = ['source', 'keyword', 'country', 'city', 'lead_type', 'total_found', 'status', 'last_scraped']
    list_filter = ['source', 'status', 'country', 'lead_type']
    search_fields = ['keyword', 'country', 'city']
    list_editable = ['status']


@admin.register(ExclusionRule)
class ExclusionRuleAdmin(admin.ModelAdmin):
    list_display = ['rule_type', 'dimension_value', 'leads_contacted', 'metric_value', 'is_active', 'overridden', 'created_at']
    list_filter = ['rule_type', 'is_active', 'overridden']
    list_editable = ['is_active', 'overridden']
    search_fields = ['dimension_value', 'reason']


@admin.register(OutreachLog)
class OutreachLogAdmin(admin.ModelAdmin):
    list_display = ['lead', 'channel', 'sequence_stage', 'status', 'sending_domain', 'sent_at']
    list_filter = ['channel', 'status', 'sequence_stage']
    search_fields = ['lead__company_name', 'lead__company_domain']
    raw_id_fields = ['lead']


@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = [
        'report_date', 'total_leads', 'total_emailed', 'total_forms_filled',
        'total_replies', 'total_interested', 'total_closed',
    ]
    readonly_fields = [
        'report_date', 'total_leads', 'total_emailed', 'total_forms_filled',
        'total_replies', 'total_interested', 'total_closed',
        'by_country', 'by_lead_type', 'by_source', 'by_channel',
        'exclusions_applied', 'created_at',
    ]


@admin.register(SmtpConnection)
class SmtpConnectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'from_email', 'host', 'port', 'daily_limit', 'is_active']
    list_editable = ['is_active']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_at']


@admin.register(LeadList)
class LeadListAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'created_at']
    filter_horizontal = ['leads']


@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    list_display = ['name', 'status', 'total_sent', 'total_opened', 'total_replied', 'total_bounced', 'created_at']
    list_filter = ['status']


admin.site.site_header = 'SalesHunter v2 Admin'
admin.site.site_title = 'SalesHunter'
admin.site.index_title = 'Lead Management'
