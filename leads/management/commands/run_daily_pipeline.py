"""
Management command to run the full daily pipeline manually.
Usage: python manage.py run_daily_pipeline
"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the full SalesHunter daily pipeline'

    def add_arguments(self, parser):
        parser.add_argument('--step', type=str, default='all',
                            choices=['all', 'scrape', 'qualify', 'email', 'form', 'followup', 'report'])

    def handle(self, *args, **options):
        from leads.tasks import (
            scrape_leads_daily, qualify_new_leads, send_daily_emails,
            fill_daily_forms, process_followups, generate_weekly_report,
        )

        step = options['step']

        if step in ('all', 'scrape'):
            self.stdout.write('Step 1: Scraping leads...')
            result = scrape_leads_daily.apply()
            self.stdout.write(f'  {result.result}')

        if step in ('all', 'qualify'):
            self.stdout.write('Step 2: Qualifying leads...')
            result = qualify_new_leads.apply()
            self.stdout.write(f'  {result.result}')

        if step in ('all', 'email'):
            self.stdout.write('Step 3: Sending emails...')
            result = send_daily_emails.apply()
            self.stdout.write(f'  {result.result}')

        if step in ('all', 'form'):
            self.stdout.write('Step 4: Filling forms...')
            result = fill_daily_forms.apply()
            self.stdout.write(f'  {result.result}')

        if step in ('all', 'followup'):
            self.stdout.write('Step 5: Processing follow-ups...')
            result = process_followups.apply()
            self.stdout.write(f'  {result.result}')

        if step == 'report':
            self.stdout.write('Generating weekly report...')
            result = generate_weekly_report.apply()
            self.stdout.write(f'  {result.result}')

        self.stdout.write(self.style.SUCCESS('Pipeline complete!'))
