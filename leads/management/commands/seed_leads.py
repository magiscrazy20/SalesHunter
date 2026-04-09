"""
Management command to seed the database with sample leads for testing.
Usage: python manage.py seed_leads --count 100
"""
import random
from django.core.management.base import BaseCommand
from leads.models import Lead, LeadType, LeadSource


SAMPLE_COUNTRIES = [
    ('US', ['New York', 'Los Angeles', 'Miami', 'Chicago', 'Houston']),
    ('UK', ['London', 'Manchester', 'Birmingham', 'Edinburgh']),
    ('UAE', ['Dubai', 'Abu Dhabi', 'Sharjah']),
    ('India', ['Mumbai', 'Delhi', 'Bangalore', 'Hyderabad']),
    ('Nigeria', ['Lagos', 'Abuja', 'Port Harcourt']),
    ('South Africa', ['Johannesburg', 'Cape Town', 'Durban']),
    ('Germany', ['Berlin', 'Munich', 'Frankfurt']),
    ('Singapore', ['Singapore']),
    ('Kenya', ['Nairobi', 'Mombasa']),
    ('Philippines', ['Manila', 'Cebu']),
]

COMPANY_PREFIXES = [
    'Global', 'Prime', 'Elite', 'Swift', 'Atlas', 'Nexus', 'Apex',
    'Titan', 'Zenith', 'Quantum', 'Vertex', 'Pinnacle', 'Stellar',
]

COMPANY_SUFFIXES = [
    'Telecom', 'Communications', 'VoIP', 'Networks', 'Connect',
    'Solutions', 'Technologies', 'Tel', 'Voice', 'Media',
]

KEYWORDS = [
    'wholesale voice {country}', 'VoIP provider {country}',
    'CLI routes {country}', 'call center {country}',
    'telecom company {city}', 'voice termination {country}',
]


class Command(BaseCommand):
    help = 'Seed the database with sample leads for testing'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=100)

    def handle(self, *args, **options):
        count = options['count']
        created = 0

        for i in range(count):
            country, cities = random.choice(SAMPLE_COUNTRIES)
            city = random.choice(cities)
            prefix = random.choice(COMPANY_PREFIXES)
            suffix = random.choice(COMPANY_SUFFIXES)
            name = f"{prefix} {suffix} {i+1}"
            domain = f"{prefix.lower()}{suffix.lower()}{i+1}.com"

            lead_type = random.choice([c[0] for c in LeadType.choices])
            source = random.choice([c[0] for c in LeadSource.choices])

            keyword = random.choice(KEYWORDS).format(country=country, city=city)

            score = random.randint(20, 95)
            email_sent = random.random() > 0.3
            form_filled = random.random() > 0.5
            replied = email_sent and random.random() > 0.92
            interested = replied and random.random() > 0.6
            closed = interested and random.random() > 0.5

            Lead.objects.create(
                company_domain=domain,
                company_name=name,
                contact_name=f"John Doe {i+1}",
                contact_email=f"contact@{domain}",
                website_url=f"https://{domain}",
                has_contact_form=random.random() > 0.3,
                country=country,
                city=city,
                lead_type=lead_type,
                source=source,
                keyword_used=keyword,
                company_size=random.choice(['small', 'medium', 'enterprise']),
                score=score,
                email_sent=email_sent,
                form_filled=form_filled,
                replied=replied,
                interested=interested,
                closed=closed,
                revenue_monthly=random.randint(50, 300) if closed else 0,
                sequence_stage=random.randint(1, 4) if email_sent else 0,
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f'Created {created} sample leads'))
