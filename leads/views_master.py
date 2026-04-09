import json
import os
import re
import html
import concurrent.futures

import requests
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from .models import SearchSession, MasterLead as Lead, FormTask


# ──────────────────────────────────────────────
# Keyword parser
# ──────────────────────────────────────────────

def _parse_keyword_sections():
    """Parse keywords.txt into sections."""
    import os
    kw_file = os.path.join(settings.BASE_DIR, 'static', 'keywords.txt')
    if not os.path.exists(kw_file):
        return []
    with open(kw_file, 'r', encoding='utf-8') as f:
        content = f.read()
    sections = []
    for block in content.split('---'):
        block = block.strip()
        if not block:
            continue
        lines = block.split('\n')
        name = ''
        keywords = []
        for line in lines:
            line = line.strip()
            if line.startswith('## '):
                # Remove "## 1. " prefix
                name = re.sub(r'^##\s*\d+\.\s*', '', line).strip()
            elif line and not line.startswith('#'):
                keywords.append(line)
        if name and keywords:
            sections.append({'name': name, 'keywords': keywords})
    return sections


# ──────────────────────────────────────────────
# Pages
# ──────────────────────────────────────────────

def master_page(request):
    return render(request, 'leads/master/master.html', {
        'active_nav': 'master',
    })

def lead_history_page(request):
    sessions = SearchSession.objects.order_by('-created_at')[:50]
    return render(request, 'leads/master/lead_history.html', {'active_nav': 'history', 'sessions': sessions})


def session_detail(request, session_id):
    session = get_object_or_404(SearchSession, id=session_id)
    leads = session.leads.all()
    return render(request, 'leads/master/session_detail.html', {'session': session, 'leads': leads, 'active_nav': 'sessions'})


def process_leads_page(request):
    from django.db.models import Count
    categories = list(Lead.objects.exclude(keyword_category='').values('keyword_category').annotate(
        count=Count('id')
    ).order_by('-count'))
    # Add "Others" for leads with empty keyword_category
    others_count = Lead.objects.filter(keyword_category='').count()
    if others_count > 0:
        categories.append({'keyword_category': 'Others', 'count': others_count})
    return render(request, 'leads/master/process_leads.html', {'active_nav': 'process', 'categories': categories})


def process_leads_category(request, category):
    """Keyword category → Country drill-down."""
    from django.db.models import Count
    if category == 'Others':
        leads_qs = Lead.objects.filter(keyword_category='')
    else:
        leads_qs = Lead.objects.filter(keyword_category=category)
    countries = leads_qs.exclude(country='').values('country').annotate(
        count=Count('id')
    ).order_by('-count')
    total = leads_qs.count()
    return render(request, 'leads/master/process_leads_category.html', {
        'active_nav': 'process', 'category': category, 'countries': countries, 'total': total,
    })


def process_leads_country(request, country):
    from django.db.models import Count
    category = request.GET.get('cat', '')
    # Get regions for this country
    leads_qs = Lead.objects.filter(country=country)
    if category == 'Others':
        leads_qs = leads_qs.filter(keyword_category='')
    elif category:
        leads_qs = leads_qs.filter(keyword_category=category)
    # Extract region from location (first part before comma, or full location)
    regions = {}
    for lead in leads_qs:
        loc = lead.location or ''
        parts = [p.strip() for p in loc.split(',') if p.strip()]
        if len(parts) >= 2:
            # Use state/region (second-to-last part for "City, State, Country" or first part for "State, Country")
            region = parts[-2] if len(parts) >= 3 else parts[0]
        elif parts:
            region = parts[0]
        else:
            region = 'Unknown'
        if region not in regions:
            regions[region] = 0
        regions[region] += 1
    sorted_regions = sorted(regions.items(), key=lambda x: -x[1])
    total = leads_qs.count()
    with_email = leads_qs.exclude(emails=[]).count()
    with_phone = leads_qs.exclude(phone='').count()
    with_website = leads_qs.exclude(website='').count()
    return render(request, 'leads/master/process_leads_country.html', {
        'active_nav': 'process', 'country': country, 'category': category,
        'regions': sorted_regions, 'total': total,
        'with_email': with_email, 'with_phone': with_phone, 'with_website': with_website,
    })


def process_leads_country_all(request, country):
    category = request.GET.get('cat', '')
    leads = Lead.objects.filter(country=country)
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)
    leads = leads.order_by('-created_at')
    with_email = leads.exclude(emails=[]).count()
    with_phone = leads.exclude(phone='').count()
    with_website = leads.exclude(website='').count()
    return render(request, 'leads/master/process_leads_all.html', {
        'active_nav': 'process', 'country': country, 'category': category, 'leads': leads,
        'with_email': with_email, 'with_phone': with_phone, 'with_website': with_website,
    })


def process_leads_region(request, country, region):
    category = request.GET.get('cat', '')
    leads = Lead.objects.filter(country=country, location__icontains=region)
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)
    leads = leads.order_by('-created_at')
    with_email = leads.exclude(emails=[]).count()
    with_phone = leads.exclude(phone='').count()
    with_website = leads.exclude(website='').count()
    return render(request, 'leads/master/process_leads_region.html', {
        'active_nav': 'process', 'country': country, 'region': region, 'category': category,
        'leads': leads, 'with_email': with_email, 'with_phone': with_phone, 'with_website': with_website,
    })


# ── Location API ──

def api_countries(request):
    from .locations import get_all_countries
    return JsonResponse(get_all_countries(), safe=False)


def api_states(request, country_code):
    from .locations import get_states
    return JsonResponse(get_states(country_code), safe=False)


def api_cities(request, country_code, state_name):
    from .locations import get_cities
    return JsonResponse(get_cities(country_code, state_name), safe=False)


# ──────────────────────────────────────────────
# Start search (server-side background)
# ──────────────────────────────────────────────

@csrf_exempt
def start_search(request):
    """Start separate searches per keyword category. Returns session IDs."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        locs = body.get('locations', '')
        sources = body.get('sources', ['Apollo', 'Google Maps', 'LinkedIn'])
        loc_display = body.get('location_display', '') or ''
        # keyword_sections: list of {name, keywords} from frontend
        kw_sections = body.get('keyword_sections', [])

        locations = [l.strip() for l in locs.split('\n') if l.strip()] if isinstance(locs, str) else locs

        if not kw_sections:
            # Fallback: old format with raw keywords
            kw = body.get('keywords', '')
            kw_display = body.get('keyword_display', '')
            kw_sections = [{'name': kw_display or 'Search', 'keywords': kw}]

        session_ids = []
        from .tasks_master import start_master_search_bg

        for section in kw_sections:
            cat_name = section['name']
            cat_kw = section['keywords']
            if isinstance(cat_kw, str):
                cat_keywords = [k.strip() for k in cat_kw.split('\n') if k.strip()]
            else:
                cat_keywords = cat_kw

            source_label = 'Master' if len(sources) == 3 else ', '.join(sources)
            name = f"{source_label}: {cat_name} in {loc_display[:40]}" if loc_display else f"{source_label}: {cat_name}"

            session = SearchSession.objects.create(
                name=name,
                source='master',
                search_params={
                    'keywords': cat_name,
                    'keyword_category': cat_name,
                    'locations': loc_display,
                    'sources': sources,
                    'keywords_raw': '\n'.join(cat_keywords),
                    'locations_raw': locs,
                },
                status='running',
                progress={'stage': 'Starting', 'detail': '', 'pct': 0},
            )

            start_master_search_bg(str(session.id), cat_keywords, locations, sources, cat_name)
            session_ids.append(str(session.id))

        return JsonResponse({'session_ids': session_ids, 'count': len(session_ids)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def session_progress(request, session_id):
    """Return current progress of a session."""
    try:
        session = SearchSession.objects.get(id=session_id)
        return JsonResponse({
            'status': session.status,
            'progress': session.progress,
            'lead_count': session.lead_count,
        })
    except SearchSession.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# ──────────────────────────────────────────────
# Session management
# ──────────────────────────────────────────────

@csrf_exempt
def create_session(request):
    """Create a 'running' session immediately so it shows in sidebar even if page refreshes."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        source = body.get('source', 'master')
        search_params = body.get('search_params', {})
        kw = search_params.get('keywords', '')
        loc = search_params.get('location', search_params.get('locations', ''))
        if isinstance(loc, list):
            loc = ', '.join(loc)
        if isinstance(kw, list):
            kw = ', '.join(kw)
        name = f"{source.replace('_', ' ').title()}: {kw[:40]} in {loc[:30]}" if kw else f"{source.title()} search"
        session = SearchSession.objects.create(
            name=name, source=source, search_params=search_params, status='running', lead_count=0,
        )
        return JsonResponse({'session_id': str(session.id)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def update_session(request):
    """Update session with leads after process completes."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        session_id = body.get('session_id')
        status = body.get('status', 'completed')
        leads_data = body.get('leads', [])
        session = SearchSession.objects.get(id=session_id)
        session.status = status
        session.lead_count = len(leads_data)
        session.save()

        if leads_data:
            lead_objects = []
            for ld in leads_data:
                lead_objects.append(Lead(
                    session=session,
                    source=ld.get('source', session.source),
                    company_name=ld.get('company_name', '')[:500],
                    industry=ld.get('industry', '')[:255],
                    location=ld.get('location', '')[:500],
                    emails=ld.get('emails', []),
                    phone=ld.get('phone', '')[:100],
                    website=ld.get('website', '')[:500],
                    linkedin_url=ld.get('linkedin_url', '')[:500],
                    keyword=ld.get('keyword', '')[:255],
                    country=ld.get('country', '')[:255],
                    employee_count=ld.get('employee_count'),
                    description=ld.get('description', ''),
                    raw_data=ld.get('raw_data', {}),
                ))
            Lead.objects.bulk_create(lead_objects)

        return JsonResponse({'saved': len(leads_data)})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def edit_lead(request, lead_id):
    """Edit a single lead's fields."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        lead = Lead.objects.get(id=lead_id)
        body = json.loads(request.body)
        for field in ['company_name', 'industry', 'location', 'phone', 'website', 'linkedin_url', 'keyword']:
            if field in body:
                setattr(lead, field, body[field])
        if 'emails' in body:
            lead.emails = body['emails']
        lead.save()
        return JsonResponse({'ok': True})
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def find_missing(request, lead_id):
    """Find missing email/phone from website using multi-strategy finder."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        lead = Lead.objects.get(id=lead_id)
        website = lead.website
        if not website:
            return JsonResponse({'error': 'No website URL for this lead'}, status=400)

        from .email_finder import find_emails_fast, _fetch_page
        from urllib.parse import urlparse

        domain = ''
        try:
            domain = urlparse(website if website.startswith('http') else 'https://' + website).hostname.replace('www.', '')
        except Exception:
            pass

        updated = {}

        if not lead.emails:
            emails = find_emails_fast(website, domain)
            if emails:
                lead.emails = emails
                updated['emails'] = emails

        if not lead.phone:
            page_html = _fetch_page(website if website.startswith('http') else 'https://' + website)
            if page_html:
                phone_pattern = re.compile(r'[\+]?[1-9]\d{0,2}[\s.\-]?\(?\d{2,4}\)?[\s.\-]?\d{3,4}[\s.\-]?\d{3,4}')
                phones = [p.strip() for p in phone_pattern.findall(page_html) if len(p.strip()) >= 10]
                if phones:
                    lead.phone = phones[0]
                    updated['phone'] = phones[0]

        lead.save()
        return JsonResponse({'updated': updated, 'emails': lead.emails, 'phone': lead.phone})
    except Lead.DoesNotExist:
        return JsonResponse({'error': 'Lead not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def find_all_missing(request, session_id):
    """Find emails for all leads in a session that don't have emails yet."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        session = SearchSession.objects.get(id=session_id)
        leads = session.leads.filter(emails=[]).exclude(website='')
        total = leads.count()
        if total == 0:
            return JsonResponse({'found': 0, 'total': 0, 'message': 'No leads need email scanning'})

        import threading
        from .email_finder import find_emails_bulk

        def bg_scan():
            from django.db import close_old_connections
            close_old_connections()
            find_emails_bulk(leads, str(session_id))

        t = threading.Thread(target=bg_scan, daemon=True)
        t.start()

        return JsonResponse({'started': True, 'total': total, 'message': f'Scanning {total} websites in background'})
    except SearchSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def find_all_emails_country(request, country):
    """Find emails for all leads in a country."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        leads = Lead.objects.filter(country=country, emails=[]).exclude(website='')
        total = leads.count()
        if total == 0:
            return JsonResponse({'started': False, 'total': 0, 'message': 'No leads need email scanning'})
        import threading
        from .email_finder import find_emails_bulk
        def bg():
            from django.db import close_old_connections
            close_old_connections()
            find_emails_bulk(leads)
        threading.Thread(target=bg, daemon=True).start()
        return JsonResponse({'started': True, 'total': total, 'message': f'Scanning {total} websites in background'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def find_all_emails_region(request, country, region):
    """Find emails for all leads in a region."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        leads = Lead.objects.filter(country=country, location__icontains=region, emails=[]).exclude(website='')
        total = leads.count()
        if total == 0:
            return JsonResponse({'started': False, 'total': 0, 'message': 'No leads need email scanning'})
        import threading
        from .email_finder import find_emails_bulk
        def bg():
            from django.db import close_old_connections
            close_old_connections()
            find_emails_bulk(leads)
        threading.Thread(target=bg, daemon=True).start()
        return JsonResponse({'started': True, 'total': total, 'message': f'Scanning {total} websites in background'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def session_list(request):
    """Return recent sessions as JSON."""
    # Auto-fix orphaned 'running' sessions older than 15 minutes
    from django.utils import timezone
    import datetime
    cutoff = timezone.now() - datetime.timedelta(hours=2)
    SearchSession.objects.filter(status='running', created_at__lt=cutoff).update(
        status='failed',
        progress={'stage': 'Error', 'detail': 'Process interrupted', 'pct': 0},
    )

    sessions = SearchSession.objects.order_by('-created_at')[:20]
    data = []
    for s in sessions:
        sources = s.search_params.get('sources', [])
        if sources and len(sources) == 3:
            source_display = 'Master'
        elif sources:
            source_display = ', '.join(sources)
        else:
            source_display = s.get_source_display()
        data.append({
            'id': str(s.id),
            'name': s.name,
            'source': s.source,
            'source_display': source_display,
            'status': s.status,
            'progress': s.progress,
            'lead_count': s.lead_count,
            'created_at': s.created_at.strftime('%b %d, %I:%M %p'),
        })
    return JsonResponse(data, safe=False)


@csrf_exempt
def delete_session(request, session_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        session = SearchSession.objects.get(id=session_id)
        session.delete()
        return JsonResponse({'ok': True})
    except SearchSession.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


# ──────────────────────────────────────────────
# Save leads
# ──────────────────────────────────────────────


# ──────────────────────────────────────────────
# Apollo search proxy
# ──────────────────────────────────────────────

@csrf_exempt
def apollo_search(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        resp = requests.post(
            'https://api.apollo.io/v1/organizations/search',
            json=body,
            headers={'Content-Type': 'application/json', 'X-Api-Key': settings.APOLLO_API_KEY},
            timeout=30,
        )
        return JsonResponse(resp.json(), status=resp.status_code, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# Email scraper (multi-agent NVIDIA)
# ──────────────────────────────────────────────

BLOCKED_DOMAINS = [
    'example.com', 'email.com', 'domain.com', 'yoursite.com', 'sentry.io',
    'webpack.js', 'wixpress.com', 'googleapis.com',
    '.png', '.jpg', '.gif', '.svg', '.css', '.js',
]

SCRAPE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
}


def _fetch_page(url, timeout=8):
    try:
        resp = requests.get(url, headers=SCRAPE_HEADERS, timeout=timeout, allow_redirects=True)
        return resp.text[:500000] if resp.status_code == 200 else ''
    except Exception:
        return ''


def _extract_emails(html_text):
    if not html_text:
        return set()
    cleaned = re.sub(r'<script[\s\S]*?</script>', '', html_text, flags=re.IGNORECASE)
    cleaned = re.sub(r'<style[\s\S]*?</style>', '', cleaned, flags=re.IGNORECASE)
    decoded = html.unescape(cleaned)
    decoded = re.sub(r'\[at\]', '@', decoded, flags=re.IGNORECASE)
    decoded = re.sub(r'\[dot\]', '.', decoded, flags=re.IGNORECASE)
    decoded = re.sub(r'\(at\)', '@', decoded, flags=re.IGNORECASE)
    decoded = re.sub(r'\(dot\)', '.', decoded, flags=re.IGNORECASE)

    pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    emails = set(e.lower() for e in pattern.findall(decoded))
    return {e for e in emails if len(e) <= 60 and not any(b in e for b in BLOCKED_DOMAINS)}


def _scrape_emails_from_website(website_url):
    if not website_url:
        return []
    base = website_url.rstrip('/')
    if not base.startswith('http'):
        base = 'https://' + base
    paths = ['', '/contact', '/contact-us', '/about', '/about-us', '/contactus', '/support', '/get-in-touch']
    urls = [base + p for p in paths]
    all_emails = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for page_html in pool.map(_fetch_page, urls):
            all_emails.update(_extract_emails(page_html))
    return list(all_emails)


def _ai_extract_single_model(text_content, domain, model):
    try:
        resp = requests.post(
            'https://integrate.api.nvidia.com/v1/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {settings.NVIDIA_API_KEY}'},
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': f'Extract ALL email addresses from this website content of {domain}. Return only email addresses, one per line. If none found, return "NONE".\n\n{text_content[:4000]}'}],
                'temperature': 0.1, 'max_tokens': 500, 'stream': False,
            },
            timeout=15,
        )
        text = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
        return set(e.lower() for e in pattern.findall(text))
    except Exception:
        return set()


def _ai_extract_emails_multi(text_content, domain):
    models = getattr(settings, 'NVIDIA_MODELS', ['minimaxai/minimax-m2.5'])
    all_emails = set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(models)) as pool:
        futures = [pool.submit(_ai_extract_single_model, text_content, domain, m) for m in models]
        for f in concurrent.futures.as_completed(futures):
            all_emails.update(f.result())
    return list(all_emails)


@csrf_exempt
def find_emails(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        website = body.get('website', '')
        domain = body.get('domain', '')
        from .email_finder import find_emails_fast
        emails = find_emails_fast(website or domain, domain)
        return JsonResponse({'emails': emails})
    except Exception as e:
        return JsonResponse({'emails': [], 'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# Apify helper (with token parameter)
# ──────────────────────────────────────────────

def _apify_request(method, path, token, json_body=None):
    url = f'https://api.apify.com{path}'
    if '?' in url:
        url += f'&token={token}'
    else:
        url += f'?token={token}'
    return requests.request(method, url, json=json_body, timeout=30)


# ──────────────────────────────────────────────
# Apify Google Maps
# ──────────────────────────────────────────────

@csrf_exempt
def apify_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        input_data = {
            'searchStringsArray': body.get('keywords', []),
            'locationQuery': body.get('location', ''),
            'maxCrawledPlacesPerSearch': body.get('maxResults', 50),
            'maximumLeadsEnrichmentRecords': 0,
            'language': 'en',
            'includeWebResults': False,
            'scrapeContacts': False,
            'scrapeDirectories': False,
            'scrapeImageAuthors': False,
            'scrapePlaceDetailPage': False,
            'scrapeReviewsPersonalData': True,
            'scrapeSocialMediaProfiles': {'facebooks': False, 'instagrams': False, 'tiktoks': False, 'twitters': False, 'youtubes': False},
            'scrapeTableReservationProvider': False,
            'skipClosedPlaces': False,
            'searchMatching': 'all',
            'placeMinimumStars': '',
            'website': 'allPlaces',
            'maxQuestions': 0, 'maxReviews': 0,
            'reviewsSort': 'newest', 'reviewsFilterString': '', 'reviewsOrigin': 'all',
            'maxImages': 0, 'allPlacesNoSearchAction': '',
        }
        resp = _apify_request('POST', '/v2/acts/compass~crawler-google-places/runs', settings.APIFY_GOOGLE_MAP_API_KEY, json_body=input_data)
        data = resp.json()
        run_id = data.get('data', {}).get('id')
        if not run_id:
            raise Exception(data.get('error', {}).get('message', 'No run ID returned'))
        return JsonResponse({'runId': run_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def apify_status(request, run_id):
    try:
        resp = _apify_request('GET', f'/v2/actor-runs/{run_id}', settings.APIFY_GOOGLE_MAP_API_KEY)
        return JsonResponse({'status': resp.json().get('data', {}).get('status', 'UNKNOWN')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def apify_results(request, run_id):
    try:
        resp = _apify_request('GET', f'/v2/actor-runs/{run_id}/dataset/items?format=json', settings.APIFY_GOOGLE_MAP_API_KEY)
        items = resp.json()
        return JsonResponse({'items': items if isinstance(items, list) else []}, safe=False)
    except Exception as e:
        return JsonResponse({'items': [], 'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# LinkedIn
# ──────────────────────────────────────────────

@csrf_exempt
def linkedin_start(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        input_data = {
            'action': 'get-companies',
            'isName': False, 'isUrl': False,
            'keywords': body.get('keywords', []),
            'location': body.get('locations', []),
            'limit': 1000,
        }
        resp = _apify_request('POST', '/v2/acts/bebity~linkedin-premium-actor/runs', settings.APIFY_LINKEDIN_API_KEY, json_body=input_data)
        data = resp.json()
        run_id = data.get('data', {}).get('id')
        if not run_id:
            raise Exception(data.get('error', {}).get('message', 'No run ID returned'))
        return JsonResponse({'runId': run_id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def linkedin_status(request, run_id):
    try:
        resp = _apify_request('GET', f'/v2/actor-runs/{run_id}', settings.APIFY_LINKEDIN_API_KEY)
        return JsonResponse({'status': resp.json().get('data', {}).get('status', 'UNKNOWN')})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def linkedin_results(request, run_id):
    try:
        resp = _apify_request('GET', f'/v2/actor-runs/{run_id}/dataset/items?format=json', settings.APIFY_LINKEDIN_API_KEY)
        items = resp.json()
        return JsonResponse({'items': items if isinstance(items, list) else []}, safe=False)
    except Exception as e:
        return JsonResponse({'items': [], 'error': str(e)}, status=500)


# ──────────────────────────────────────────────
# Form Automation
# ──────────────────────────────────────────────

def _load_entities():
    entities_file = os.path.join(settings.BASE_DIR, 'form_automation', 'entities.json')
    try:
        with open(entities_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _get_entity(name):
    for e in _load_entities():
        if e['company'] == name:
            return e
    return None


def _entity_stats(entity_name):
    tasks = FormTask.objects.filter(entity_name=entity_name)
    total_leads = Lead.objects.exclude(website='').count()
    return {
        'total': total_leads,
        'websites': tasks.count(),
        'success': tasks.filter(status='success').count(),
        'failed': tasks.filter(status='failed').count(),
        'running': tasks.filter(status='running').count(),
        'pending': tasks.filter(status='pending').count(),
    }


def in_progress_page(request):
    """Show all form automation tasks grouped by entity with country+keyword breakdown."""
    # Safety: reset any stuck 'running' tasks (from server restart)
    from django.utils import timezone
    import datetime
    stuck = FormTask.objects.filter(
        status='running',
        created_at__lt=timezone.now() - datetime.timedelta(minutes=10)
    )
    if stuck.exists():
        stuck.update(status='failed', message='Interrupted — server restarted')

    entities = _load_entities()
    entity_rows = []

    for e in entities:
        name = e['company']
        tasks = FormTask.objects.filter(entity_name=name)
        if not tasks.exists():
            continue

        # Get all unique country+keyword combos that have tasks
        task_websites = set(tasks.values_list('website', flat=True))
        leads_with_tasks = Lead.objects.filter(website__in=task_websites)

        # Build country+keyword breakdown
        combos = {}
        for lead in leads_with_tasks:
            key = (lead.country or 'Unknown', lead.keyword_category or 'Other')
            if key not in combos:
                combos[key] = {'websites': set()}
            combos[key]['websites'].add(lead.website)

        # Also find countries+keywords with remaining leads (not yet processed)
        all_leads = Lead.objects.exclude(website='')
        done_websites = set(tasks.filter(status__in=['success', 'failed']).values_list('website', flat=True))
        for lead in all_leads:
            if lead.website in done_websites or lead.website in task_websites:
                continue
            key = (lead.country or 'Unknown', lead.keyword_category or 'Other')
            if key not in combos:
                combos[key] = {'websites': set()}
            combos[key]['websites'].add(lead.website)

        # Build sub-rows per combo with failed URL details
        sub_rows = []
        for (country, keyword), cdata in combos.items():
            c_tasks = tasks.filter(website__in=cdata['websites'])
            remaining = len(cdata['websites'] - done_websites - set(tasks.filter(status__in=['running', 'pending']).values_list('website', flat=True)))
            failed_tasks = list(c_tasks.filter(status='failed').values('id', 'website', 'company_name', 'message')[:50])
            sub_rows.append({
                'country': country,
                'keyword': keyword,
                'total': len(cdata['websites']),
                'success': c_tasks.filter(status='success').count(),
                'failed': c_tasks.filter(status='failed').count(),
                'running': c_tasks.filter(status='running').count(),
                'pending': c_tasks.filter(status='pending').count(),
                'remaining': remaining,
                'failed_tasks': failed_tasks,
            })
        sub_rows.sort(key=lambda x: (-(x['running'] + x['pending']), -x['total']))

        # ALL currently running tasks
        running_tasks = list(tasks.filter(status='running').values('website', 'company_name', 'lead__country', 'lead__keyword_category')[:10])

        entity_rows.append({
            'name': name,
            'email': e.get('email', ''),
            'running': tasks.filter(status='running').count(),
            'pending': tasks.filter(status='pending').count(),
            'success': tasks.filter(status='success').count(),
            'failed': tasks.filter(status='failed').count(),
            'total': tasks.count(),
            'running_tasks': running_tasks,
            'active': tasks.filter(status__in=['running', 'pending']).exists(),
            'sub_rows': sub_rows,
        })

    entity_rows.sort(key=lambda x: (-int(x['active']), -x['total']))

    # Global counts
    total_running = FormTask.objects.filter(status='running').count()
    total_pending = FormTask.objects.filter(status='pending').count()
    total_success = FormTask.objects.filter(status='success').count()
    total_failed = FormTask.objects.filter(status='failed').count()

    return render(request, 'leads/master/in_progress.html', {
        'active_nav': 'in_progress',
        'entity_rows': entity_rows,
        'total_running': total_running,
        'total_pending': total_pending,
        'total_success': total_success,
        'total_failed': total_failed,
    })


@csrf_exempt
def in_progress_stop_all(request):
    """Stop tasks. Can stop by batch_id (specific batch), entity, or all."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    body = json.loads(request.body)
    batch_id = body.get('batch_id', '')
    entity_name = body.get('entity_name', '')
    if batch_id:
        # Stop only this specific batch
        count = FormTask.objects.filter(batch_id=batch_id, status__in=['running', 'pending']).update(
            status='cancelled', message='Batch stopped'
        )
    elif entity_name:
        count = FormTask.objects.filter(entity_name=entity_name, status__in=['running', 'pending']).update(
            status='cancelled', message='Stopped from In Progress'
        )
    else:
        count = FormTask.objects.filter(status__in=['running', 'pending']).update(
            status='cancelled', message='Stopped from In Progress'
        )
    return JsonResponse({'stopped': count})


def in_progress_live(request):
    """Single API for all live data on the In Progress page."""
    entities = _load_entities()
    result = {'global': {}, 'entities': {}}

    g_running = g_pending = g_success = g_failed = 0

    for e in entities:
        name = e['company']
        tasks = FormTask.objects.filter(entity_name=name)
        if not tasks.exists():
            continue

        running = tasks.filter(status='running').count()
        pending = tasks.filter(status='pending').count()
        success = tasks.filter(status='success').count()
        failed = tasks.filter(status='failed').count()
        g_running += running
        g_pending += pending
        g_success += success
        g_failed += failed

        # All running tasks for this entity
        running_list = []
        for t in tasks.filter(status='running'):
            lead = t.lead
            running_list.append({
                'website': t.website,
                'company': t.company_name,
                'batch_id': t.batch_id,
                'country': lead.country if lead else '',
                'keyword': lead.keyword_category if lead else '',
            })

        # Per-task status for failed URL sub-tables
        task_statuses = {}
        for t in tasks:
            task_statuses[t.website] = {'id': t.id, 'status': t.status, 'message': t.message[:50], 'batch_id': t.batch_id}

        result['entities'][name] = {
            'running': running, 'pending': pending,
            'success': success, 'failed': failed,
            'total': tasks.count(),
            'task_statuses': task_statuses,
            'active': running > 0 or pending > 0,
            'running_tasks': running_list,
        }

    result['global'] = {
        'running': g_running, 'pending': g_pending,
        'success': g_success, 'failed': g_failed,
    }
    return JsonResponse(result)


def form_automation_page(request):
    """Entity list with overall charts."""
    entities = _load_entities()
    entity_data = []
    for e in entities:
        stats = _entity_stats(e['company'])
        entity_data.append({**e, 'stats': stats})

    return render(request, 'leads/master/form_automation.html', {
        'active_nav': 'form_automation',
        'entities': entity_data,
        'entities_json': json.dumps([{'name': e['company'], **e['stats']} for e in entity_data]),
    })


def form_automation_entity(request, entity_name):
    """Entity → Keyword Category drill-down with charts."""
    entity = _get_entity(entity_name)
    if not entity:
        from django.http import Http404
        raise Http404("Entity not found")

    from django.db.models import Count
    tasks = FormTask.objects.filter(entity_name=entity_name)
    stats = _entity_stats(entity_name)

    # Group by keyword_category
    categories = []
    cat_list = Lead.objects.exclude(website='').exclude(keyword_category='').values('keyword_category').annotate(total=Count('id')).order_by('-total')

    for c in cat_list:
        cat_name = c['keyword_category']
        cat_websites = set(Lead.objects.filter(keyword_category=cat_name).exclude(website='').values_list('website', flat=True))
        c_tasks = tasks.filter(website__in=cat_websites)
        categories.append({
            'name': cat_name,
            'total': c['total'],
            'websites': len(cat_websites),
            'success': c_tasks.filter(status='success').count(),
            'failed': c_tasks.filter(status='failed').count(),
            'running': c_tasks.filter(status='running').count(),
        })

    # Add "Others" for leads with no keyword_category
    others_leads = Lead.objects.filter(keyword_category='').exclude(website='')
    if others_leads.exists():
        others_websites = set(others_leads.values_list('website', flat=True))
        o_tasks = tasks.filter(website__in=others_websites)
        categories.append({
            'name': 'Others',
            'total': others_leads.count(),
            'websites': len(others_websites),
            'success': o_tasks.filter(status='success').count(),
            'failed': o_tasks.filter(status='failed').count(),
            'running': o_tasks.filter(status='running').count(),
        })

    return render(request, 'leads/master/form_automation_entity.html', {
        'active_nav': 'form_automation',
        'entity': entity, 'stats': stats,
        'stats_json': json.dumps(stats),
        'categories': categories,
        'categories_json': json.dumps(categories),
    })


def form_automation_category(request, entity_name, category):
    """Entity → Category → Countries."""
    entity = _get_entity(entity_name)
    if not entity:
        from django.http import Http404
        raise Http404("Entity not found")

    from django.db.models import Count
    tasks = FormTask.objects.filter(entity_name=entity_name)
    if category == 'Others':
        leads = Lead.objects.filter(keyword_category='').exclude(website='')
    else:
        leads = Lead.objects.filter(keyword_category=category).exclude(website='')

    countries = []
    for c in leads.exclude(country='').values('country').annotate(total=Count('id')).order_by('-total'):
        c_websites = set(leads.filter(country=c['country']).values_list('website', flat=True))
        c_tasks = tasks.filter(website__in=c_websites)
        countries.append({
            'name': c['country'],
            'total': c['total'],
            'websites': len(c_websites),
            'success': c_tasks.filter(status='success').count(),
            'failed': c_tasks.filter(status='failed').count(),
            'running': c_tasks.filter(status='running').count(),
        })

    all_websites = set(leads.values_list('website', flat=True))
    all_tasks = tasks.filter(website__in=all_websites)
    stats = {
        'total': leads.count(),
        'websites': len(all_websites),
        'success': all_tasks.filter(status='success').count(),
        'failed': all_tasks.filter(status='failed').count(),
        'running': all_tasks.filter(status='running').count(),
    }

    return render(request, 'leads/master/form_automation_cat.html', {
        'active_nav': 'form_automation',
        'entity': entity, 'category': category, 'stats': stats,
        'stats_json': json.dumps(stats),
        'countries': countries,
        'countries_json': json.dumps(countries),
    })


def form_automation_country(request, entity_name, country):
    """Entity → Category → Country → Region drill-down."""
    entity = _get_entity(entity_name)
    if not entity:
        from django.http import Http404
        raise Http404("Entity not found")

    category = request.GET.get('cat', '')
    tasks = FormTask.objects.filter(entity_name=entity_name)
    leads = Lead.objects.filter(country=country).exclude(website='')
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)

    # Build regions
    regions = {}
    for lead in leads:
        loc = lead.location or ''
        parts = [p.strip() for p in loc.split(',') if p.strip()]
        if len(parts) >= 2:
            region = parts[-2] if len(parts) >= 3 else parts[0]
        elif parts:
            region = parts[0]
        else:
            region = 'Unknown'
        if region not in regions:
            regions[region] = {'websites': set(), 'lead_count': 0}
        regions[region]['websites'].add(lead.website)
        regions[region]['lead_count'] += 1

    region_data = []
    for rname, rdata in regions.items():
        r_tasks = tasks.filter(website__in=rdata['websites'])
        region_data.append({
            'name': rname,
            'total': rdata['lead_count'],
            'websites': len(rdata['websites']),
            'success': r_tasks.filter(status='success').count(),
            'failed': r_tasks.filter(status='failed').count(),
            'running': r_tasks.filter(status='running').count(),
        })
    region_data.sort(key=lambda x: -x['total'])

    # Country-level stats
    all_websites = set(leads.values_list('website', flat=True))
    c_tasks = tasks.filter(website__in=all_websites)
    stats = {
        'total': leads.count(),
        'success': c_tasks.filter(status='success').count(),
        'failed': c_tasks.filter(status='failed').count(),
        'running': c_tasks.filter(status='running').count(),
    }

    return render(request, 'leads/master/form_automation_country.html', {
        'active_nav': 'form_automation',
        'entity': entity, 'country': country, 'category': category, 'stats': stats,
        'stats_json': json.dumps(stats),
        'regions': region_data,
        'regions_json': json.dumps(region_data),
    })


def form_automation_country_all(request, entity_name, country):
    """Entity → Country → All leads table with Start Automation."""
    entity = _get_entity(entity_name)
    if not entity:
        from django.http import Http404
        raise Http404("Entity not found")

    category = request.GET.get('cat', '')
    leads = Lead.objects.filter(country=country).exclude(website='')
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)
    leads = leads.order_by('id')  # Top-down order by ID
    tasks_map = {t.website: t for t in FormTask.objects.filter(entity_name=entity_name)}

    all_websites = set(leads.values_list('website', flat=True))
    t_qs = FormTask.objects.filter(entity_name=entity_name, website__in=all_websites)
    stats = {
        'total': leads.count(),
        'success': t_qs.filter(status='success').count(),
        'failed': t_qs.filter(status='failed').count(),
        'running': t_qs.filter(status='running').count(),
    }

    return render(request, 'leads/master/form_automation_country_all.html', {
        'active_nav': 'form_automation',
        'entity': entity, 'country': country, 'category': category,
        'stats': stats, 'leads': leads, 'tasks': tasks_map,
        'stats_json': json.dumps(stats),
    })


def form_automation_region(request, entity_name, country, region):
    """Entity → Country → Region → Leads table."""
    entity = _get_entity(entity_name)
    if not entity:
        from django.http import Http404
        raise Http404("Entity not found")

    category = request.GET.get('cat', '')
    leads = Lead.objects.filter(country=country, location__icontains=region).exclude(website='')
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)
    leads = leads.order_by('-created_at')
    tasks_map = {t.website: t for t in FormTask.objects.filter(entity_name=entity_name)}

    all_websites = set(leads.values_list('website', flat=True))
    t_qs = FormTask.objects.filter(entity_name=entity_name, website__in=all_websites)
    stats = {
        'total': leads.count(),
        'websites': len(all_websites),
        'success': t_qs.filter(status='success').count(),
        'failed': t_qs.filter(status='failed').count(),
        'running': t_qs.filter(status='running').count(),
    }

    return render(request, 'leads/master/form_automation_region.html', {
        'active_nav': 'form_automation',
        'entity': entity, 'country': country, 'region': region, 'category': category,
        'stats': stats, 'leads': leads, 'tasks': tasks_map,
        'stats_json': json.dumps(stats),
    })


@csrf_exempt
def form_automation_run(request):
    """Run form automation for a specific lead + entity in background."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        entity_name = body.get('entity_name')
        lead_id = body.get('lead_id')
        website = body.get('website')

        if not entity_name or not website:
            return JsonResponse({'error': 'entity_name and website required'}, status=400)

        entity = _get_entity(entity_name)
        if not entity:
            return JsonResponse({'error': 'Entity not found'}, status=404)

        # Find lead_id from website if not provided
        if not lead_id:
            lead = Lead.objects.filter(website=website).first()
            lead_id = lead.id if lead else None

        company_name = body.get('company_name', '')
        if not company_name and lead_id:
            try:
                company_name = Lead.objects.get(id=lead_id).company_name
            except Lead.DoesNotExist:
                pass

        # Create or update form task
        task, _ = FormTask.objects.update_or_create(
            entity_name=entity_name,
            website=website,
            defaults={
                'company_name': company_name,
                'lead_id': lead_id,
                'status': 'running',
                'message': 'Starting...',
            }
        )

        # Run in background
        import threading
        def bg_run():
            from django.db import close_old_connections
            close_old_connections()
            try:
                from form_automation.runner import fill_form
                result = fill_form(website, entity)
                close_old_connections()
                FormTask.objects.filter(id=task.id).update(
                    status=result['status'],
                    message=result['message']
                )
            except Exception as ex:
                close_old_connections()
                FormTask.objects.filter(id=task.id).update(
                    status='failed',
                    message=str(ex)[:200]
                )

        threading.Thread(target=bg_run, daemon=True).start()
        return JsonResponse({'task_id': task.id, 'status': 'running'})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def form_automation_run_batch(request):
    """Run form automation for all leads in a country/region sequentially in background."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        body = json.loads(request.body)
        entity_name = body.get('entity_name')
        country = body.get('country', '')
        region = body.get('region', '')
        category = body.get('category', '')

        entity = _get_entity(entity_name)
        if not entity:
            return JsonResponse({'error': 'Entity not found'}, status=404)

        # Get leads to process
        leads = Lead.objects.exclude(website='')
        if country:
            leads = leads.filter(country=country)
        if region:
            leads = leads.filter(location__icontains=region)
        if category == 'Others':
            leads = leads.filter(keyword_category='')
        elif category:
            leads = leads.filter(keyword_category=category)

        # Order by ID (top-down) and exclude already done or currently running
        leads = leads.order_by('id')
        skip_websites = set(FormTask.objects.filter(
            entity_name=entity_name,
            status__in=['success', 'failed', 'running']
        ).values_list('website', flat=True))
        seen = set()
        leads_to_process = []
        for l in leads:
            if l.website not in skip_websites and l.website not in seen:
                seen.add(l.website)
                leads_to_process.append((l.id, l.website, l.company_name))

        if not leads_to_process:
            return JsonResponse({'started': False, 'message': 'No leads to process (all done or no websites)'})

        # Generate unique batch_id for this run
        import uuid as _uuid
        batch_id = str(_uuid.uuid4())[:8]

        # Run strictly one-by-one in background thread
        import threading
        def bg_batch():
            from django.db import close_old_connections
            from form_automation.runner import fill_form
            import time as _time

            total = len(leads_to_process)
            for i, (lead_id, website, company_name) in enumerate(leads_to_process):
                close_old_connections()

                # Check if THIS batch was cancelled (not other batches)
                if FormTask.objects.filter(batch_id=batch_id, status='cancelled').exists():
                    break

                # Create/update task as running
                log_lines = f"[{i+1}/{total}] Batch:{batch_id} Starting: {website}\n"
                FormTask.objects.update_or_create(
                    entity_name=entity_name, website=website,
                    defaults={
                        'company_name': company_name, 'lead_id': lead_id,
                        'status': 'running', 'batch_id': batch_id,
                        'message': f'Processing ({i+1}/{total})...',
                        'logs': log_lines + 'Finding contact page...\n',
                    }
                )
                start_t = _time.time()
                try:
                    result = fill_form(website, entity)
                    elapsed = int(_time.time() - start_t)
                    close_old_connections()
                    log_lines += f"Result: {result['status']} — {result['message']}\nDuration: {elapsed}s\n"
                    FormTask.objects.filter(entity_name=entity_name, website=website).update(
                        status=result['status'], message=result['message'][:200], logs=log_lines
                    )
                except Exception as ex:
                    elapsed = int(_time.time() - start_t)
                    err_msg = str(ex)[:150]
                    if 'shutdown' in err_msg.lower():
                        close_old_connections()
                        FormTask.objects.filter(entity_name=entity_name, website=website).update(
                            status='pending', message='Server restarted — will retry', logs=log_lines + f"Interrupted: {err_msg}\n"
                        )
                        break
                    close_old_connections()
                    log_lines += f"Error: {err_msg}\nDuration: {elapsed}s\n"
                    FormTask.objects.filter(entity_name=entity_name, website=website).update(
                        status='failed', message=err_msg[:200], logs=log_lines
                    )
                    break

        threading.Thread(target=bg_batch, daemon=True).start()
        return JsonResponse({'started': True, 'total': len(leads_to_process), 'batch_id': batch_id, 'message': f'Processing {len(leads_to_process)} websites one-by-one'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
def form_automation_cancel(request, task_id):
    """Cancel a single running/pending task."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    try:
        task = FormTask.objects.get(id=task_id)
        if task.status in ('pending', 'running'):
            task.status = 'cancelled'
            task.message = 'Cancelled by user'
            task.save()
        return JsonResponse({'ok': True})
    except FormTask.DoesNotExist:
        return JsonResponse({'error': 'Not found'}, status=404)


@csrf_exempt
def form_automation_cancel_all(request):
    """Cancel all pending tasks for an entity."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    body = json.loads(request.body)
    entity_name = body.get('entity_name')
    count = FormTask.objects.filter(entity_name=entity_name, status__in=['pending', 'running']).update(
        status='cancelled', message='Cancelled by user'
    )
    return JsonResponse({'cancelled': count})


def form_automation_logs(request):
    """Get logs and ALL currently running tasks for an entity."""
    entity_name = request.GET.get('entity')
    if not entity_name:
        return JsonResponse({'error': 'entity required'}, status=400)

    running_tasks = FormTask.objects.filter(entity_name=entity_name, status='running')
    running_list = []
    for t in running_tasks:
        lead = t.lead
        running_list.append({
            'website': t.website,
            'company': t.company_name,
            'batch_id': t.batch_id,
            'country': lead.country if lead else '',
            'keyword': lead.keyword_category if lead else '',
        })

    # Latest task for logs
    task = running_tasks.first()
    if not task:
        task = FormTask.objects.filter(entity_name=entity_name).order_by('-created_at').first()

    return JsonResponse({
        'logs': task.logs if task else '',
        'website': task.website if task else '',
        'company': task.company_name if task else '',
        'status': task.status if task else 'idle',
        'message': task.message if task else '',
        'country': task.lead.country if task and task.lead else '',
        'keyword': task.lead.keyword_category if task and task.lead else '',
        'running_tasks': running_list,
    })


def form_automation_status(request):
    """Get status of form tasks for an entity, with counts filtered by country/region/category."""
    entity_name = request.GET.get('entity')
    if not entity_name:
        return JsonResponse({'error': 'entity param required'}, status=400)

    tasks = FormTask.objects.filter(entity_name=entity_name)

    # Filter tasks to the relevant scope
    country = request.GET.get('country', '')
    region = request.GET.get('region', '')
    category = request.GET.get('category', '')

    leads = Lead.objects.exclude(website='')
    if country:
        leads = leads.filter(country=country)
    if region:
        leads = leads.filter(location__icontains=region)
    if category == 'Others':
        leads = leads.filter(keyword_category='')
    elif category:
        leads = leads.filter(keyword_category=category)

    scoped_websites = set(leads.values_list('website', flat=True))
    scoped_tasks = tasks.filter(website__in=scoped_websites)

    task_data = {t.website: {'id': t.id, 'status': t.status, 'message': t.message} for t in scoped_tasks}

    # Count based on actual task statuses for websites in this scope
    success_count = scoped_tasks.filter(status='success').count()
    failed_count = scoped_tasks.filter(status='failed').count()
    running_count = scoped_tasks.filter(status='running').count()
    pending_count = scoped_tasks.filter(status='pending').count()

    counts = {
        'total': len(scoped_websites),
        'success': success_count,
        'failed': failed_count,
        'running': running_count,
        'pending': pending_count,
        'not_started': len(scoped_websites) - success_count - failed_count - running_count - pending_count,
    }

    return JsonResponse({'tasks': task_data, 'counts': counts})
