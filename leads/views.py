import base64
import csv
import io
import json
import threading
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import (
    Lead, SourceExhaustionTracker, ExclusionRule, OutreachLog, WeeklyReport,
    EmailCampaign, SmtpConnection, EmailTemplate, LeadList, LeadType, LeadSource,
)


def dashboard(request):
    now = timezone.now()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_leads = Lead.objects.count()
    leads_today = Lead.objects.filter(created_at__date=today).count()
    leads_this_week = Lead.objects.filter(created_at__gte=week_ago).count()

    emailed = Lead.objects.filter(email_sent=True).count()
    forms_filled = Lead.objects.filter(form_filled=True).count()
    replies = Lead.objects.filter(replied=True).count()
    interested = Lead.objects.filter(interested=True).count()
    closed = Lead.objects.filter(closed=True).count()

    total_mrr = Lead.objects.filter(closed=True).aggregate(
        total=Sum('revenue_monthly')
    )['total'] or 0

    reply_rate = (replies / emailed * 100) if emailed else 0
    close_rate = (closed / total_leads * 100) if total_leads else 0

    # Funnel data
    qualified = Lead.objects.filter(score__gte=40).count()
    funnel = [
        {'label': 'Leads Scraped', 'count': total_leads, 'color': '#22c55e'},
        {'label': 'Qualified (score 40+)', 'count': qualified, 'color': '#3b82f6'},
        {'label': 'Emailed', 'count': emailed, 'color': '#a855f7'},
        {'label': 'Form Filled', 'count': forms_filled, 'color': '#06b6d4'},
        {'label': 'Replied', 'count': replies, 'color': '#f97316'},
        {'label': 'Interested', 'count': interested, 'color': '#eab308'},
        {'label': 'Closed', 'count': closed, 'color': '#22c55e'},
    ]

    # By country (top 10)
    by_country = (
        Lead.objects.values('country')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')[:10]
    )

    # By lead type
    by_lead_type = (
        Lead.objects.values('lead_type')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # By source
    by_source = (
        Lead.objects.values('source')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Active exclusion rules
    active_exclusions = ExclusionRule.objects.filter(is_active=True, overridden=False)

    # Exhausted sources
    exhausted_sources = SourceExhaustionTracker.objects.filter(status='exhausted').count()
    active_sources = SourceExhaustionTracker.objects.filter(status='active').count()

    # Leads needing follow-up
    followup_due = Lead.objects.filter(
        next_followup_at__lte=now,
        sequence_stage__lt=4,
        replied=False,
        email_sent=True,
    ).count()

    # Recent leads
    recent_leads = Lead.objects.all()[:20]

    # Daily lead counts (last 30 days)
    daily_leads = (
        Lead.objects.filter(created_at__gte=month_ago)
        .annotate(date=TruncDate('created_at'))
        .values('date')
        .annotate(count=Count('id'))
        .order_by('date')
    )

    context = {
        'total_leads': total_leads,
        'leads_today': leads_today,
        'leads_this_week': leads_this_week,
        'emailed': emailed,
        'forms_filled': forms_filled,
        'replies': replies,
        'interested': interested,
        'closed': closed,
        'total_mrr': total_mrr,
        'reply_rate': reply_rate,
        'close_rate': close_rate,
        'funnel': funnel,
        'by_country': by_country,
        'by_lead_type': by_lead_type,
        'by_source': by_source,
        'active_exclusions': active_exclusions,
        'exhausted_sources': exhausted_sources,
        'active_sources': active_sources,
        'followup_due': followup_due,
        'recent_leads': recent_leads,
        'daily_leads': json.dumps(
            [{'date': str(d['date']), 'count': d['count']} for d in daily_leads]
        ),
    }
    return render(request, 'leads/dashboard.html', context)


def lead_list(request):
    leads = Lead.objects.all()

    # Filters
    country = request.GET.get('country')
    lead_type = request.GET.get('lead_type')
    source = request.GET.get('source')
    status = request.GET.get('status')
    search = request.GET.get('q')
    min_score = request.GET.get('min_score')

    if country:
        leads = leads.filter(country=country)
    if lead_type:
        leads = leads.filter(lead_type=lead_type)
    if source:
        leads = leads.filter(source=source)
    if status == 'replied':
        leads = leads.filter(replied=True)
    elif status == 'interested':
        leads = leads.filter(interested=True)
    elif status == 'closed':
        leads = leads.filter(closed=True)
    elif status == 'not_contacted':
        leads = leads.filter(email_sent=False, form_filled=False)
    if search:
        leads = leads.filter(
            Q(company_name__icontains=search) |
            Q(company_domain__icontains=search) |
            Q(contact_name__icontains=search) |
            Q(contact_email__icontains=search)
        )
    if min_score:
        leads = leads.filter(score__gte=int(min_score))

    countries = Lead.objects.values_list('country', flat=True).distinct().order_by('country')

    context = {
        'leads': leads[:200],
        'total_count': leads.count(),
        'countries': countries,
        'lead_types': LeadType.choices,
        'sources': LeadSource.choices,
        'filters': {
            'country': country or '',
            'lead_type': lead_type or '',
            'source': source or '',
            'status': status or '',
            'q': search or '',
            'min_score': min_score or '',
        },
    }
    return render(request, 'leads/lead_list.html', context)


def lead_detail(request, pk):
    lead = get_object_or_404(Lead, pk=pk)
    outreach_logs = lead.outreach_logs.all()
    context = {
        'lead': lead,
        'outreach_logs': outreach_logs,
    }
    return render(request, 'leads/lead_detail.html', context)


def intelligence(request):
    # Country performance
    country_stats = (
        Lead.objects.values('country')
        .annotate(
            total=Count('id'),
            emailed=Count('id', filter=Q(email_sent=True)),
            replied_count=Count('id', filter=Q(replied=True)),
            interested_count=Count('id', filter=Q(interested=True)),
            closed_count=Count('id', filter=Q(closed=True)),
            revenue=Sum('revenue_monthly', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Lead type performance
    type_stats = (
        Lead.objects.values('lead_type')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
            revenue=Sum('revenue_monthly', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Source performance
    source_stats = (
        Lead.objects.values('source')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Exclusion rules
    exclusions = ExclusionRule.objects.all()

    # Exhaustion tracker
    exhaustion = SourceExhaustionTracker.objects.all()[:50]

    # Recent reports
    reports = WeeklyReport.objects.all()[:10]

    context = {
        'country_stats': country_stats,
        'type_stats': type_stats,
        'source_stats': source_stats,
        'exclusions': exclusions,
        'exhaustion': exhaustion,
        'reports': reports,
    }
    return render(request, 'leads/intelligence.html', context)


@require_POST
def toggle_exclusion(request, pk):
    rule = get_object_or_404(ExclusionRule, pk=pk)
    rule.overridden = not rule.overridden
    rule.save()
    return redirect('intelligence')


def form_filling(request):
    """Contact Form Filling page - tracks form submissions to company websites."""
    total_leads = Lead.objects.count()
    has_form = Lead.objects.filter(has_contact_form=True).count()
    no_form = Lead.objects.filter(has_contact_form=False).count()
    forms_filled = Lead.objects.filter(form_filled=True).count()
    forms_pending = Lead.objects.filter(has_contact_form=True, form_filled=False, score__gte=40).count()
    forms_replied = Lead.objects.filter(form_filled=True, replied=True).count()
    forms_interested = Lead.objects.filter(form_filled=True, interested=True).count()
    forms_closed = Lead.objects.filter(form_filled=True, closed=True).count()

    form_reply_rate = (forms_replied / forms_filled * 100) if forms_filled else 0

    # Form fills by country
    by_country = (
        Lead.objects.filter(form_filled=True)
        .values('country')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')[:10]
    )

    # Form fills by lead type
    by_lead_type = (
        Lead.objects.filter(form_filled=True)
        .values('lead_type')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Recent form submissions
    recent_forms = Lead.objects.filter(form_filled=True).order_by('-updated_at')[:20]

    # Pending form fills (qualified leads with forms not yet filled)
    pending_fills = Lead.objects.filter(
        has_contact_form=True, form_filled=False, score__gte=40
    ).order_by('-score')[:20]

    # Form outreach logs
    form_logs = OutreachLog.objects.filter(channel='form').order_by('-sent_at')[:30]

    context = {
        'total_leads': total_leads,
        'has_form': has_form,
        'no_form': no_form,
        'forms_filled': forms_filled,
        'forms_pending': forms_pending,
        'forms_replied': forms_replied,
        'forms_interested': forms_interested,
        'forms_closed': forms_closed,
        'form_reply_rate': form_reply_rate,
        'by_country': by_country,
        'by_lead_type': by_lead_type,
        'recent_forms': recent_forms,
        'pending_fills': pending_fills,
        'form_logs': form_logs,
    }
    return render(request, 'leads/form_filling.html', context)


def email_outreach(request):
    """Redirect to email dashboard."""
    return redirect('email_dashboard')


def email_dashboard(request):
    """Email section - Dashboard. All stats from OutreachLog + EmailCampaign (real data)."""
    email_logs = OutreachLog.objects.filter(channel='email')

    # Real counts from OutreachLog — each unique lead counted once
    sent = email_logs.filter(status__in=['sent', 'opened', 'replied']).values('lead').distinct().count()
    # Opened: from tracking pixel (OutreachLog status) OR opened_at set OR Lead.email_opened flag
    opened_from_logs = email_logs.filter(
        Q(status='opened') | Q(opened_at__isnull=False)
    ).values('lead').distinct().count()
    opened_from_leads = Lead.objects.filter(email_opened=True).count()
    opened = max(opened_from_logs, opened_from_leads)
    replied_count = email_logs.filter(status='replied').values('lead').distinct().count()
    bounced = email_logs.filter(status='bounced').values('lead').distinct().count()
    failed = email_logs.filter(status='failed').values('lead').distinct().count()

    # Interested / Closed still come from Lead flags (set manually by user)
    interested = Lead.objects.filter(interested=True).count()
    closed = Lead.objects.filter(closed=True).count()

    # Pending = leads assigned to any campaign's lead list that haven't been emailed yet
    sent_lead_ids = email_logs.values_list('lead_id', flat=True).distinct()
    campaign_list_ids = EmailCampaign.objects.exclude(
        lead_list__isnull=True
    ).values_list('lead_list_id', flat=True)
    pending = Lead.objects.filter(
        lead_lists__in=campaign_list_ids, contact_email__gt=''
    ).exclude(pk__in=sent_lead_ids).distinct().count()

    # Campaign-level aggregates
    campaign_agg = EmailCampaign.objects.aggregate(
        total_sent=Sum('total_sent'),
        total_opened=Sum('total_opened'),
        total_replied=Sum('total_replied'),
        total_bounced=Sum('total_bounced'),
    )
    camp_sent = campaign_agg['total_sent'] or 0
    camp_opened = campaign_agg['total_opened'] or 0
    camp_replied = campaign_agg['total_replied'] or 0

    # Use whichever is larger (OutreachLog or campaign sum) so nothing is undercounted
    sent = max(sent, camp_sent)
    opened = max(opened, camp_opened)

    open_rate = round(opened / sent * 100, 1) if sent else 0
    reply_rate = round(replied_count / sent * 100, 1) if sent else 0
    bounce_rate = round(bounced / sent * 100, 1) if sent else 0

    campaigns = EmailCampaign.objects.all().order_by('-created_at')[:10]

    # Recent replies — from OutreachLog for accurate timestamps
    recent_reply_logs = email_logs.filter(status='replied').select_related('lead').order_by('-replied_at')[:10]
    recent_replies = [log.lead for log in recent_reply_logs]
    # Fallback to Lead flags if no OutreachLog replies recorded yet
    if not recent_replies:
        recent_replies = Lead.objects.filter(replied=True).order_by('-updated_at')[:10]

    # Daily delivery breakdown for line chart (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    daily_stats = (
        email_logs.filter(sent_at__gte=thirty_days_ago)
        .annotate(day=TruncDate('sent_at'))
        .values('day')
        .annotate(
            sent_count=Count('id', filter=Q(status__in=['sent', 'opened', 'replied'])),
            opened_count=Count('id', filter=Q(status='opened')),
            replied_count=Count('id', filter=Q(status='replied')),
            bounced_count=Count('id', filter=Q(status='bounced')),
            failed_count=Count('id', filter=Q(status='failed')),
        )
        .order_by('day')
    )
    chart_labels = [d['day'].strftime('%b %d') for d in daily_stats]
    chart_sent = [d['sent_count'] for d in daily_stats]
    chart_opened = [d['opened_count'] for d in daily_stats]
    chart_replied = [d['replied_count'] for d in daily_stats]
    chart_bounced = [d['bounced_count'] for d in daily_stats]
    chart_failed = [d['failed_count'] for d in daily_stats]
    context = {
        'active_tab': 'dashboard',
        'sent': sent,
        'pending': pending,
        'opened': opened,
        'replied': replied_count,
        'interested': interested,
        'closed': closed,
        'bounced': bounced,
        'failed': failed,
        'open_rate': open_rate,
        'reply_rate': reply_rate,
        'bounce_rate': bounce_rate,
        'campaigns': campaigns,
        'recent_replies': recent_replies,
        'chart_labels': json.dumps(chart_labels),
        'chart_sent': json.dumps(chart_sent),
        'chart_opened': json.dumps(chart_opened),
        'chart_replied': json.dumps(chart_replied),
        'chart_bounced': json.dumps(chart_bounced),
        'chart_failed': json.dumps(chart_failed),
    }
    return render(request, 'leads/email/dashboard.html', context)


def email_campaigns(request):
    """Email section - Campaigns list."""
    campaigns = EmailCampaign.objects.all()
    context = {'active_tab': 'campaigns', 'campaigns': campaigns}
    return render(request, 'leads/email/campaigns.html', context)


def email_leads(request):
    """Email section - Lead lists."""
    lead_lists = LeadList.objects.all()
    if request.method == 'POST':
        name = request.POST.get('name', 'Untitled List')
        description = request.POST.get('description', '')
        ll = LeadList.objects.create(name=name, description=description)
        # Auto-populate from filters
        country = request.POST.get('country', '')
        lead_type = request.POST.get('lead_type', '')
        min_score = int(request.POST.get('min_score', 40))
        leads_qs = Lead.objects.filter(score__gte=min_score, contact_email__gt='')
        if country:
            leads_qs = leads_qs.filter(country=country)
        if lead_type:
            leads_qs = leads_qs.filter(lead_type=lead_type)
        ll.leads.set(leads_qs[:1000])
        return redirect('email_leads')

    # Annotate lists with stats
    lead_lists = lead_lists.annotate(
        total_leads=Count('leads'),
        processed=Count('leads', filter=Q(leads__email_sent=True) | Q(leads__form_filled=True)),
        unprocessed=Count('leads', filter=Q(leads__email_sent=False, leads__form_filled=False)),
    )

    countries = Lead.objects.values_list('country', flat=True).distinct().order_by('country')
    context = {
        'active_tab': 'leads',
        'lead_lists': lead_lists,
        'countries': countries,
        'lead_types': LeadType.choices,
        'sources': LeadSource.choices,
    }
    return render(request, 'leads/email/leads.html', context)


def email_leads_upload(request):
    """Upload CSV to create leads and add them to a lead list."""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        list_id = request.POST.get('lead_list')

        if not csv_file or not list_id:
            return redirect('email_leads')

        lead_list = get_object_or_404(LeadList, pk=int(list_id))

        decoded = csv_file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(decoded))

        created_count = 0
        skipped_count = 0

        for row in reader:
            # Normalize CSV column names (case-insensitive, strip spaces)
            cleaned = {k.strip().lower().replace(' ', '_'): v.strip() for k, v in row.items() if k}

            # Try to find domain from various possible columns
            domain = (
                cleaned.get('company_domain', '')
                or cleaned.get('domain', '')
                or cleaned.get('website', '').replace('https://', '').replace('http://', '').split('/')[0]
                or cleaned.get('website_url', '').replace('https://', '').replace('http://', '').split('/')[0]
                or cleaned.get('email', '').split('@')[-1] if cleaned.get('email') else ''
            )
            domain = domain.lower().strip()

            if not domain:
                skipped_count += 1
                continue

            # Dedup check
            lead, was_created = Lead.objects.get_or_create(
                company_domain=domain,
                defaults={
                    'company_name': cleaned.get('company_name', '') or cleaned.get('company', '') or domain,
                    'contact_name': (
                        cleaned.get('contact_name', '')
                        or cleaned.get('name', '')
                        or f"{cleaned.get('first_name', '')} {cleaned.get('last_name', '')}".strip()
                        or cleaned.get('firstname', '')
                    ),
                    'contact_email': cleaned.get('contact_email', '') or cleaned.get('email', ''),
                    'contact_phone': cleaned.get('contact_phone', '') or cleaned.get('phone', ''),
                    'website_url': cleaned.get('website_url', '') or cleaned.get('website', ''),
                    'country': cleaned.get('country', ''),
                    'city': cleaned.get('city', ''),
                    'lead_type': cleaned.get('lead_type', 'voip_provider'),
                    'source': cleaned.get('source', 'linkedin'),
                    'keyword_used': cleaned.get('keyword_used', '') or cleaned.get('keyword', ''),
                    'company_size': cleaned.get('company_size', ''),
                    'score': int(cleaned.get('score', 50) or 50),
                },
            )

            lead_list.leads.add(lead)
            if was_created:
                created_count += 1
            else:
                skipped_count += 1

        return redirect('email_leads_detail', pk=lead_list.pk)

    return redirect('email_leads')


def email_leads_detail(request, pk):
    """View leads inside a specific lead list."""
    lead_list = get_object_or_404(LeadList, pk=pk)
    leads = lead_list.leads.all()

    # Filters
    search = request.GET.get('q', '')
    country = request.GET.get('country', '')
    if search:
        leads = leads.filter(
            Q(company_name__icontains=search) |
            Q(company_domain__icontains=search) |
            Q(contact_name__icontains=search) |
            Q(contact_email__icontains=search)
        )
    if country:
        leads = leads.filter(country=country)

    countries = lead_list.leads.values_list('country', flat=True).distinct().order_by('country')

    context = {
        'active_tab': 'leads',
        'lead_list': lead_list,
        'leads': leads[:200],
        'total_count': leads.count(),
        'countries': countries,
        'filters': {'q': search, 'country': country},
    }
    return render(request, 'leads/email/leads_detail.html', context)


@require_POST
def email_leads_add_manual(request):
    """Manually add a single lead to a lead list."""
    list_id = request.POST.get('lead_list')
    if not list_id:
        return redirect('email_leads')
    lead_list = get_object_or_404(LeadList, pk=int(list_id))
    domain = request.POST.get('company_domain', '').lower().strip()
    if not domain:
        return redirect('email_leads')
    lead, _ = Lead.objects.get_or_create(
        company_domain=domain,
        defaults={
            'company_name': request.POST.get('company_name', '') or domain,
            'contact_name': request.POST.get('contact_name', ''),
            'contact_email': request.POST.get('contact_email', ''),
            'contact_phone': request.POST.get('contact_phone', ''),
            'country': request.POST.get('country', ''),
            'city': request.POST.get('city', ''),
            'lead_type': request.POST.get('lead_type', 'voip_provider'),
            'score': 50,
        },
    )
    lead_list.leads.add(lead)
    return redirect('email_leads_detail', pk=lead_list.pk)


@require_POST
def email_leads_delete(request, pk):
    get_object_or_404(LeadList, pk=pk).delete()
    return redirect('email_leads')


@require_POST
def email_leads_delete_selected(request, pk):
    """Remove selected leads from a lead list."""
    lead_list = get_object_or_404(LeadList, pk=pk)
    lead_ids = request.POST.getlist('lead_ids')
    if lead_ids:
        lead_list.leads.filter(pk__in=lead_ids).delete()
    return redirect('email_leads_detail', pk=pk)


def email_templates(request):
    """Email section - Templates."""
    templates = EmailTemplate.objects.all()
    context = {'active_tab': 'templates', 'templates': templates}
    return render(request, 'leads/email/templates.html', context)


def email_template_create(request):
    """Create a new email template."""
    if request.method == 'POST':
        EmailTemplate.objects.create(
            name=request.POST.get('name', ''),
            subject=request.POST.get('subject', ''),
            body=request.POST.get('body', ''),
        )
        return redirect('email_templates')
    context = {'active_tab': 'templates'}
    return render(request, 'leads/email/template_create.html', context)


def email_template_edit(request, pk):
    """Edit an existing email template."""
    template = get_object_or_404(EmailTemplate, pk=pk)
    if request.method == 'POST':
        template.name = request.POST.get('name', template.name)
        template.subject = request.POST.get('subject', template.subject)
        template.body = request.POST.get('body', template.body)
        template.save()
        return redirect('email_templates')
    context = {'active_tab': 'templates', 'template': template}
    return render(request, 'leads/email/template_edit.html', context)


@require_POST
def email_template_delete(request, pk):
    get_object_or_404(EmailTemplate, pk=pk).delete()
    return redirect('email_templates')


def email_smtp(request):
    """Email section - SMTP Settings."""
    connections = SmtpConnection.objects.all()
    context = {'active_tab': 'smtp', 'connections': connections}
    return render(request, 'leads/email/smtp.html', context)


def email_smtp_create(request):
    """Create a new SMTP connection."""
    if request.method == 'POST':
        SmtpConnection.objects.create(
            name=request.POST.get('name', ''),
            host=request.POST.get('host', ''),
            port=int(request.POST.get('port', 587)),
            username=request.POST.get('username', ''),
            password=request.POST.get('password', ''),
            use_tls=request.POST.get('use_tls') == 'on',
            from_email=request.POST.get('from_email', ''),
            from_name=request.POST.get('from_name', ''),
            daily_limit=int(request.POST.get('daily_limit', 100)),
        )
        return redirect('email_smtp')
    context = {'active_tab': 'smtp'}
    return render(request, 'leads/email/smtp_create.html', context)


@require_POST
def email_smtp_delete(request, pk):
    get_object_or_404(SmtpConnection, pk=pk).delete()
    return redirect('email_smtp')


def email_warmup(request):
    """Email section - Warmup."""
    connections = SmtpConnection.objects.filter(is_active=True)
    context = {'active_tab': 'warmup', 'connections': connections}
    return render(request, 'leads/email/warmup.html', context)


def email_reports(request):
    """Email section - Reports."""
    campaigns = EmailCampaign.objects.all()
    total_sent = sum(c.total_sent for c in campaigns)
    total_opened = sum(c.total_opened for c in campaigns)
    total_replied = sum(c.total_replied for c in campaigns)
    total_bounced = sum(c.total_bounced for c in campaigns)

    context = {
        'active_tab': 'reports',
        'campaigns': campaigns,
        'total_sent': total_sent,
        'total_opened': total_opened,
        'total_replied': total_replied,
        'total_bounced': total_bounced,
        'open_rate': round(total_opened / total_sent * 100, 1) if total_sent else 0,
        'reply_rate': round(total_replied / total_sent * 100, 1) if total_sent else 0,
    }
    return render(request, 'leads/email/reports.html', context)


def email_replies(request):
    """Email section - Reply Reports."""
    replied_leads = Lead.objects.filter(replied=True).order_by('-updated_at')
    by_country = (
        replied_leads.values('country')
        .annotate(total=Count('id'), interested_count=Count('id', filter=Q(interested=True)), closed_count=Count('id', filter=Q(closed=True)))
        .order_by('-total')
    )
    context = {
        'active_tab': 'replies',
        'replied_leads': replied_leads[:50],
        'total_replies': replied_leads.count(),
        'by_country': by_country,
    }
    return render(request, 'leads/email/replies.html', context)


def campaign_create(request):
    """Create a new email campaign."""
    if request.method == 'POST':
        lead_list_id = request.POST.get('lead_list')
        template_id = request.POST.get('template')
        smtp_id = request.POST.get('smtp_connection')
        scheduled_at = request.POST.get('scheduled_at') or None

        campaign = EmailCampaign.objects.create(
            name=request.POST.get('name', 'Untitled Campaign'),
            description=request.POST.get('description', ''),
            subject=request.POST.get('subject', ''),
            body=request.POST.get('body', ''),
            send_option=request.POST.get('send_option', 'now'),
            scheduled_at=scheduled_at,
            lead_list_id=int(lead_list_id) if lead_list_id else None,
            template_id=int(template_id) if template_id else None,
            smtp_connection_id=int(smtp_id) if smtp_id else None,
            cc=request.POST.get('cc', ''),
            bcc=request.POST.get('bcc', ''),
        )

        if campaign.lead_list:
            campaign.total_recipients = campaign.lead_list.leads.count()
            campaign.save(update_fields=['total_recipients'])

        return redirect('campaign_detail', pk=campaign.pk)

    context = {
        'lead_lists': LeadList.objects.all(),
        'templates': EmailTemplate.objects.all(),
        'smtp_connections': SmtpConnection.objects.filter(is_active=True),
    }
    return render(request, 'leads/campaign_create.html', context)


def campaign_detail(request, pk):
    """View campaign details and stats."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)

    lead_list_leads = campaign.lead_list.leads.all() if campaign.lead_list else Lead.objects.none()
    leads_count = lead_list_leads.count()

    # Compute real stats from OutreachLog for this campaign's leads
    campaign_logs = OutreachLog.objects.filter(
        lead__in=lead_list_leads, channel='email'
    )
    real_sent = campaign_logs.filter(status__in=['sent', 'opened', 'replied']).values('lead').distinct().count()
    real_opened = campaign_logs.filter(
        Q(status='opened') | Q(opened_at__isnull=False)
    ).values('lead').distinct().count()
    real_replied = campaign_logs.filter(status='replied').values('lead').distinct().count()
    real_bounced = campaign_logs.filter(status='bounced').values('lead').distinct().count()

    # Sync campaign model with real data
    campaign.total_sent = real_sent
    campaign.total_opened = real_opened
    campaign.total_replied = real_replied
    campaign.total_bounced = real_bounced
    campaign.save(update_fields=['total_sent', 'total_opened', 'total_replied', 'total_bounced'])

    # By country
    by_country = (
        lead_list_leads.values('country')
        .annotate(
            total=Count('id'),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')[:10]
    )

    context = {
        'campaign': campaign,
        'leads_count': leads_count,
        'by_country': by_country,
        'campaign_logs': campaign_logs.order_by('-sent_at')[:30],
        'recent_leads': lead_list_leads[:20],
    }
    return render(request, 'leads/campaign_detail.html', context)


def campaign_edit(request, pk):
    """Edit an existing campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    if request.method == 'POST':
        campaign.name = request.POST.get('name', campaign.name)
        campaign.description = request.POST.get('description', '')
        campaign.subject = request.POST.get('subject', campaign.subject)
        campaign.body = request.POST.get('body', campaign.body)
        campaign.send_option = request.POST.get('send_option', 'now')
        campaign.scheduled_at = request.POST.get('scheduled_at') or None
        lead_list_id = request.POST.get('lead_list')
        template_id = request.POST.get('template')
        smtp_id = request.POST.get('smtp_connection')
        campaign.lead_list_id = int(lead_list_id) if lead_list_id else None
        campaign.template_id = int(template_id) if template_id else None
        campaign.smtp_connection_id = int(smtp_id) if smtp_id else None
        campaign.cc = request.POST.get('cc', '')
        campaign.bcc = request.POST.get('bcc', '')
        campaign.save()
        return redirect('campaign_detail', pk=campaign.pk)

    context = {
        'campaign': campaign,
        'lead_lists': LeadList.objects.all(),
        'templates': EmailTemplate.objects.all(),
        'smtp_connections': SmtpConnection.objects.filter(is_active=True),
    }
    return render(request, 'leads/campaign_edit.html', context)


@require_POST
def campaign_action(request, pk):
    """Send, pause, or delete a campaign."""
    campaign = get_object_or_404(EmailCampaign, pk=pk)
    action = request.POST.get('action')

    if action == 'send':
        campaign.status = 'sending'
        campaign.save(update_fields=['status'])
        # Dispatch actual email sending — try Celery, fall back to a thread
        from .tasks import send_campaign_emails, _run_campaign_send
        try:
            send_campaign_emails.delay(campaign.pk)
        except Exception:
            t = threading.Thread(target=_run_campaign_send, args=(campaign.pk,), daemon=True)
            t.start()
    elif action == 'pause':
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
    elif action == 'resume':
        campaign.status = 'sending'
        campaign.save(update_fields=['status'])
    elif action == 'delete':
        campaign.delete()
        return redirect('email_outreach')

    return redirect('campaign_detail', pk=campaign.pk)


def track_open(request, log_id):
    """Serve a 1×1 tracking pixel and mark the OutreachLog as opened."""
    from django.http import HttpResponse
    from django.db.models import F
    try:
        log = OutreachLog.objects.get(pk=log_id)
        if log.status == 'sent':
            log.status = 'opened'
            log.opened_at = timezone.now()
            log.save(update_fields=['status', 'opened_at'])
            log.lead.email_opened = True
            log.lead.save(update_fields=['email_opened'])
            # Update campaign stats
            EmailCampaign.objects.filter(
                lead_list__leads=log.lead
            ).update(total_opened=F('total_opened') + 1)
    except OutreachLog.DoesNotExist:
        pass
    # 1×1 transparent GIF
    gif = base64.b64decode(
        'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7'
    )
    return HttpResponse(gif, content_type='image/gif')


def leads_pipeline(request):
    """Leads Pipeline page - full funnel view from scrape to close."""
    total = Lead.objects.count()
    qualified = Lead.objects.filter(score__gte=40).count()
    contacted = Lead.objects.filter(Q(email_sent=True) | Q(form_filled=True)).count()
    replied_count = Lead.objects.filter(replied=True).count()
    interested_count = Lead.objects.filter(interested=True).count()
    closed_count = Lead.objects.filter(closed=True).count()
    total_mrr = Lead.objects.filter(closed=True).aggregate(t=Sum('revenue_monthly'))['t'] or 0

    # Pipeline stages
    new_leads = Lead.objects.filter(email_sent=False, form_filled=False).count()
    in_sequence = Lead.objects.filter(email_sent=True, replied=False, sequence_stage__lt=4).count()
    sequence_done = Lead.objects.filter(email_sent=True, replied=False, sequence_stage__gte=4).count()

    # Funnel
    funnel = [
        {'label': 'Total Scraped', 'count': total, 'color': '#22c55e', 'pct': 100},
        {'label': 'Qualified (40+)', 'count': qualified, 'color': '#3b82f6', 'pct': round(qualified / total * 100) if total else 0},
        {'label': 'Contacted', 'count': contacted, 'color': '#a855f7', 'pct': round(contacted / total * 100) if total else 0},
        {'label': 'Replied', 'count': replied_count, 'color': '#f97316', 'pct': round(replied_count / total * 100) if total else 0},
        {'label': 'Interested', 'count': interested_count, 'color': '#eab308', 'pct': round(interested_count / total * 100) if total else 0},
        {'label': 'Closed Won', 'count': closed_count, 'color': '#22c55e', 'pct': round(closed_count / total * 100, 1) if total else 0},
    ]

    # By country pipeline
    by_country = (
        Lead.objects.values('country')
        .annotate(
            total=Count('id'),
            qualified=Count('id', filter=Q(score__gte=40)),
            contacted=Count('id', filter=Q(email_sent=True) | Q(form_filled=True)),
            replied_count=Count('id', filter=Q(replied=True)),
            interested_count=Count('id', filter=Q(interested=True)),
            closed_count=Count('id', filter=Q(closed=True)),
            revenue=Sum('revenue_monthly', filter=Q(closed=True)),
        )
        .order_by('-total')[:15]
    )

    # By lead type pipeline
    by_lead_type = (
        Lead.objects.values('lead_type')
        .annotate(
            total=Count('id'),
            contacted=Count('id', filter=Q(email_sent=True) | Q(form_filled=True)),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
            revenue=Sum('revenue_monthly', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # By source pipeline
    by_source = (
        Lead.objects.values('source')
        .annotate(
            total=Count('id'),
            contacted=Count('id', filter=Q(email_sent=True) | Q(form_filled=True)),
            replied_count=Count('id', filter=Q(replied=True)),
            closed_count=Count('id', filter=Q(closed=True)),
        )
        .order_by('-total')
    )

    # Hot leads (replied or interested, not yet closed)
    hot_leads = Lead.objects.filter(
        Q(replied=True) | Q(interested=True), closed=False
    ).order_by('-score')[:15]

    # Recently closed
    recent_closed = Lead.objects.filter(closed=True).order_by('-updated_at')[:10]

    context = {
        'total': total,
        'qualified': qualified,
        'contacted': contacted,
        'replied_count': replied_count,
        'interested_count': interested_count,
        'closed_count': closed_count,
        'total_mrr': total_mrr,
        'new_leads': new_leads,
        'in_sequence': in_sequence,
        'sequence_done': sequence_done,
        'funnel': funnel,
        'by_country': by_country,
        'by_lead_type': by_lead_type,
        'by_source': by_source,
        'hot_leads': hot_leads,
        'recent_closed': recent_closed,
    }
    return render(request, 'leads/leads_pipeline.html', context)


def api_lead_stats(request):
    """JSON endpoint for chart data."""
    total = Lead.objects.count()
    return JsonResponse({
        'total_leads': total,
        'emailed': Lead.objects.filter(email_sent=True).count(),
        'forms_filled': Lead.objects.filter(form_filled=True).count(),
        'replied': Lead.objects.filter(replied=True).count(),
        'interested': Lead.objects.filter(interested=True).count(),
        'closed': Lead.objects.filter(closed=True).count(),
        'mrr': float(
            Lead.objects.filter(closed=True).aggregate(Sum('revenue_monthly'))['revenue_monthly__sum'] or 0
        ),
    })
