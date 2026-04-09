"""
Background task runner for lead generation (from lead_master).
All processing happens server-side in threads — survives page refresh/close.
"""
import threading
import time
import re
import logging
import unicodedata

import pycountry
import requests
from django.conf import settings

from .models import SearchSession, MasterLead as Lead

logger = logging.getLogger(__name__)

# ── Country normalizer ──

_country_lookup = {}
_US_STATES = {'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY','DC'}

def _build_country_lookup():
    if _country_lookup:
        return
    for c in pycountry.countries:
        name = unicodedata.normalize('NFD', c.name)
        name = ''.join(ch for ch in name if unicodedata.category(ch) != 'Mn')
        _country_lookup[c.alpha_2.upper()] = name
        _country_lookup[c.alpha_3.upper()] = name
        _country_lookup[name.upper()] = name
        if hasattr(c, 'common_name'):
            cn = unicodedata.normalize('NFD', c.common_name)
            cn = ''.join(ch for ch in cn if unicodedata.category(ch) != 'Mn')
            _country_lookup[cn.upper()] = cn

def normalize_country(val):
    if not val:
        return ''
    _build_country_lookup()
    val = val.strip()
    upper = val.upper()
    if upper in _country_lookup:
        return _country_lookup[upper]
    m = re.match(r'^([A-Z]{2})\s+\d{4,5}$', upper)
    if m and m.group(1) in _US_STATES:
        return 'United States'
    if upper in _US_STATES and upper not in _country_lookup:
        return 'United States'
    return val


def _update_progress(session_id, stage, detail='', pct=0):
    try:
        from django.db import close_old_connections
        close_old_connections()
        SearchSession.objects.filter(id=session_id).update(
            progress={'stage': stage, 'detail': detail, 'pct': pct}
        )
    except Exception:
        pass


def _save_leads_to_db(session_id, leads_data, source, keyword_category=''):
    from django.db import close_old_connections
    close_old_connections()
    session = SearchSession.objects.get(id=session_id)
    lead_objects = []
    for ld in leads_data:
        lead_objects.append(Lead(
            session=session,
            source=ld.get('source') or source,
            company_name=(ld.get('company_name') or '')[:500],
            industry=(ld.get('industry') or '')[:255],
            location=(ld.get('location') or '')[:500],
            emails=ld.get('emails') or [],
            phone=(ld.get('phone') or '')[:100],
            website=(ld.get('website') or '')[:500],
            linkedin_url=(ld.get('linkedin_url') or '')[:500],
            keyword=(ld.get('keyword') or '')[:255],
            keyword_category=keyword_category or (ld.get('keyword_category') or '')[:255],
            country=normalize_country(ld.get('country') or '')[:255],
            employee_count=ld.get('employee_count'),
            description=(ld.get('description') or ''),
            raw_data=ld.get('raw_data') or {},
        ))
    Lead.objects.bulk_create(lead_objects)
    session.lead_count = session.leads.count()
    session.save(update_fields=['lead_count'])
    return lead_objects


def _find_emails_for_leads(session_id, lead_ids):
    from django.db import close_old_connections
    from .email_finder import find_emails_bulk
    close_old_connections()

    leads = Lead.objects.filter(id__in=lead_ids)
    _update_progress(session_id, 'Finding emails', f'Scanning {leads.count()} websites...', 80)
    find_emails_bulk(leads, session_id)


def _search_apollo(session_id, keywords, location, kw_str):
    _update_progress(session_id, 'Apollo', 'Searching...', 10)
    try:
        base_body = {'per_page': 100, 'q_organization_keyword_tags': keywords}
        if location:
            base_body['organization_locations'] = [location]

        resp = requests.post(
            'https://api.apollo.io/v1/organizations/search',
            json={**base_body, 'page': 1},
            headers={'Content-Type': 'application/json', 'X-Api-Key': settings.APOLLO_API_KEY},
            timeout=30,
        )
        if resp.status_code != 200:
            return []

        data = resp.json()
        combined = list(data.get('organizations', []))
        total_pages = data.get('pagination', {}).get('total_pages', 1)

        for p in range(2, total_pages + 1):
            _update_progress(session_id, 'Apollo', f'Page {p}/{total_pages}', 10 + int((p/total_pages)*20))
            pr = requests.post(
                'https://api.apollo.io/v1/organizations/search',
                json={**base_body, 'page': p},
                headers={'Content-Type': 'application/json', 'X-Api-Key': settings.APOLLO_API_KEY},
                timeout=30,
            )
            if pr.status_code != 200:
                break
            combined.extend(pr.json().get('organizations', []))

        leads = []
        for org in combined:
            leads.append({
                'source': 'apollo',
                'company_name': org.get('name', ''),
                'industry': org.get('industry', ''),
                'location': ', '.join(filter(None, [org.get('city'), org.get('state'), org.get('country')])),
                'phone': org.get('phone') or (org.get('primary_phone', {}) or {}).get('number', ''),
                'website': org.get('website_url', ''),
                'linkedin_url': org.get('linkedin_url', ''),
                'keyword': kw_str,
                'country': org.get('country', ''),
                'raw_data': org,
            })
        return leads
    except Exception as e:
        logger.error(f"Apollo search failed: {e}")
        return []


def _search_google_maps(session_id, keywords, location, kw_str, max_results=50):
    from .views_master import _apify_request
    _update_progress(session_id, 'Google Maps', 'Starting scraper...', 15)
    try:
        input_data = {
            'searchStringsArray': keywords,
            'locationQuery': location,
            'maxCrawledPlacesPerSearch': max_results,
            'maximumLeadsEnrichmentRecords': 0, 'language': 'en',
            'includeWebResults': False, 'scrapeContacts': False,
            'scrapeDirectories': False, 'scrapeImageAuthors': False,
            'scrapePlaceDetailPage': False, 'scrapeReviewsPersonalData': True,
            'scrapeSocialMediaProfiles': {'facebooks': False, 'instagrams': False, 'tiktoks': False, 'twitters': False, 'youtubes': False},
            'scrapeTableReservationProvider': False, 'skipClosedPlaces': False,
            'searchMatching': 'all', 'placeMinimumStars': '', 'website': 'allPlaces',
            'maxQuestions': 0, 'maxReviews': 0, 'reviewsSort': 'newest',
            'reviewsFilterString': '', 'reviewsOrigin': 'all', 'maxImages': 0,
            'allPlacesNoSearchAction': '',
        }
        resp = _apify_request('POST', '/v2/acts/compass~crawler-google-places/runs', settings.APIFY_GOOGLE_MAP_API_KEY, json_body=input_data)
        resp_data = resp.json()
        run_id = resp_data.get('data', {}).get('id')
        if not run_id:
            return []

        while True:
            time.sleep(3)
            sr = _apify_request('GET', f'/v2/actor-runs/{run_id}', settings.APIFY_GOOGLE_MAP_API_KEY)
            status = sr.json().get('data', {}).get('status', '')
            if status == 'SUCCEEDED':
                break
            elif status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                return []
            _update_progress(session_id, 'Google Maps', f'Scraping... ({status})', 25)

        rr = _apify_request('GET', f'/v2/actor-runs/{run_id}/dataset/items?format=json', settings.APIFY_GOOGLE_MAP_API_KEY)
        rr_data = rr.json()
        items = rr_data if isinstance(rr_data, list) else []

        seen = set()
        unique = []
        for item in items:
            key = item.get('placeId') or item.get('title', '')
            if key not in seen:
                seen.add(key)
                unique.append(item)

        leads = []
        for b in unique:
            leads.append({
                'source': 'google_maps',
                'company_name': b.get('title') or b.get('name', ''),
                'industry': b.get('categoryName', ''),
                'location': b.get('address', ''),
                'phone': b.get('phone', ''),
                'website': b.get('website', ''),
                'keyword': kw_str,
                'country': (b.get('address', '').split(',')[-1].strip() if b.get('address') else ''),
                'raw_data': b,
            })
        return leads
    except Exception as e:
        logger.error(f"Google Maps search failed: {e}")
        return []


def _search_linkedin(session_id, keywords, locations, kw_str):
    from .views_master import _apify_request
    _update_progress(session_id, 'LinkedIn', 'Starting scraper...', 20)
    try:
        input_data = {
            'action': 'get-companies',
            'isName': False, 'isUrl': False,
            'keywords': keywords,
            'location': locations,
            'limit': 1000,
        }
        resp = _apify_request('POST', '/v2/acts/bebity~linkedin-premium-actor/runs', settings.APIFY_LINKEDIN_API_KEY, json_body=input_data)
        resp_data = resp.json()
        run_id = resp_data.get('data', {}).get('id')
        if not run_id:
            return []

        while True:
            time.sleep(3)
            sr = _apify_request('GET', f'/v2/actor-runs/{run_id}', settings.APIFY_LINKEDIN_API_KEY)
            status = sr.json().get('data', {}).get('status', '')
            if status == 'SUCCEEDED':
                break
            elif status in ('FAILED', 'ABORTED', 'TIMED-OUT'):
                return []
            _update_progress(session_id, 'LinkedIn', f'Scraping... ({status})', 30)

        rr = _apify_request('GET', f'/v2/actor-runs/{run_id}/dataset/items?format=json', settings.APIFY_LINKEDIN_API_KEY)
        rr_data = rr.json()
        items = rr_data if isinstance(rr_data, list) else []

        seen = set()
        unique = []
        for item in items:
            key = item.get('url') or item.get('name', '')
            if key not in seen:
                seen.add(key)
                unique.append(item)

        leads = []
        for b in unique:
            hq = b.get('headquarter') or {}
            leads.append({
                'source': 'linkedin',
                'company_name': b.get('name', ''),
                'industry': ', '.join(b.get('industry', [])),
                'location': ', '.join(filter(None, [hq.get('city'), hq.get('country')])),
                'website': b.get('websiteUrl', ''),
                'linkedin_url': b.get('url', ''),
                'keyword': kw_str,
                'country': hq.get('country', ''),
                'employee_count': b.get('employeeCount'),
                'description': (b.get('description') or '')[:500],
                'raw_data': b,
            })
        return leads
    except Exception as e:
        logger.error(f"LinkedIn search failed: {e}")
        return []


def run_master_search(session_id, keywords, locations, sources, keyword_category=''):
    from django.db import connection
    connection.close()

    try:
        kw_str = ', '.join(keywords) if isinstance(keywords, list) else keywords
        location_str = locations[0] if locations else ''
        all_lead_ids = []

        if 'Apollo' in sources:
            _update_progress(session_id, 'Apollo', 'Searching...', 5)
            apollo_leads = _search_apollo(session_id, keywords, location_str, kw_str)
            if apollo_leads:
                saved = _save_leads_to_db(session_id, apollo_leads, 'apollo', keyword_category)
                all_lead_ids.extend([l.id for l in saved])
                _update_progress(session_id, 'Apollo', f'{len(apollo_leads)} leads found', 30)
            else:
                _update_progress(session_id, 'Apollo', 'No results or failed', 30)

        if 'Google Maps' in sources:
            _update_progress(session_id, 'Google Maps', 'Starting...', 35)
            gmaps_leads = _search_google_maps(session_id, keywords, location_str, kw_str)
            if gmaps_leads:
                saved = _save_leads_to_db(session_id, gmaps_leads, 'google_maps', keyword_category)
                all_lead_ids.extend([l.id for l in saved])
                _update_progress(session_id, 'Google Maps', f'{len(gmaps_leads)} leads found', 55)
            else:
                _update_progress(session_id, 'Google Maps', 'No results or failed', 55)

        if 'LinkedIn' in sources:
            _update_progress(session_id, 'LinkedIn', 'Starting...', 60)
            linkedin_leads = _search_linkedin(session_id, keywords, locations, kw_str)
            if linkedin_leads:
                saved = _save_leads_to_db(session_id, linkedin_leads, 'linkedin', keyword_category)
                all_lead_ids.extend([l.id for l in saved])
                _update_progress(session_id, 'LinkedIn', f'{len(linkedin_leads)} leads found', 75)
            else:
                _update_progress(session_id, 'LinkedIn', 'No results or failed', 75)

        if all_lead_ids:
            _update_progress(session_id, 'Finding emails', f'Scanning {len(all_lead_ids)} websites...', 80)
            _find_emails_for_leads(session_id, all_lead_ids)

        from django.db import close_old_connections
        close_old_connections()
        session = SearchSession.objects.get(id=session_id)
        session.status = 'completed' if session.lead_count > 0 else 'failed'
        session.progress = {'stage': 'Done', 'detail': f'{session.lead_count} leads', 'pct': 100}
        session.save()

    except Exception as e:
        logger.error(f"Master search failed for session {session_id}: {e}")
        try:
            from django.db import close_old_connections
            close_old_connections()
            session = SearchSession.objects.get(id=session_id)
            session.status = 'failed'
            session.progress = {'stage': 'Error', 'detail': str(e)[:100], 'pct': 0}
            session.save()
        except Exception:
            pass


def start_master_search_bg(session_id, keywords, locations, sources, keyword_category=''):
    t = threading.Thread(
        target=run_master_search,
        args=(session_id, keywords, locations, sources, keyword_category),
        daemon=True,
    )
    t.start()
    return t
