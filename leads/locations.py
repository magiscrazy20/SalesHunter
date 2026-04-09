"""
Location service:
- pycountry for countries (249 countries, offline)
- CountriesNow free API for states and cities (live, cached)
- Curated locations.json as fast fallback
"""
import unicodedata
import json
import os
import logging

import pycountry
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_states_cache = {}
_cities_cache = {}


def _normalize(text):
    normalized = unicodedata.normalize('NFD', text)
    return ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')


def get_all_countries():
    return sorted([
        {'code': c.alpha_2, 'name': _normalize(c.name)}
        for c in pycountry.countries
    ], key=lambda x: x['name'])


def get_states(country_code):
    if country_code in _states_cache:
        return _states_cache[country_code]

    country = pycountry.countries.get(alpha_2=country_code)
    country_name = _normalize(country.name) if country else ''

    states = _fetch_states_from_api(country_name)
    if not states:
        states = _get_states_pycountry(country_code)

    _states_cache[country_code] = states
    return states


def _fetch_states_from_api(country_name):
    try:
        resp = requests.get(
            'https://countriesnow.space/api/v0.1/countries/states/q',
            params={'country': country_name},
            timeout=8,
        )
        if resp.status_code == 200:
            data = resp.json()
            if not data.get('error'):
                raw_states = data.get('data', {}).get('states', [])
                return sorted([
                    {'code': '', 'name': _normalize(s.get('name', ''))}
                    for s in raw_states if s.get('name')
                ], key=lambda x: x['name'])
    except Exception as e:
        logger.debug(f"CountriesNow states API failed: {e}")
    return []


def _get_states_pycountry(country_code):
    try:
        subs = pycountry.subdivisions.get(country_code=country_code)
        states = []
        seen = set()
        for s in subs:
            if s.parent_code is None:
                name = _normalize(s.name)
                if name not in seen:
                    seen.add(name)
                    states.append({'code': s.code, 'name': name})
        return sorted(states, key=lambda x: x['name'])
    except Exception:
        return []


def get_cities(country_code, state_name):
    cache_key = f"{country_code}:{state_name}"
    if cache_key in _cities_cache:
        return _cities_cache[cache_key]

    country = pycountry.countries.get(alpha_2=country_code)
    country_name = _normalize(country.name) if country else ''

    cities = _get_cities_curated(country_name, state_name)
    if not cities:
        cities = _fetch_cities_from_api(country_name, state_name)

    _cities_cache[cache_key] = cities
    return cities


def _get_cities_curated(country_name, state_name):
    cities_file = os.path.join(settings.BASE_DIR, 'static', 'data', 'locations.json')
    try:
        with open(cities_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception:
        return []

    country_data = data.get(country_name, {})
    if state_name in country_data:
        return country_data[state_name]
    norm_state = _normalize(state_name)
    for key, cities in country_data.items():
        if _normalize(key) == norm_state:
            return cities
    return []


def _fetch_cities_from_api(country_name, state_name):
    try:
        resp = requests.get(
            'https://countriesnow.space/api/v0.1/countries/state/cities/q',
            params={'country': country_name, 'state': state_name},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            if not data.get('error'):
                raw_cities = data.get('data', [])
                return [_normalize(c) for c in raw_cities if c and len(c) > 1]
    except Exception as e:
        logger.debug(f"CountriesNow cities API failed: {e}")
    return []
