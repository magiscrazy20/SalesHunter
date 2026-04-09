import uuid
from django.db import models
from django.utils import timezone


class LeadType(models.TextChoices):
    VOIP_PROVIDER = 'voip_provider', 'VoIP Provider'
    MNO = 'mno', 'MNO'
    MVNO = 'mvno', 'MVNO'
    CALL_CENTER = 'call_center', 'Call Center / BPO'
    UCAAS = 'ucaas', 'UCaaS Provider'
    CCAAS = 'ccaas', 'CCaaS Provider'
    RESELLER = 'reseller', 'Wholesale Reseller'
    ITSP = 'itsp', 'ITSP'


class LeadSource(models.TextChoices):
    LINKEDIN = 'linkedin', 'LinkedIn (Apollo)'
    GOOGLE_SEARCH = 'google_search', 'Google Search'
    GOOGLE_MAPS = 'google_maps', 'Google Maps'
    DIRECTORY = 'directory', 'Telecom Directory'
    CONFERENCE = 'conference', 'Conference List'


class ExhaustionStatus(models.TextChoices):
    ACTIVE = 'active', 'Active'
    EXHAUSTED = 'exhausted', 'Exhausted'
    PAUSED = 'paused', 'Paused'


class Lead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_domain = models.CharField(max_length=255, unique=True, db_index=True)
    company_name = models.CharField(max_length=255)
    contact_name = models.CharField(max_length=255, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    website_url = models.URLField(max_length=500, blank=True)
    has_contact_form = models.BooleanField(default=False)

    country = models.CharField(max_length=100, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    lead_type = models.CharField(max_length=20, choices=LeadType.choices, db_index=True)
    source = models.CharField(max_length=20, choices=LeadSource.choices, db_index=True)
    keyword_used = models.CharField(max_length=255, blank=True)
    company_size = models.CharField(
        max_length=20,
        choices=[('small', 'Small'), ('medium', 'Medium'), ('enterprise', 'Enterprise')],
        blank=True,
    )
    score = models.IntegerField(default=0, help_text='AI quality score 0-100')

    # Outreach tracking
    email_sent = models.BooleanField(default=False)
    form_filled = models.BooleanField(default=False)
    email_opened = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)
    interested = models.BooleanField(default=False)
    closed = models.BooleanField(default=False)
    revenue_monthly = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Sequence tracking
    sequence_stage = models.IntegerField(
        default=0,
        help_text='Which email in the sequence (0=not started, 1-4)',
    )
    last_contacted_at = models.DateTimeField(null=True, blank=True)
    next_followup_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['country', 'lead_type']),
            models.Index(fields=['source', 'keyword_used']),
            models.Index(fields=['score']),
            models.Index(fields=['replied']),
            models.Index(fields=['closed']),
            models.Index(fields=['sequence_stage', 'next_followup_at']),
        ]

    def __str__(self):
        return f"{self.company_name} ({self.company_domain})"

    @property
    def is_qualified(self):
        return self.score >= 40


class SourceExhaustionTracker(models.Model):
    source = models.CharField(max_length=20, choices=LeadSource.choices)
    keyword = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    city = models.CharField(max_length=100, blank=True)
    lead_type = models.CharField(max_length=20, choices=LeadType.choices, blank=True)
    total_found = models.IntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=ExhaustionStatus.choices,
        default=ExhaustionStatus.ACTIVE,
    )
    last_scraped = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ['source', 'keyword', 'country', 'city', 'lead_type']
        ordering = ['-last_scraped']

    def __str__(self):
        return f"{self.source} | {self.keyword} | {self.country} [{self.status}]"


class ExclusionRule(models.Model):
    RULE_TYPES = [
        ('country_pause', 'Country Pause (0 closes after N leads)'),
        ('type_deprioritize', 'Lead Type Deprioritize (<0.5% close rate)'),
        ('source_reduce', 'Source Reduce (<1% reply rate)'),
        ('domain_rotate', 'Domain Rotate (low open rate)'),
    ]

    rule_type = models.CharField(max_length=30, choices=RULE_TYPES)
    dimension_value = models.CharField(
        max_length=255,
        help_text='The country, lead type, source, or domain being excluded',
    )
    reason = models.TextField()
    leads_contacted = models.IntegerField(default=0)
    metric_value = models.FloatField(
        default=0,
        help_text='The close rate, reply rate, or open rate that triggered exclusion',
    )
    is_active = models.BooleanField(default=True)
    overridden = models.BooleanField(
        default=False,
        help_text='Manually overridden by admin',
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        status = 'OVERRIDDEN' if self.overridden else ('ACTIVE' if self.is_active else 'INACTIVE')
        return f"[{status}] {self.get_rule_type_display()} - {self.dimension_value}"


class OutreachLog(models.Model):
    CHANNEL_CHOICES = [
        ('email', 'Email'),
        ('form', 'Contact Form'),
    ]
    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('opened', 'Opened'),
        ('replied', 'Replied'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='outreach_logs')
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    sequence_stage = models.IntegerField(help_text='1=intro, 2=quality, 3=social proof, 4=breakup')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='sent')
    subject = models.CharField(max_length=500, blank=True)
    message_body = models.TextField(blank=True)
    sending_domain = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    opened_at = models.DateTimeField(null=True, blank=True)
    replied_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.channel} #{self.sequence_stage} to {self.lead.company_domain} [{self.status}]"


class SmtpConnection(models.Model):
    name = models.CharField(max_length=255)
    host = models.CharField(max_length=255)
    port = models.IntegerField(default=587)
    username = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    use_tls = models.BooleanField(default=True)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    daily_limit = models.IntegerField(default=100, help_text='Max emails per day from this connection')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.from_email})"


class EmailTemplate(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=500)
    body = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class LeadList(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    leads = models.ManyToManyField(Lead, blank=True, related_name='lead_lists')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.leads.count()} leads)"


class EmailCampaign(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('scheduled', 'Scheduled'),
        ('paused', 'Paused'),
    ]
    SEND_OPTION_CHOICES = [
        ('now', 'Send Now'),
        ('later', 'Schedule for Later'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    # Email content
    subject = models.CharField(max_length=500, default='')
    body = models.TextField(default='', help_text='Use {{firstName}}, {{lastName}}, {{company}}, {{email}} for personalization')

    # Send options
    send_option = models.CharField(max_length=10, choices=SEND_OPTION_CHOICES, default='now')
    scheduled_at = models.DateTimeField(null=True, blank=True)

    # Connections
    lead_list = models.ForeignKey(LeadList, on_delete=models.SET_NULL, null=True, blank=True, related_name='campaigns')
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    smtp_connection = models.ForeignKey(SmtpConnection, on_delete=models.SET_NULL, null=True, blank=True, help_text='Leave blank for auto-select')

    # Additional recipients
    cc = models.TextField(blank=True, help_text='Comma-separated CC emails')
    bcc = models.TextField(blank=True, help_text='Comma-separated BCC emails')

    # Stats
    total_recipients = models.IntegerField(default=0)
    total_sent = models.IntegerField(default=0)
    total_opened = models.IntegerField(default=0)
    total_replied = models.IntegerField(default=0)
    total_bounced = models.IntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} [{self.status}]"

    @property
    def open_rate(self):
        return round(self.total_opened / self.total_sent * 100, 1) if self.total_sent else 0

    @property
    def reply_rate(self):
        return round(self.total_replied / self.total_sent * 100, 1) if self.total_sent else 0

    def render_body(self, lead):
        text = self.body
        text = text.replace('{{firstName}}', lead.contact_name.split()[0] if lead.contact_name else '')
        text = text.replace('{{lastName}}', ' '.join(lead.contact_name.split()[1:]) if lead.contact_name else '')
        text = text.replace('{{company}}', lead.company_name)
        text = text.replace('{{email}}', lead.contact_email)
        return text

    def render_subject(self, lead):
        text = self.subject
        text = text.replace('{{firstName}}', lead.contact_name.split()[0] if lead.contact_name else '')
        text = text.replace('{{lastName}}', ' '.join(lead.contact_name.split()[1:]) if lead.contact_name else '')
        text = text.replace('{{company}}', lead.company_name)
        text = text.replace('{{email}}', lead.contact_email)
        return text


class WeeklyReport(models.Model):
    report_date = models.DateField(unique=True)
    total_leads = models.IntegerField(default=0)
    total_emailed = models.IntegerField(default=0)
    total_forms_filled = models.IntegerField(default=0)
    total_replies = models.IntegerField(default=0)
    total_interested = models.IntegerField(default=0)
    total_closed = models.IntegerField(default=0)

    # JSON fields for breakdowns
    by_country = models.JSONField(default=dict)
    by_lead_type = models.JSONField(default=dict)
    by_source = models.JSONField(default=dict)
    by_channel = models.JSONField(default=dict)

    exclusions_applied = models.JSONField(default=list)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-report_date']

    def __str__(self):
        return f"Weekly Report - {self.report_date}"


# ─── LEAD MASTER MODELS (migrated from lead_master project) ──────────

class SearchSession(models.Model):
    SOURCE_CHOICES = [
        ('apollo', 'Apollo'),
        ('google_maps', 'Google Maps'),
        ('linkedin', 'LinkedIn'),
        ('master', 'Master'),
    ]
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('partial', 'Partial'),
        ('failed', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    search_params = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    progress = models.JSONField(default=dict, blank=True)
    lead_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.lead_count} leads)"


class MasterLead(models.Model):
    SOURCE_CHOICES = [
        ('apollo', 'Apollo'),
        ('google_maps', 'Google Maps'),
        ('linkedin', 'LinkedIn'),
    ]

    session = models.ForeignKey(SearchSession, on_delete=models.CASCADE, related_name='leads')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    company_name = models.CharField(max_length=500)
    industry = models.CharField(max_length=255, blank=True, default='')
    location = models.CharField(max_length=500, blank=True, default='')
    emails = models.JSONField(default=list)
    phone = models.CharField(max_length=100, blank=True, default='')
    website = models.URLField(max_length=500, blank=True, default='')
    linkedin_url = models.URLField(max_length=500, blank=True, default='')
    keyword = models.CharField(max_length=255, blank=True, default='')
    keyword_category = models.CharField(max_length=255, blank=True, default='')
    country = models.CharField(max_length=255, blank=True, default='')
    employee_count = models.IntegerField(null=True, blank=True)
    description = models.TextField(blank=True, default='')
    raw_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.company_name


class FormTask(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    entity_name = models.CharField(max_length=255)
    lead = models.ForeignKey(MasterLead, on_delete=models.CASCADE, related_name='form_tasks', null=True, blank=True)
    company_name = models.CharField(max_length=500)
    website = models.URLField(max_length=500)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    batch_id = models.CharField(max_length=50, blank=True, default='')
    message = models.TextField(blank=True, default='')
    logs = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entity_name} -> {self.company_name} ({self.status})"
