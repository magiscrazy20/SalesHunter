"""
High-speed multi-strategy email finder.
All strategies run in PARALLEL — first result wins.
"""
import re
import html
import logging
import concurrent.futures
from urllib.parse import urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BLOCKED = {
    'example.com', 'email.com', 'domain.com', 'yoursite.com', 'sentry.io',
    'webpack.js', 'wixpress.com', 'googleapis.com', 'schema.org',
    'w3.org', 'cloudflare.com', 'jquery.com', 'google.com', 'googleusercontent.com',
    'gstatic.com', 'facebook.com', 'twitter.com', 'youtube.com',
    '.png', '.jpg', '.gif', '.svg', '.css', '.js', '.woff', '.ico',
}

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Encoding': 'gzip, deflate',
}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

_http_session = None


def _get_http_session():
    global _http_session
    if _http_session is None:
        _http_session = requests.Session()
        _http_session.headers.update(HEADERS)
        adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
        _http_session.mount('http://', adapter)
        _http_session.mount('https://', adapter)
    return _http_session


def _clean_emails(raw_emails):
    seen = set()
    result = []
    for e in raw_emails:
        e = e.lower().strip('.')
        if e in seen or len(e) > 60:
            continue
        if any(b in e for b in BLOCKED):
            continue
        seen.add(e)
        result.append(e)
    return result


def _extract_from_html(html_text):
    if not html_text:
        return []
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)
    decoded = html.unescape(cleaned)
    decoded = re.sub(r'\s*[\[\(\{]\s*at\s*[\]\)\}]\s*', '@', decoded, flags=re.IGNORECASE)
    decoded = re.sub(r'\s*[\[\(\{]\s*dot\s*[\]\)\}]\s*', '.', decoded, flags=re.IGNORECASE)
    return _clean_emails(EMAIL_RE.findall(decoded))


def _fetch_page(url, timeout=4):
    try:
        resp = _get_http_session().get(url, timeout=timeout, allow_redirects=True)
        return resp.text[:200000] if resp.status_code == 200 else ''
    except Exception:
        return ''


# ─── Strategy 1: Parallel page scrape (fastest) ───

def strategy_fast_scrape(base_url):
    if not base_url:
        return []
    base = base_url.rstrip('/')
    if not base.startswith('http'):
        base = 'https://' + base

    paths = ['', '/contact', '/contact-us', '/about', '/about-us', '/contactus']
    urls = [base + p for p in paths]

    all_emails = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        futures = {pool.submit(_fetch_page, u, 4): u for u in urls}
        for f in concurrent.futures.as_completed(futures):
            emails = _extract_from_html(f.result())
            if emails:
                all_emails.extend(emails)
                for remaining in futures:
                    remaining.cancel()
                break

    return _clean_emails(all_emails)


# ─── Strategy 2: Google dork search ───

def strategy_google_search(domain):
    if not domain:
        return []
    try:
        resp = _get_http_session().get(
            'https://www.google.com/search',
            params={'q': f'"{domain}" email OR contact', 'num': 10},
            headers={**HEADERS, 'Accept-Language': 'en-US,en;q=0.9'},
            timeout=5,
        )
        if resp.status_code == 200:
            found = _extract_from_html(resp.text)
            return _clean_emails([e for e in found if domain in e])
    except Exception:
        pass
    return []


# ─── Strategy 3: AI extraction (fast model only) ───

def strategy_ai_extract(website_url, domain):
    if not website_url:
        return []
    base = website_url.rstrip('/')
    if not base.startswith('http'):
        base = 'https://' + base

    page_html = _fetch_page(base, timeout=4)
    if not page_html:
        return []

    text = re.sub(r'<[^>]+>', ' ', page_html)
    text = re.sub(r'\s+', ' ', text).strip()[:3000]
    if len(text) < 50:
        return []

    try:
        resp = requests.post(
            'https://integrate.api.nvidia.com/v1/chat/completions',
            headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {settings.NVIDIA_API_KEY}'},
            json={
                'model': 'meta/llama-3.1-8b-instruct',
                'messages': [{'role': 'user', 'content': f'List every email address found in this text from {domain}. One per line. If none, say NONE.\n\n{text}'}],
                'temperature': 0, 'max_tokens': 200, 'stream': False,
            },
            timeout=8,
        )
        content = resp.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        return _clean_emails(EMAIL_RE.findall(content))
    except Exception:
        return []


# ─── Strategy 4: Selenium (JS sites — last resort) ───

_selenium_driver = None
_selenium_lock = None


def _get_selenium_driver():
    global _selenium_driver, _selenium_lock
    import threading
    if _selenium_lock is None:
        _selenium_lock = threading.Lock()

    with _selenium_lock:
        if _selenium_driver is not None:
            try:
                _selenium_driver.title
                return _selenium_driver
            except Exception:
                try:
                    _selenium_driver.quit()
                except Exception:
                    pass
                _selenium_driver = None

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager

            options = Options()
            options.add_argument('--headless=new')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-extensions')
            options.add_argument('--blink-settings=imagesEnabled=false')
            options.page_load_strategy = 'eager'

            service = Service(ChromeDriverManager().install())
            _selenium_driver = webdriver.Chrome(service=service, options=options)
            _selenium_driver.set_page_load_timeout(5)
            _selenium_driver.implicitly_wait(1)
            return _selenium_driver
        except Exception as e:
            logger.error(f"Selenium init failed: {e}")
            return None


def strategy_selenium_scrape(website_url):
    if not website_url:
        return []
    base = website_url.rstrip('/')
    if not base.startswith('http'):
        base = 'https://' + base

    driver = _get_selenium_driver()
    if not driver:
        return []

    for path in ['', '/contact']:
        try:
            driver.get(base + path)
            import time
            time.sleep(0.5)
            emails = _extract_from_html(driver.page_source)
            if emails:
                return _clean_emails(emails)
        except Exception:
            continue
    return []


# ─── Master finder: ALL strategies run in PARALLEL ───

def find_emails_fast(website_url, domain=None):
    if not website_url and not domain:
        return []

    if not domain and website_url:
        try:
            parsed = urlparse(website_url if website_url.startswith('http') else 'https://' + website_url)
            domain = parsed.hostname.replace('www.', '') if parsed.hostname else ''
        except Exception:
            domain = ''

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        future_scrape = pool.submit(strategy_fast_scrape, website_url)
        future_google = pool.submit(strategy_google_search, domain)
        future_ai = pool.submit(strategy_ai_extract, website_url, domain)

        futures = [future_scrape, future_google, future_ai]
        for f in concurrent.futures.as_completed(futures):
            try:
                result = f.result()
                if result:
                    for other in futures:
                        other.cancel()
                    return result
            except Exception:
                continue

    return strategy_selenium_scrape(website_url)


def find_emails_bulk(leads_queryset, session_id=None):
    """Find emails for multiple leads — 10 concurrent workers."""
    from .models import MasterLead as Lead
    import threading

    leads_to_scan = [(l.id, l.website) for l in leads_queryset if l.website and not l.emails]
    total = len(leads_to_scan)
    if not total:
        return 0

    found_count = 0
    done_count = 0
    lock = threading.Lock()

    def scan_one(lead_id, website):
        nonlocal found_count, done_count
        try:
            from django.db import close_old_connections
            close_old_connections()

            domain = ''
            try:
                parsed = urlparse(website if website.startswith('http') else 'https://' + website)
                domain = parsed.hostname.replace('www.', '') if parsed.hostname else ''
            except Exception:
                pass

            emails = find_emails_fast(website, domain)
            if emails:
                Lead.objects.filter(id=lead_id).update(emails=emails)
                with lock:
                    found_count += 1
        except Exception as e:
            logger.error(f"Email scan failed for lead {lead_id}: {e}")
        finally:
            with lock:
                done_count += 1
            if session_id and done_count % 3 == 0:
                from .tasks_master import _update_progress
                pct = 80 + int((done_count / total) * 20)
                _update_progress(session_id, 'Finding emails', f'{done_count}/{total}', pct)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [pool.submit(scan_one, lid, ws) for lid, ws in leads_to_scan]
        concurrent.futures.wait(futures)

    return found_count
