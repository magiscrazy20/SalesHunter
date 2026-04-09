"""
Form automation runner — fills contact forms on websites.
Uses the ContactFormAutomation engine from form_engine.py.
Callable from Django views.
"""
import json
import os
import sys
import logging
import time

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def load_entities():
    entities_file = os.path.join(BASE_DIR, 'entities.json')
    with open(entities_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_entity(company_name):
    for e in load_entities():
        if e['company'] == company_name:
            return e
    return None


def fill_form(url, entity_data):
    """
    Fill a contact form on the given URL with entity data.
    Creates a fresh browser, processes one URL, then closes.
    Max 60s per URL to prevent hanging.
    """
    automation = None
    start = time.time()
    try:
        sys.path.insert(0, BASE_DIR)
        from form_engine import ContactFormAutomation

        automation = ContactFormAutomation(headless=True)
        automation.contact_data = {
            'name': entity_data.get('name', ''),
            'first_name': entity_data.get('first_name', ''),
            'last_name': entity_data.get('last_name', ''),
            'company': entity_data.get('company', ''),
            'email': entity_data.get('email', ''),
            'phone': entity_data.get('phone', ''),
            'subject': entity_data.get('subject', 'I would like to buy your service.'),
            'message': entity_data.get('message', ''),
            'teams_id': entity_data.get('teams_link', ''),
        }

        logger.info(f"Form fill: {entity_data.get('company')} -> {url}")
        automation.setup_driver()

        # Set shorter timeouts on the driver
        try:
            automation.driver.set_page_load_timeout(30)
            automation.driver.set_script_timeout(20)
        except Exception:
            pass

        contact_url = automation.find_contact_page(url)
        elapsed = time.time() - start

        if elapsed > 120:
            return {'status': 'failed', 'message': f'Timeout finding contact page ({int(elapsed)}s)'}

        if contact_url:
            success = automation._fill_contact_form()
            elapsed = time.time() - start
            if success:
                return {'status': 'success', 'message': f'Submitted ({int(elapsed)}s)'}
            else:
                return {'status': 'failed', 'message': f'Could not fill form ({int(elapsed)}s)'}
        else:
            return {'status': 'failed', 'message': f'No contact page ({int(elapsed)}s)'}

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Form error {url}: {e}")
        return {'status': 'failed', 'message': f'{str(e)[:150]} ({int(elapsed)}s)'}
    finally:
        if automation:
            try:
                automation.cleanup()
            except Exception:
                pass
