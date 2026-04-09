"""
Celery tasks for SalesHunter v2 automated workflows.

These tasks handle:
1. Lead scraping from multiple sources
2. Lead qualification and scoring (via Claude AI)
3. Cold email sending (via Instantly.dev)
4. Contact form filling (via Puppeteer/Playwright)
5. Follow-up sequence management
6. Weekly intelligence reports
7. Auto-exclusion rule evaluation
"""
import hashlib
import logging
import smtplib
import threading
import time
import uuid
from datetime import timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr, formatdate, make_msgid

from celery import shared_task
from django.conf import settings
from django.db.models import Count, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)

WHConfig = settings.SALESHUNTER


# ─── 1. SCRAPING TASKS ──────────────────────────────────────────────

@shared_task(bind=True, max_retries=3)
def scrape_leads_daily(self):
    """
    Master task: scrape 1,000 new unique leads per day.
    Dispatches to individual source scrapers.
    """
    from .models import SourceExhaustionTracker

    active_sources = SourceExhaustionTracker.objects.filter(status='active')
    target = WHConfig['DAILY_SCRAPE_TARGET']

    # Distribute across sources
    tasks = [
        scrape_apollo.s(target // 3),
        scrape_google_search.s(target // 4),
        scrape_google_maps.s(target // 4),
        scrape_directories.s(target // 6),
    ]

    logger.info(f"Starting daily scrape for {target} leads")
    for task in tasks:
        task.apply_async()

    return f"Dispatched scraping tasks for {target} leads"


@shared_task(bind=True, max_retries=3)
def scrape_apollo(self, count):
    """
    Scrape leads from Apollo.io (LinkedIn profiles).
    TODO: Integrate with Apollo.io API.
    """
    from .models import Lead, SourceExhaustionTracker
    from .services.scraper import ApolloScraper

    try:
        scraper = ApolloScraper(api_key=WHConfig['APOLLO_API_KEY'])
        leads_data = scraper.search(count=count)

        added = 0
        for data in leads_data:
            domain = data.get('company_domain', '').lower().strip()
            if not domain:
                continue
            if Lead.objects.filter(company_domain=domain).exists():
                continue  # Dedup check

            Lead.objects.create(
                company_domain=domain,
                company_name=data.get('company_name', ''),
                contact_name=data.get('contact_name', ''),
                contact_email=data.get('contact_email', ''),
                contact_phone=data.get('contact_phone', ''),
                website_url=data.get('website_url', ''),
                country=data.get('country', ''),
                city=data.get('city', ''),
                lead_type=data.get('lead_type', 'voip_provider'),
                source='linkedin',
                keyword_used=data.get('keyword_used', ''),
                company_size=data.get('company_size', ''),
            )
            added += 1

        logger.info(f"Apollo scraper: added {added}/{count} leads")
        return f"Apollo: {added} new leads added"
    except Exception as exc:
        logger.error(f"Apollo scraper failed: {exc}")
        raise self.retry(exc=exc, countdown=60)


@shared_task(bind=True, max_retries=3)
def scrape_google_search(self, count):
    """
    Scrape leads from Google Search results.
    TODO: Integrate with SerpAPI or custom scraper.
    """
    logger.info(f"Google Search scraper: target {count} leads")
    # Placeholder - implement with SerpAPI
    return f"Google Search: placeholder for {count} leads"


@shared_task(bind=True, max_retries=3)
def scrape_google_maps(self, count):
    """
    Scrape leads from Google Maps.
    TODO: Integrate with Google Maps / Places API.
    """
    logger.info(f"Google Maps scraper: target {count} leads")
    # Placeholder - implement with Places API
    return f"Google Maps: placeholder for {count} leads"


@shared_task(bind=True, max_retries=3)
def scrape_directories(self, count):
    """
    Scrape from telecom directories (TeleGeography, ITW, etc).
    TODO: Implement directory scrapers.
    """
    logger.info(f"Directory scraper: target {count} leads")
    return f"Directories: placeholder for {count} leads"


# ─── 2. QUALIFICATION TASKS ─────────────────────────────────────────

@shared_task
def qualify_new_leads():
    """
    Score and tag all unscored leads using Claude AI.
    """
    from .models import Lead

    unscored = Lead.objects.filter(score=0)
    count = unscored.count()

    for lead in unscored[:500]:  # Batch of 500
        score_lead.delay(str(lead.id))

    logger.info(f"Dispatched scoring for {min(count, 500)} leads")
    return f"Queued {min(count, 500)} leads for scoring"


@shared_task(bind=True, max_retries=2)
def score_lead(self, lead_id):
    """
    Score a single lead using Claude AI.
    TODO: Integrate with Claude API for intelligent scoring.
    """
    from .models import Lead, ExclusionRule

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return

    # Check exclusion rules
    excluded = ExclusionRule.objects.filter(
        is_active=True, overridden=False
    )
    for rule in excluded:
        if rule.rule_type == 'country_pause' and rule.dimension_value == lead.country:
            lead.score = 0
            lead.save(update_fields=['score'])
            return f"Lead {lead.company_domain} excluded (country paused)"
        if rule.rule_type == 'type_deprioritize' and rule.dimension_value == lead.lead_type:
            lead.score = max(lead.score - 30, 0)

    # TODO: Replace with Claude API call for intelligent scoring
    # For now, basic rule-based scoring
    score = 50  # Base score
    if lead.contact_email:
        score += 15
    if lead.website_url:
        score += 10
    if lead.lead_type in ('voip_provider', 'call_center', 'ucaas'):
        score += 10
    if lead.contact_phone:
        score += 5
    if lead.company_size == 'enterprise':
        score += 10
    elif lead.company_size == 'medium':
        score += 5

    lead.score = min(score, 100)
    lead.save(update_fields=['score'])
    return f"Scored {lead.company_domain}: {lead.score}"


# ─── 3. EMAIL OUTREACH TASKS ────────────────────────────────────────

@shared_task
def send_daily_emails():
    """
    Send cold emails to qualified leads that haven't been emailed yet.
    """
    from .models import Lead

    leads = Lead.objects.filter(
        email_sent=False,
        score__gte=WHConfig['MIN_LEAD_SCORE'],
        contact_email__isnull=False,
    ).exclude(contact_email='').order_by('-score')[:WHConfig['DAILY_EMAIL_TARGET']]

    count = 0
    for lead in leads:
        send_email_to_lead.delay(str(lead.id), sequence_stage=1)
        count += 1

    logger.info(f"Dispatched {count} emails")
    return f"Queued {count} emails for sending"


@shared_task(bind=True, max_retries=2)
def send_email_to_lead(self, lead_id, sequence_stage=1):
    """
    Send a personalized email to a single lead via Instantly.dev.
    TODO: Integrate with Instantly.dev API.
    """
    from .models import Lead, OutreachLog

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return

    # Generate email content based on stage
    subjects = {
        1: f"{lead.contact_name or 'Hi'}, premium voice routes to {lead.country} - free test",
        2: f"High ASR CLI routes to {lead.country} - Rozper quality guarantee",
        3: f"Rozper carries millions of minutes monthly - see for yourself",
        4: f"Last note - free test offer still open",
    }
    subject = subjects.get(sequence_stage, subjects[1])

    # TODO: Use Claude API to generate personalized email body
    # TODO: Send via Instantly.dev API

    # Log the outreach
    OutreachLog.objects.create(
        lead=lead,
        channel='email',
        sequence_stage=sequence_stage,
        status='sent',
        subject=subject,
        sending_domain=f"domain{(lead.pk.int % WHConfig['SENDING_DOMAINS_COUNT']) + 1}.rozper.com",
    )

    lead.email_sent = True
    lead.sequence_stage = sequence_stage
    lead.last_contacted_at = timezone.now()

    # Set next follow-up
    followup_days = WHConfig['FOLLOW_UP_DAYS']
    if sequence_stage < len(followup_days):
        days_until_next = followup_days[sequence_stage] - followup_days[sequence_stage - 1] if sequence_stage > 0 else followup_days[0]
        lead.next_followup_at = timezone.now() + timedelta(days=days_until_next)

    lead.save()
    return f"Email #{sequence_stage} sent to {lead.company_domain}"


def _run_campaign_send(campaign_id):
    """
    Core SMTP sending logic — runs in the Celery worker or a fallback thread.
    Iterates through leads in the campaign's lead list and sends each one
    an email via the campaign's configured SmtpConnection.
    """
    from .models import EmailCampaign, OutreachLog, SmtpConnection
    from django.conf import settings as django_settings

    site_url = getattr(django_settings, 'SITE_URL', 'http://localhost:8000').rstrip('/')

    try:
        campaign = EmailCampaign.objects.get(pk=campaign_id)
    except EmailCampaign.DoesNotExist:
        return

    if not campaign.lead_list:
        campaign.status = 'sent'
        campaign.save(update_fields=['status'])
        return

    # Resolve SMTP connection
    smtp_cfg = campaign.smtp_connection
    if not smtp_cfg:
        smtp_cfg = SmtpConnection.objects.filter(is_active=True).first()
    if not smtp_cfg:
        logger.error("Campaign %s: no active SMTP connection configured.", campaign_id)
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
        return

    leads = campaign.lead_list.leads.filter(
        contact_email__isnull=False
    ).exclude(contact_email='')

    campaign.total_recipients = leads.count()
    campaign.save(update_fields=['total_recipients'])

    from_addr = formataddr((smtp_cfg.from_name, smtp_cfg.from_email)) if smtp_cfg.from_name else smtp_cfg.from_email
    from_domain = smtp_cfg.from_email.split('@')[-1]
    sent_count = 0

    try:
        if smtp_cfg.port == 465:
            server = smtplib.SMTP_SSL(smtp_cfg.host, smtp_cfg.port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_cfg.host, smtp_cfg.port, timeout=30)
            if smtp_cfg.use_tls:
                server.starttls()

        server.login(smtp_cfg.username, smtp_cfg.password)
    except smtplib.SMTPException as exc:
        logger.error("Campaign %s: SMTP connection failed — %s", campaign_id, exc)
        campaign.status = 'paused'
        campaign.save(update_fields=['status'])
        return

    try:
        for lead in leads:
            # Respect pause requests between sends
            campaign.refresh_from_db(fields=['status'])
            if campaign.status == 'paused':
                break

            subject = campaign.render_subject(lead)
            body = campaign.render_body(lead)

            # Create the OutreachLog first so we have its PK for the tracking pixel
            log = OutreachLog.objects.create(
                lead=lead,
                channel='email',
                sequence_stage=1,
                status='sent',
                subject=subject,
                message_body=body,
                sending_domain=from_domain,
            )

            # ── Build a proper email that won't be flagged as spam ──

            # Convert plain text to clean HTML (no <pre>, proper paragraphs)
            paragraphs = body.strip().split('\n\n')
            html_parts = []
            for p in paragraphs:
                lines = p.strip().replace('\n', '<br>')
                html_parts.append(f'<p style="margin:0 0 12px 0;line-height:1.6;">{lines}</p>')
            html_inner = ''.join(html_parts)

            # Only add tracking pixel if SITE_URL is not localhost
            pixel_tag = ''
            if 'localhost' not in site_url and '127.0.0.1' not in site_url:
                pixel_url = f"{site_url}/track/open/{log.pk}/"
                pixel_tag = f'<img src="{pixel_url}" width="1" height="1" alt="" style="display:none">'

            # Unsubscribe link (helps deliverability even if placeholder)
            unsub_line = (
                '<p style="margin-top:20px;font-size:11px;color:#999;">'
                'If you prefer not to receive further emails, simply reply with "unsubscribe".</p>'
            )

            html_body = (
                '<!DOCTYPE html>'
                '<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>'
                f'<body style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#333;'
                f'max-width:600px;margin:0 auto;padding:20px;">'
                f'{html_inner}'
                f'{unsub_line}'
                f'{pixel_tag}'
                f'</body></html>'
            )

            msg = MIMEMultipart('alternative')

            # ── Required headers to avoid spam ──
            msg['Subject'] = subject
            msg['From'] = from_addr
            msg['To'] = formataddr((lead.contact_name or '', lead.contact_email))
            msg['Reply-To'] = smtp_cfg.from_email
            msg['Message-ID'] = make_msgid(domain=from_domain)
            msg['Date'] = formatdate(localtime=True)
            msg['MIME-Version'] = '1.0'
            msg['X-Mailer'] = 'SalesHunter'
            # List-Unsubscribe header (major spam filter signal)
            msg['List-Unsubscribe'] = f'<mailto:{smtp_cfg.from_email}?subject=unsubscribe>'

            if campaign.cc:
                msg['Cc'] = campaign.cc
            if campaign.bcc:
                msg['Bcc'] = campaign.bcc

            # Plain text first, then HTML (proper MIME order)
            plain_part = MIMEText(body + '\n\n---\nTo unsubscribe, reply with "unsubscribe".', 'plain', 'utf-8')
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(plain_part)
            msg.attach(html_part)

            all_recipients = [lead.contact_email]
            if campaign.cc:
                all_recipients += [e.strip() for e in campaign.cc.split(',') if e.strip()]
            if campaign.bcc:
                all_recipients += [e.strip() for e in campaign.bcc.split(',') if e.strip()]

            try:
                server.sendmail(smtp_cfg.from_email, all_recipients, msg.as_string())
                status = 'sent'
                sent_count += 1
            except smtplib.SMTPException as exc:
                logger.error("Failed to send to %s: %s", lead.contact_email, exc)
                status = 'failed'
                log.status = 'failed'
                log.save(update_fields=['status'])

            if status == 'sent':
                lead.email_sent = True
                lead.last_contacted_at = timezone.now()
                lead.save(update_fields=['email_sent', 'last_contacted_at'])
                campaign.total_sent = sent_count
                campaign.save(update_fields=['total_sent'])

            # Throttle: small delay between sends to avoid rate limiting
            time.sleep(2)
    finally:
        try:
            server.quit()
        except Exception:
            pass

    if campaign.status != 'paused':
        campaign.status = 'sent'
        campaign.save(update_fields=['status'])

    logger.info("Campaign %s: sent %d emails.", campaign_id, sent_count)
    return f"Sent {sent_count} emails for campaign {campaign_id}"


@shared_task
def send_campaign_emails(campaign_id):
    """Celery task wrapper for campaign email sending."""
    return _run_campaign_send(campaign_id)


# ─── 4. FORM FILLING TASKS ──────────────────────────────────────────

@shared_task
def fill_daily_forms():
    """
    Fill contact forms on websites of qualified leads.
    """
    from .models import Lead

    leads = Lead.objects.filter(
        form_filled=False,
        has_contact_form=True,
        score__gte=WHConfig['MIN_LEAD_SCORE'],
        website_url__isnull=False,
    ).exclude(website_url='').order_by('-score')[:WHConfig['DAILY_FORM_TARGET']]

    count = 0
    for lead in leads:
        fill_contact_form.delay(str(lead.id))
        count += 1

    logger.info(f"Dispatched {count} form fills")
    return f"Queued {count} contact forms for filling"


@shared_task(bind=True, max_retries=2)
def fill_contact_form(self, lead_id):
    """
    Visit a lead's website, find and fill the contact form.
    TODO: Integrate with Puppeteer/Playwright for browser automation.
    """
    from .models import Lead, OutreachLog

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return

    config = WHConfig
    message = (
        f"Hi, I'm {config['CONTACT_NAME']} from {config['COMPANY_NAME']}. "
        f"We offer premium CLI voice routes to 190+ countries with high ASR. "
        f"Would you be interested in a free test to compare quality on your key destinations? "
        f"Let me know and I'll set it up right away."
    )

    # TODO: Use Playwright/Puppeteer to:
    # 1. Navigate to lead.website_url
    # 2. Find /contact, /contact-us, /inquiry, /get-quote pages
    # 3. Detect and fill form fields
    # 4. Submit the form

    OutreachLog.objects.create(
        lead=lead,
        channel='form',
        sequence_stage=1,
        status='sent',
        message_body=message,
    )

    lead.form_filled = True
    lead.save(update_fields=['form_filled'])
    return f"Contact form filled for {lead.company_domain}"


# ─── 5. FOLLOW-UP TASKS ─────────────────────────────────────────────

@shared_task
def process_followups():
    """
    Send follow-up emails to leads who haven't replied.
    Runs daily. Checks which leads are due for next follow-up.
    """
    from .models import Lead

    now = timezone.now()
    due = Lead.objects.filter(
        next_followup_at__lte=now,
        replied=False,
        sequence_stage__gt=0,
        sequence_stage__lt=4,
    )

    count = 0
    for lead in due:
        next_stage = lead.sequence_stage + 1
        send_email_to_lead.delay(str(lead.id), sequence_stage=next_stage)
        count += 1

    logger.info(f"Processed {count} follow-ups")
    return f"Sent {count} follow-up emails"


# ─── 6. WEEKLY INTELLIGENCE ─────────────────────────────────────────

@shared_task
def generate_weekly_report():
    """
    Generate weekly intelligence report.
    Runs every Sunday.
    """
    from .models import Lead, WeeklyReport

    today = timezone.now().date()
    week_ago = today - timedelta(days=7)

    week_leads = Lead.objects.filter(created_at__date__gte=week_ago)

    # By country breakdown
    by_country = {}
    for row in week_leads.values('country').annotate(
        total=Count('id'),
        replies=Count('id', filter=Q(replied=True)),
        closed=Count('id', filter=Q(closed=True)),
    ):
        by_country[row['country']] = {
            'total': row['total'],
            'replies': row['replies'],
            'closed': row['closed'],
            'close_rate': round(row['closed'] / row['total'] * 100, 1) if row['total'] else 0,
        }

    # By lead type breakdown
    by_lead_type = {}
    for row in week_leads.values('lead_type').annotate(
        total=Count('id'),
        replies=Count('id', filter=Q(replied=True)),
        closed=Count('id', filter=Q(closed=True)),
    ):
        by_lead_type[row['lead_type']] = {
            'total': row['total'],
            'replies': row['replies'],
            'closed': row['closed'],
        }

    # By source
    by_source = {}
    for row in week_leads.values('source').annotate(
        total=Count('id'),
        replies=Count('id', filter=Q(replied=True)),
    ):
        by_source[row['source']] = {
            'total': row['total'],
            'replies': row['replies'],
            'reply_rate': round(row['replies'] / row['total'] * 100, 1) if row['total'] else 0,
        }

    # By channel
    email_only = week_leads.filter(email_sent=True, form_filled=False)
    form_only = week_leads.filter(form_filled=True, email_sent=False)
    both = week_leads.filter(email_sent=True, form_filled=True)

    by_channel = {
        'email_only': {
            'total': email_only.count(),
            'replies': email_only.filter(replied=True).count(),
        },
        'form_only': {
            'total': form_only.count(),
            'replies': form_only.filter(replied=True).count(),
        },
        'both': {
            'total': both.count(),
            'replies': both.filter(replied=True).count(),
        },
    }

    report = WeeklyReport.objects.create(
        report_date=today,
        total_leads=week_leads.count(),
        total_emailed=week_leads.filter(email_sent=True).count(),
        total_forms_filled=week_leads.filter(form_filled=True).count(),
        total_replies=week_leads.filter(replied=True).count(),
        total_interested=week_leads.filter(interested=True).count(),
        total_closed=week_leads.filter(closed=True).count(),
        by_country=by_country,
        by_lead_type=by_lead_type,
        by_source=by_source,
        by_channel=by_channel,
    )

    # Run auto-exclusion evaluation
    evaluate_exclusion_rules.delay()

    logger.info(f"Generated weekly report for {today}")
    return f"Weekly report generated: {report}"


# ─── 7. AUTO-EXCLUSION RULES ────────────────────────────────────────

@shared_task
def evaluate_exclusion_rules():
    """
    Evaluate auto-exclusion rules based on performance data.
    """
    from .models import Lead, ExclusionRule

    config = WHConfig

    # Rule 1: Country with 0 closes after 200+ leads
    country_stats = (
        Lead.objects.values('country')
        .annotate(
            total=Count('id', filter=Q(email_sent=True)),
            closes=Count('id', filter=Q(closed=True)),
        )
        .filter(total__gte=config['COUNTRY_PAUSE_THRESHOLD'], closes=0)
    )
    for stat in country_stats:
        ExclusionRule.objects.update_or_create(
            rule_type='country_pause',
            dimension_value=stat['country'],
            defaults={
                'reason': f"0 closes after {stat['total']} leads contacted",
                'leads_contacted': stat['total'],
                'metric_value': 0,
                'is_active': True,
            },
        )

    # Rule 2: Lead type with <0.5% close rate after 500+
    type_stats = (
        Lead.objects.values('lead_type')
        .annotate(
            total=Count('id', filter=Q(email_sent=True)),
            closes=Count('id', filter=Q(closed=True)),
        )
        .filter(total__gte=500)
    )
    for stat in type_stats:
        close_rate = stat['closes'] / stat['total'] if stat['total'] else 0
        if close_rate < config['LEAD_TYPE_DEPRIORITIZE_RATE']:
            ExclusionRule.objects.update_or_create(
                rule_type='type_deprioritize',
                dimension_value=stat['lead_type'],
                defaults={
                    'reason': f"{close_rate*100:.2f}% close rate after {stat['total']} leads",
                    'leads_contacted': stat['total'],
                    'metric_value': close_rate * 100,
                    'is_active': True,
                },
            )

    # Rule 3: Source with <1% reply rate after 1000+
    source_stats = (
        Lead.objects.values('source')
        .annotate(
            total=Count('id', filter=Q(email_sent=True)),
            replies=Count('id', filter=Q(replied=True)),
        )
        .filter(total__gte=1000)
    )
    for stat in source_stats:
        reply_rate = stat['replies'] / stat['total'] if stat['total'] else 0
        if reply_rate < config['SOURCE_REDUCE_RATE']:
            ExclusionRule.objects.update_or_create(
                rule_type='source_reduce',
                dimension_value=stat['source'],
                defaults={
                    'reason': f"{reply_rate*100:.2f}% reply rate after {stat['total']} sends",
                    'leads_contacted': stat['total'],
                    'metric_value': reply_rate * 100,
                    'is_active': True,
                },
            )

    logger.info("Exclusion rules evaluated")
    return "Exclusion rules evaluated"


# ─── 8. HANDOFF TASK ────────────────────────────────────────────────

@shared_task
def notify_hot_lead(lead_id):
    """
    Notify Sajid when a lead replies or shows interest.
    TODO: Integrate with HubSpot + email/Slack notification.
    """
    from .models import Lead

    try:
        lead = Lead.objects.get(id=lead_id)
    except Lead.DoesNotExist:
        return

    # TODO: Push to HubSpot Free CRM
    # TODO: Send notification email/Slack message

    logger.info(f"HOT LEAD: {lead.company_name} ({lead.company_domain}) - replied!")
    return f"Notification sent for hot lead: {lead.company_domain}"
