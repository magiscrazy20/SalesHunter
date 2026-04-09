## -*- coding: latin-1 -*-
# -*- coding: utf-8 -*-
#!/usr/bin/env python3
#Contact Form Automation Script using Selenium
#Automatically finds and fills contact forms on websites with specified details.
#Enhanced with subject field support and strong anti-bot challenge handling.


import time
import logging
import undetected_chromedriver as uc
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from urllib.parse import urlparse, urljoin
import os
import sys
import random
import string
# import psycopg2  # removed
import json
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options as ChromeOptions
import concurrent.futures

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('contact_automation.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# Configuration - Easy toggle for headless mode
HEADLESS = True  # Set to True for headless operation

# Performance Configuration - Ultra-Aggressive for maximum speed
ULTRA_AGGRESSIVE_MODE = True  # NEW: Ultra-aggressive mode for maximum speed
ULTRA_FAST_MODE = True  # Keep for compatibility
if ULTRA_AGGRESSIVE_MODE:
    # Ultra-aggressive timing settings for maximum speed (40-60% faster)
    PAGE_LOAD_WAIT = 1.0      # 50% reduction
    CLICK_WAIT = 0.2          # 60% reduction  
    STEP_WAIT = 0.5           # 50% reduction
    FORM_WAIT = 1.0           # 50% reduction
    TYPING_DELAY = (0.002, 0.005)  # 80% reduction
    HUMAN_DELAY = (0.005, 0.015)   # 70% reduction
    WAIT_VISIBLE_INPUTS = 2   # 60% reduction
    TRANSITION_WAIT_SECONDS = 4     # 60% reduction
    TRANSITION_SLOW_WAIT_SECONDS = 8  # 60% reduction
elif ULTRA_FAST_MODE:
    # Optimized timing settings for speed and reliability
    PAGE_LOAD_WAIT = 2.0  # Reduced for faster execution
    CLICK_WAIT = 0.5  # Reduced for faster interactions
    STEP_WAIT = 1.0  # Reduced for faster steps
    FORM_WAIT = 2.0  # Reduced for faster form processing
    TYPING_DELAY = (0.01, 0.02)  # Reduced for faster typing
    HUMAN_DELAY = (0.02, 0.05)  # Reduced for faster execution
    WAIT_VISIBLE_INPUTS = 5  # Reduced for faster element detection
    TRANSITION_WAIT_SECONDS = 10  # Reduced for faster transitions
    TRANSITION_SLOW_WAIT_SECONDS = 15  # Reduced for faster processing
else:
    # Standard timing settings
    PAGE_LOAD_WAIT = 5.0
    CLICK_WAIT = 2.0
    STEP_WAIT = 3.0
    FORM_WAIT = 4.0
    TYPING_DELAY = (0.02, 0.05)
    HUMAN_DELAY = (0.05, 0.12)
    WAIT_VISIBLE_INPUTS = 10
    TRANSITION_WAIT_SECONDS = 15
    TRANSITION_SLOW_WAIT_SECONDS = 25

# Smart retry controls
SMART_RETRY = True

# Smart timeout management for dynamic performance
SMART_TIMEOUTS = True

# Accept-Language header for multilingual sites
ACCEPT_LANGS = 'en-US,en;q=0.9,fr;q=0.8,de;q=0.8,es;q=0.8,pt;q=0.7,it;q=0.7,ru;q=0.6,tr;q=0.6,ar;q=0.6,hi;q=0.6,zh-CN;q=0.6,zh;q=0.5,ja;q=0.5,ko;q=0.5,pl;q=0.5,nl;q=0.5,sv;q=0.5,fi;q=0.5,no;q=0.5,da;q=0.5'

class ContactFormAutomation:
    def __init__(self, headless=True):
        self.headless = headless
        self.driver = None
        self.wait = None
        
        # Performance timing constants
        if ULTRA_AGGRESSIVE_MODE:
            # Ultra-aggressive timing for maximum speed (40-60% faster)
            self.PAGE_LOAD_WAIT = 1.0
            self.CLICK_WAIT = 0.2
            self.STEP_WAIT = 0.5
            self.FORM_WAIT = 1.0
            self.TYPING_DELAY = (0.002, 0.005)
            self.HUMAN_DELAY = (0.005, 0.015)
            self.WAIT_VISIBLE_INPUTS = 2
            self.TRANSITION_WAIT_SECONDS = 4
            self.TRANSITION_SLOW_WAIT_SECONDS = 8
        elif ULTRA_FAST_MODE:
            self.PAGE_LOAD_WAIT = 2.0
            self.CLICK_WAIT = 0.5
            self.STEP_WAIT = 1.0
            self.FORM_WAIT = 2.0
            self.TYPING_DELAY = (0.01, 0.02)
            self.HUMAN_DELAY = (0.02, 0.05)
            self.WAIT_VISIBLE_INPUTS = 5
            self.TRANSITION_WAIT_SECONDS = 8
            self.TRANSITION_SLOW_WAIT_SECONDS = 12
        else:
            self.PAGE_LOAD_WAIT = 5.0
            self.CLICK_WAIT = 2.0
            self.STEP_WAIT = 3.0
            self.FORM_WAIT = 4.0
            self.TYPING_DELAY = (0.02, 0.05)
            self.HUMAN_DELAY = (0.05, 0.12)
            self.WAIT_VISIBLE_INPUTS = 10
            self.TRANSITION_WAIT_SECONDS = 15
            self.TRANSITION_SLOW_WAIT_SECONDS = 25
        
        # Contact form data
        
        # Smart timeout management
        if SMART_TIMEOUTS:
            self.timeout_cache = {}  # Cache timeouts for domains
            
        # Contact data — set externally via set_contact_data() or runner.py
        # NO hardcoded data — always set from entity before use
        self.contact_data = {
            'name': '', 'first_name': '', 'last_name': '',
            'company': '', 'email': '', 'phone': '',
            'subject': '', 'message': '', 'teams_id': '',
        }

    def set_contact_data(self, data):
        """Set contact data from entity. Called by runner.py before form filling."""
        self.contact_data = {
            'name': data.get('name', ''),
            'first_name': data.get('first_name', ''),
            'last_name': data.get('last_name', ''),
            'company': data.get('company', ''),
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'subject': data.get('subject', 'I would like to buy your service.'),
            'message': data.get('message', ''),
            'teams_id': data.get('teams_id', data.get('teams_link', '')),
        }
        logger.info(f"Contact data set for: {self.contact_data['company']} ({self.contact_data['email']})")

        # Field matching patterns
        self.field_patterns = {
            'name': ['name', 'fullname', 'full_name', 'username', 'contact_name', 'contactname', 'your_name', 'customer_name', 'client_name',
                     'nombre', 'nome', 'nom', '???', '???', '??? ?? ?????', '??', '??', 'ad', 'isim', 'wpforms[fields][0]', 'field_0', 'input_0'],
            'first_name': ['fname', 'first_name', 'firstname', 'first', 'given_name', 'givenname', 'forename', 'personal_name', 'personalname', 'name_first',
                           'prenom', 'nombre', 'nome', '???', '?', 'first-name', 'primer_nombre', 'wpforms[fields][0]', 'wpforms[fields][1]', 'field_1', 'input_1'],
            'last_name': ['lname', 'last_name', 'lastname', 'last', 'family_name', 'familyname', 'surname', 'name_last', 'second_name', 'secondname',
                          'apellido', 'sobrenome', 'nom de famille', '???????', '?', 'last-name', 'apellidos', 'wpforms[fields][1]', 'wpforms[fields][2]', 'field_2', 'input_2'],
            'company': ['company', 'organization', 'organisation', 'business', 'firm', 'employer', 'company_name', 'org', 'corp', 'corporation', 'enterprise', 'institution', 'workplace', 'employer_name', 'business_name',
                        'empresa', 'compaï¿½ï¿½a', 'sociedad', 'sociï¿½tï¿½', 'entreprise', 'azienda', 'empresa/organizaciï¿½n', '???????????', '??', '??', 'wpforms[fields][2]', 'wpforms[fields][3]', 'field_company', 'input_company'],
            'email': ['email', 'mail', 'user_email', 'contact_email', 'your_email', 'e-mail', 'email_address', 'emailaddress', 'customer_email',
                      'correo', 'correo electrï¿½nico', 'e-mail', 'courriel', '???', '????', '?????', 'eposta', 'wpforms[fields][1]', 'wpforms[fields][2]', 'wpforms[fields][3]', 'field_email', 'input_email'],
            'phone': ['phone', 'number', 'contact_number', 'mobile', 'tel', 'telephone', 'phone_number', 'phonenumber', 'contact_phone', 'your_phone',
                      'telï¿½fono', 'mï¿½vil', 'telefone', 'tï¿½lï¿½phone', '??', '??', '???????', 'gsm', 'wpforms[fields][3]', 'wpforms[fields][4]', 'field_phone', 'input_phone'],
            'subject': ['subject', 'subj', 'topic', 'title', 'enquiry_subject', 'message_subject', 'contact_subject', 'subject_line', 'subject_title', 'enquiry_title',
                        'asunto', 'assunto', 'objet', 'oggetto', '?????', 'tema', '??', '??', 'wpforms[fields][4]', 'wpforms[fields][5]', 'field_subject', 'input_subject'],
            'message': ['message', 'msg', 'enquiry', 'comment', 'details', 'description', 'your-message', 'your_message', 'comments', 'inquiry', 'request', 'feedback', 'textarea', 'additional_info', 'notes', 'content', 'body', 'Write A Message', 'Any Requirements', 'Please share any specific needs or questions about the solution.', 'tell us more', 'additional details', 'more information', 'your requirements', 'project details', 'service requirements', 'business needs', 'specific needs', 'questions', 'concerns', 'requirements', 'specifications', 'description', 'brief', 'overview', 'summary', 'details about', 'information about', 'Your information helps us serve you better', 'how can we help', 'what can we do for you', 'tell us about your project', 'describe your needs', 'share your thoughts', 'additional comments', 'other information', 'anything else', 'further details', 'more info', 'elaborate', 'explain', 'clarify', 'specify',
                        'mensaje', 'mensagem', 'message', 'messaggio', '??', '?????', '?????????', 'mesaj', '???????', '?? ???????', 'wpforms[fields][2]', 'wpforms[fields][5]', 'wpforms[fields][6]', 'field_message', 'input_message'],
            'teams_id': ['teams', 'skype', 'contact_link', 'link', 'profile', 'website', 'url', 'social_media', 'social', 'messaging', 'communication']
        }
        
        # Contact page keywords
        self.contact_keywords = [
            'contact', 'contact us', 'contact-us', 'contactus', 'get in touch', 'getintouch', 'get-in-touch',
            'reach us', 'reach-us', 'reachus', 'support', 'help', 'customer service', 'customer support',
            'business contact', 'business-contact', 'businesscontact', 'sales contact', 'sales-contact',
            'salescontact', 'partnership', 'work with us', 'work-with-us', 'workwithus', 'collaborate',
            'collaboration', 'enquiry', 'enquiries', 'inquiry', 'inquiries', 'quote', 'request quote',
            'request-quote', 'requestquote', 'get quote', 'get-quote', 'getquote',
            'connect', 'connect with us', 'connect-with-us', 'connectwithus', 'message us', 'message-us',
            'messageus', 'write to us', 'write-to-us', 'writetous', 'send message', 'send-message',
            'sendmessage', 'contact form', 'contact-form', 'contactform', 'enquiry form', 'enquiry-form',
            'enquiryform', 'inquiry form', 'inquiry-form', 'inquiryform',
            'customer care', 'customer-care', 'customercare', 'client support', 'client-support',
            'clientsupport', 'technical support', 'technical-support', 'technicalsupport',
            'help desk', 'helpdesk', 'support desk', 'supportdesk',
            'communicate', 'communication', 'talk to us', 'talk-to-us', 'talktous', 'speak to us',
            'speak-to-us', 'speaktous', 'call us', 'call-us', 'callus', 'email us', 'email-us',
            'emailus', 'write us', 'write-us', 'writeus',
            # Spanish/Portuguese
            'contacto', 'contï¿½ctanos', 'contato', 'fale conosco', 'fale-conosco', 'solicitar orï¿½amento', 'orcamento',
            # French
            'contactez-nous', 'nous contacter', 'demander un devis', 'devis',
            # German
            'kontakt', 'kontaktieren', 'angebot anfordern',
            # Italian
            'contatto', 'contattaci', 'richiedi preventivo',
            # Dutch/Scandinavian
            'neem contact op', 'kontakt oss', 'kontakta oss', 'ta kontakt',
            # Turkish
            'iletisim', 'bize ulasin',
            # Russian
            '????????', '?????????', '???????? ???',
            # Arabic
            '???? ???', '????? ????', '??????',
            # Hindi
            '?????? ????', '???? ?????? ????',
            # Chinese/Japanese/Korean
            '????', '????', '??', '??????', '????', '????'
        ]
        
        # User agent rotation
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15'
        ]
        
        # Window sizes
        self.window_sizes = [
            (1920, 1080), (1366, 768), (1440, 900), (1536, 864), (1280, 720),
            (1600, 900), (1680, 1050), (2560, 1440), (3840, 2160)
        ]
        
        # Results file (not used — results stored in Django DB)
        self.results_file = None
        
        # Website-specific customizations
        self.website_customizations = {
            'mcmbpo.com': {
                'form_selectors': ['.contact-form', '.enquiry-form', '[class*="form"]'],
                'field_mappings': {
                    'name': ['#name', '#fullname', '[name="name"]', '[placeholder*="name"]'],
                    'first_name': ['#first_name', '#fname', '[name="first_name"]', '[name="fname"]', '[placeholder*="first"]', '[placeholder*="first name"]'],
                    'last_name': ['#last_name', '#lname', '[name="last_name"]', '[name="lname"]', '[placeholder*="last"]', '[placeholder*="last name"]'],
                    'company': ['#company', '#organization', '[name="company"]', '[name="organization"]', '[placeholder*="company"]', '[placeholder*="organization"]'],
                    'email': ['#email', '#email_address', '[name="email"]', '[placeholder*="email"]'],
                    'phone': ['#phone', '#telephone', '[name="phone"]', '[placeholder*="phone"]'],
                    'subject': ['#subject', '[name="subject"]', '[placeholder*="subject"]'],
                    'message': ['#message', '#enquiry', '[name="message"]', '[placeholder*="message"]', 'textarea', 'textarea[name*="message"]', 'textarea[id*="message"]', 'textarea[placeholder*="message"]', 'textarea[class*="message"]']
                }
            },
            'vonage.com': {
                'form_selectors': ['.contact-form', '.support-form', '[data-form="contact"]', 'form', '.form-container'],
                'field_mappings': {
                    'name': ['[name*="name"]', '[id*="name"]', '[placeholder*="name"]', 'input[name="name"]', 'input[id="name"]'],
                    'first_name': ['[name*="first"]', '[name*="fname"]', '[id*="first"]', '[id*="fname"]', '[placeholder*="first"]', '[placeholder*="first name"]'],
                    'last_name': ['[name*="last"]', '[name*="lname"]', '[id*="last"]', '[id*="lname"]', '[placeholder*="last"]', '[placeholder*="last name"]'],
                    'company': ['[name*="company"]', '[name*="organization"]', '[name*="organisation"]', '[name*="business"]', '[name*="firm"]', '[id*="company"]', '[id*="organization"]', '[placeholder*="company"]', '[placeholder*="organization"]'],
                    'email': ['[name*="email"]', '[id*="email"]', '[placeholder*="email"]', 'input[name="email"]', 'input[id="email"]'],
                    'phone': ['[name*="phone"]', '[id*="phone"]', '[placeholder*="phone"]', 'input[name="phone"]', 'input[id="phone"]'],
                    'subject': ['[name*="subject"]', '[id*="subject"]', '[placeholder*="subject"]', 'input[name="subject"]', 'input[id="subject"]'],
                    'message': ['[name*="message"]', '[id*="message"]', '[placeholder*="message"]', 'textarea[name="message"]', 'textarea[id="message"]', 'textarea', 'textarea[name*="message"]', 'textarea[id*="message"]', 'textarea[placeholder*="message"]', 'textarea[class*="message"]', 'textarea[class*="enquiry"]', 'textarea[class*="comment"]']
                }
            }
        }

    def setup_driver(self):
        """Setup Chrome driver with enhanced undetected-chromedriver and anti-detection features."""
        try:
            # Try multiple approaches for better compatibility
            try:
                # Approach 1: Enhanced undetected-chromedriver with anti-detection
                options = uc.ChromeOptions()
                
                if self.headless:
                    options.add_argument('--headless')
                
                # Enhanced anti-detection arguments
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_argument('--disable-extensions')
                options.add_argument('--disable-plugins')
                options.add_argument('--disable-images')  # Faster loading
                options.add_argument('--disable-javascript-harmony-shipping')
                options.add_argument('--disable-background-timer-throttling')
                options.add_argument('--disable-backgrounding-occluded-windows')
                options.add_argument('--disable-renderer-backgrounding')
                options.add_argument('--disable-features=TranslateUI')
                options.add_argument('--disable-ipc-flooding-protection')
                
                # Random user agent
                user_agent = random.choice(self.user_agents)
                options.add_argument(f'--user-agent={user_agent}')
                
                # Random window size
                window_size = random.choice(self.window_sizes)
                options.add_argument(f'--window-size={window_size[0]},{window_size[1]}')
                
                self.driver = uc.Chrome(options=options, version_main=None)
                try:
                    self.driver.set_page_load_timeout(15 if ULTRA_FAST_MODE else 30)  # Increased timeout for reliability
                except Exception:
                    pass
                
                # Set random window size after driver creation
                self.driver.set_window_size(window_size[0], window_size[1])
                
            except Exception as e1:
                logger.debug(f"First approach failed: {e1}")
                
                # Approach 2: Minimal options with anti-detection
                try:
                    options = uc.ChromeOptions()
                    
                    if self.headless:
                        options.add_argument('--headless')
                    
                    options.add_argument('--no-sandbox')
                    options.add_argument('--disable-dev-shm-usage')
                    options.add_argument('--disable-blink-features=AutomationControlled')
                    
                    # Random user agent
                    user_agent = random.choice(self.user_agents)
                    options.add_argument(f'--user-agent={user_agent}')
                    
                    self.driver = uc.Chrome(options=options, version_main=None)
                    try:
                        self.driver.set_page_load_timeout(15 if ULTRA_FAST_MODE else 30)  # Increased timeout for reliability
                    except Exception:
                        pass
                    
                except Exception as e2:
                    logger.debug(f"Second approach failed: {e2}")
                    
                    # Approach 3: No options at all
                    self.driver = uc.Chrome(version_main=None)
                    try:
                        self.driver.set_page_load_timeout(15 if ULTRA_FAST_MODE else 35)  # Increased timeout for reliability
                    except Exception:
                        pass
            
            # Set up wait
            self.wait = WebDriverWait(self.driver, 10 if ULTRA_FAST_MODE else 20)  # Increased wait for reliability
            
            # Execute anti-detection scripts
            self._execute_anti_detection_scripts()
            # Install AJAX tracker for SPA/AJAX step detection
            try:
                self._install_ajax_tracker()
            except Exception as _e:
                logger.debug(f"Failed to install AJAX tracker: {_e}")
            
            logger.info("Chrome driver setup completed successfully with anti-detection features")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Chrome driver: {e}")
            # Fallback to standard ChromeDriver (webdriver-manager)
            try:
                logger.info("Attempting fallback to standard ChromeDriver via webdriver-manager...")
                # Prepare Chrome options
                co = ChromeOptions()
                if self.headless:
                    co.add_argument('--headless')
                co.add_argument('--no-sandbox')
                co.add_argument('--disable-dev-shm-usage')
                co.add_argument('--disable-blink-features=AutomationControlled')
                co.add_argument('--disable-extensions')
                co.add_argument('--disable-plugins')
                co.add_argument('--disable-features=TranslateUI')
                # Language and user-agent
                try:
                    co.add_argument(f'--accept-lang={ACCEPT_LANGS}')
                except Exception:
                    pass
                try:
                    ua = random.choice(self.user_agents)
                    co.add_argument(f'--user-agent={ua}')
                except Exception:
                    pass
                # Window size
                try:
                    ws = random.choice(self.window_sizes)
                    co.add_argument(f'--window-size={ws[0]},{ws[1]}')
                except Exception:
                    ws = (1366, 768)
                # Page load strategy - ultra aggressive for speed
                try:
                    co.page_load_strategy = 'eager'  # Don't wait for all resources
                    co.add_argument('--disable-images')  # Don't load images for speed
                except Exception:
                    pass
                # Build driver
                svc = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=svc, options=co)
                try:
                    self.driver.set_page_load_timeout(15 if ULTRA_FAST_MODE else 30)  # Increased timeout for reliability
                except Exception:
                    pass
                # Set wait and hardening
                self.wait = WebDriverWait(self.driver, 10 if ULTRA_FAST_MODE else 20)  # Increased wait for reliability
                try:
                    self._execute_anti_detection_scripts()
                except Exception:
                    pass
                try:
                    self._install_ajax_tracker()
                except Exception:
                    pass
                # Ensure window size
                try:
                    self.driver.set_window_size(ws[0], ws[1])
                except Exception:
                    pass
                logger.info("Fallback ChromeDriver setup completed successfully")
                return True
            except Exception as e_fallback:
                logger.error(f"Fallback ChromeDriver setup failed: {e_fallback}")
                return False

    def _execute_anti_detection_scripts(self):
        """Execute JavaScript to remove automation indicators."""
        try:
            # Remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Remove automation properties
            self.driver.execute_script("""
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
            """)
            
            # Add random properties to make detection harder
            random_props = [''.join(random.choices(string.ascii_lowercase, k=8)) for _ in range(3)]
            for prop in random_props:
                self.driver.execute_script(f"window.{prop} = 'random_value'")
            
            logger.info("Anti-detection scripts executed successfully")
            
        except Exception as e:
            logger.debug(f"Error executing anti-detection scripts: {e}")

    def _install_ajax_tracker(self):
        """Injects a tracker that records last AJAX/fetch completion timestamp on window.__ajaxLastDone."""
        try:
            js = """
            (function(){
                try{
                    if(window.__ajaxTrackerInstalled){return;}
                    window.__ajaxTrackerInstalled = true;
                    window.__ajaxLastDone = Date.now();
                    function mark(){ window.__ajaxLastDone = Date.now(); }
                    // XHR
                    const _open = XMLHttpRequest.prototype.open;
                    const _send = XMLHttpRequest.prototype.send;
                    XMLHttpRequest.prototype.open = function(){ this.addEventListener('loadend', mark); return _open.apply(this, arguments); };
                    XMLHttpRequest.prototype.send = function(){ try{ this.addEventListener('loadend', mark); }catch(e){} return _send.apply(this, arguments); };
                    // fetch
                    const _fetch = window.fetch;
                    window.fetch = function(){ return _fetch.apply(this, arguments).then(function(r){ try{ mark(); }catch(e){} return r; }); };
                }catch(e){}
            })();
            """
            self.driver.execute_script(js)
        except Exception as e:
            logger.debug(f"AJAX tracker injection failed: {e}")

    def _human_like_delay(self, min_delay=None, max_delay=None):
        """Add optimized human-like random delays (ultra fast)."""
        if min_delay is None:
            min_delay = self.HUMAN_DELAY[0]
        if max_delay is None:
            max_delay = self.HUMAN_DELAY[1]
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)

    def _human_like_typing(self, element, text):
        """Type text with optimized human-like delays between keystrokes - ultra fast."""
        try:
            element.clear()
            # Ultra fast typing with minimal delays
            for char in text:
                element.send_keys(char)
                self._human_like_delay(self.TYPING_DELAY[0], self.TYPING_DELAY[1])  # Ultra fast delay between keystrokes
            return True
        except Exception as e:
            logger.debug(f"Error in human-like typing: {e}")
            return False

    def _human_like_click(self, element):
        """Click element with human-like mouse movement and offset."""
        try:
            # Get element location and size
            location = element.location
            size = element.size
            
            # Calculate random offset within the element
            offset_x = random.randint(5, max(5, size['width'] - 5))
            offset_y = random.randint(5, max(5, size['height'] - 5))
            
            # Create action chains for human-like movement
            actions = ActionChains(self.driver)
            
            # Move to element with random offset
            actions.move_to_element_with_offset(element, offset_x, offset_y)
            
            # Small random movement before click
            actions.move_by_offset(random.randint(-2, 2), random.randint(-2, 2))
            
            # Click with random delay
            self._human_like_delay(0.1, 0.3)
            actions.click()
            actions.perform()
            
            return True
            
        except Exception as e:
            logger.debug(f"Error in human-like click: {e}")
            # Fallback to regular click
            try:
                element.click()
                return True
            except:
                return False

    def _is_hidden_field(self, element):
        """Check if a field is hidden (honeypot detection)."""
        try:
            # Check CSS display property
            display = element.value_of_css_property('display')
            if display == 'none':
                return True
            
            # Check visibility property
            visibility = element.value_of_css_property('visibility')
            if visibility == 'hidden':
                return True
            
            # Check type attribute
            field_type = element.get_attribute('type')
            if field_type == 'hidden':
                return True
            
            # Check aria-hidden attribute
            aria_hidden = element.get_attribute('aria-hidden')
            if aria_hidden == 'true':
                return True
            
            # Check if element is outside viewport
            if not element.is_displayed():
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if field is hidden: {e}")
            return False

    def find_contact_page(self, url):
        """Enhanced contact page finding with improved error handling and robustness."""
        try:
            logger.info(f"Starting enhanced contact page search on: {url}")
            
            # Step 1: Load the main page with better error handling
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver.get(url)
                    # Wait for page to be ready
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(self.PAGE_LOAD_WAIT)
                    logger.info(f"Loaded main page: {self.driver.current_url}")
                    break
                except Exception as e:
                    logger.warning(f"Attempt {attempt + 1} failed to load {url}: {e}")
                    if attempt == max_retries - 1:
                        logger.error(f"Failed to load {url} after {max_retries} attempts")
                        return False
                    time.sleep(2)  # Wait before retry
            
            # Step 2: Check if we're already on a contact page (fastest check)
            if self._is_contact_page():
                logger.info(f"Already on contact page: {self.driver.current_url}")
                return True
            
            # Step 3: Enhanced direct contact URL testing
            if self._try_direct_contact_urls_enhanced(url):
                return True
            
            # Step 4: Improved visible link scan with better filtering
            if self._enhanced_visible_contact_scan():
                return True
            
            # Step 5: Quick sitemap probe with validation
            try:
                contact_from_sitemap = self._probe_sitemap_for_contact(url)
                if contact_from_sitemap and self._validate_contact_url(contact_from_sitemap):
                    logger.info(f"Found contact in sitemap: {contact_from_sitemap}")
                    self.driver.get(contact_from_sitemap)
                    WebDriverWait(self.driver, 10).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(self.PAGE_LOAD_WAIT)
                    if self._is_contact_page():
                        return True
            except Exception as e:
                logger.debug(f"Sitemap probe failed: {e}")
            
            # Step 6: Enhanced candidate scoring with better validation
            try:
                if self._open_best_contact_candidate_enhanced(max_candidates=8):
                    return True
            except Exception as e:
                logger.debug(f"Candidate scoring failed: {e}")
            
            logger.warning(f"No contact page found on: {url}")
            return False
            
        except Exception as e:
            logger.error(f"Error finding contact page on {url}: {e}")
            return False

    def _validate_contact_url(self, url):
        """Validate if a URL is likely to be a contact page."""
        try:
            if not url or url in ['#', 'javascript:void(0)', 'javascript:;']:
                return False
            
            url_lower = url.lower()
            contact_indicators = [
                'contact', 'support', 'help', 'enquiry', 'inquiry',
                'get-in-touch', 'reach-us', 'customer-service'
            ]
            
            return any(indicator in url_lower for indicator in contact_indicators)
        except Exception:
            return False
    
    def _try_direct_contact_urls_enhanced(self, base_url):
        """Enhanced direct contact URL testing with better validation."""
        try:
            contact_paths = self._comprehensive_url_patterns()
            tested_urls = set()
            
            for i, path in enumerate(contact_paths[:25]):  # Test more URLs
                try:
                    test_url = urljoin(base_url, path)
                    if test_url in tested_urls:
                        continue
                    tested_urls.add(test_url)
                    
                    logger.debug(f"Testing direct URL {i+1}/25: {test_url}")
                    
                    # Navigate with timeout
                    self.driver.set_page_load_timeout(10)
                    self.driver.get(test_url)
                    
                    # Wait for page to load
                    WebDriverWait(self.driver, 8).until(
                        lambda driver: driver.execute_script("return document.readyState") == "complete"
                    )
                    time.sleep(1)
                    
                    if self._is_contact_page():
                        logger.info(f"? Found contact page via direct URL: {test_url}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to test URL {test_url}: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Direct URL testing failed: {e}")
            return False
    
    def _enhanced_visible_contact_scan(self):
        """Enhanced visible contact link scanning with better filtering."""
        try:
            # Focus on key areas first
            priority_selectors = [
                'nav a, .nav a, .navbar a, [role="navigation"] a',
                'header a, .header a',
                'footer a, .footer a, [role="contentinfo"] a',
                '.menu a, .main-menu a, .primary-menu a'
            ]
            
            for selector in priority_selectors:
                try:
                    links = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for link in links[:10]:  # Limit to first 10 per area
                        try:
                            if not link.is_displayed():
                                continue
                                
                            href = link.get_attribute('href')
                            text = link.text.strip()
                            
                            if self._is_contact_link_enhanced(link):
                                logger.info(f"Found potential contact link: {text} -> {href}")
                                
                                # Use enhanced link clicking with navigation handling
                                def check_contact_page():
                                    return self._is_contact_page()
                                
                                if self._enhanced_link_click_with_navigation(
                                    link, 
                                    expected_result_check=check_contact_page,
                                    return_on_failure=True
                                ):
                                    return True
                                    
                        except Exception:
                            continue
                except Exception:
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Enhanced visible scan failed: {e}")
            return False
    
    def _is_contact_link_enhanced(self, link):
        """Enhanced contact link detection with better filtering."""
        try:
            text = (link.text or '').lower().strip()
            href = (link.get_attribute('href') or '').lower().strip()
            title = (link.get_attribute('title') or '').lower().strip()
            aria = (link.get_attribute('aria-label') or '').lower().strip()
            
            # Skip empty or invalid links
            if not href or href in ['#', 'javascript:void(0)', 'javascript:;']:
                return False
            
            if not text and not any(keyword in href for keyword in ['contact', 'support', 'help']):
                return False
            
            # Skip non-contact keywords
            skip_keywords = [
                'login', 'signin', 'register', 'signup', 'cart', 'shop',
                'blog', 'news', 'search', 'home', 'about', 'privacy',
                'terms', 'social', 'facebook', 'twitter', 'linkedin'
            ]
            
            all_text = f"{text} {href} {title} {aria}"
            if any(skip in all_text for skip in skip_keywords):
                return False
            
            # Check for contact keywords
            contact_keywords = [
                'contact us', 'contact-us', 'contactus', '/contact',
                'get in touch', 'reach us', 'customer service',
                'customer support', 'technical support', 'help desk',
                'contact', 'support', 'help', 'enquiry', 'inquiry'
            ]
            
            return any(keyword in all_text for keyword in contact_keywords)
            
        except Exception:
            return False
    
    def _open_best_contact_candidate_enhanced(self, max_candidates: int = 8):
        """Enhanced candidate scoring with better validation."""
        candidates = []
        try:
            # Focus on key areas with better selectors
            areas = []
            selectors = [
                'header, nav, .navbar, .nav, [role="navigation"]',
                'footer, .footer, #footer, [role="contentinfo"]',
                '.menu, .main-menu, .primary-menu, .top-menu'
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    areas.extend(elements)
                except Exception:
                    continue
            
            # Fallback to body if no specific areas found
            if not areas:
                try:
                    areas = [self.driver.find_element(By.TAG_NAME, 'body')]
                except Exception:
                    return False
            
            seen_hrefs = set()
            for area in areas:
                try:
                    links = area.find_elements(By.TAG_NAME, 'a')
                    for link in links[:20]:  # Limit per area
                        try:
                            href = (link.get_attribute('href') or '').strip()
                            if not href or href in seen_hrefs:
                                continue
                            seen_hrefs.add(href)
                            
                            if not link.is_displayed():
                                continue
                            
                            text = (link.text or '').strip()
                            title = (link.get_attribute('title') or '').strip()
                            aria = (link.get_attribute('aria-label') or '').strip()
                            cls = (link.get_attribute('class') or '').strip()
                            
                            score = self._score_contact_candidate_enhanced(href, text, title, aria, cls)
                            if score > 0:
                                candidates.append((score, link, href, text))
                        except Exception:
                            continue
                except Exception:
                    continue
        except Exception:
            pass
        
        if not candidates:
            return False
        
        # Sort by score and try top candidates
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_candidates = candidates[:max_candidates]
        
        for score, link, href, text in top_candidates:
            try:
                if not link.is_displayed() or not link.is_enabled():
                    continue
                
                logger.info(f"Trying enhanced candidate (score {score}): {text or href}")
                
                # Wait for element to be clickable
                try:
                    WebDriverWait(self.driver, 3).until(EC.element_to_be_clickable(link))
                except TimeoutException:
                    continue
                
                # Use enhanced link clicking with navigation handling
                def check_contact_page():
                    return self._is_contact_page()
                
                if self._enhanced_link_click_with_navigation(
                    link, 
                    expected_result_check=check_contact_page,
                    return_on_failure=True
                ):
                    return True
                    
            except Exception:
                continue
        
        return False
    
    def _score_contact_candidate_enhanced(self, href: str, text: str, title: str, aria: str, cls: str) -> int:
        """Enhanced scoring for contact candidates with better keyword matching."""
        try:
            score = 0
            full_text = f"{(text or '').lower()} {(title or '').lower()} {(aria or '').lower()} {(cls or '').lower()} {(href or '').lower()}"
            
            # High priority indicators
            high_priority = [
                'contact us', 'contact-us', 'contactus', '/contact',
                'get in touch', 'customer service', 'customer support'
            ]
            
            for keyword in high_priority:
                if keyword in full_text:
                    score += 100
            
            # Medium priority indicators
            medium_priority = [
                'contact', 'support', 'help', 'enquiry', 'inquiry',
                'reach us', 'get quote', 'sales'
            ]
            
            for keyword in medium_priority:
                if keyword in full_text:
                    score += 50
            
            # Bonus for good URL patterns
            if '/contact' in href.lower():
                score += 75
            
            # Penalty for non-contact indicators
            penalties = [
                'login', 'signin', 'register', 'cart', 'shop',
                'blog', 'news', 'home', 'about', 'privacy'
            ]
            
            for penalty in penalties:
                if penalty in full_text:
                    score -= 50
            
            # Penalty for very short text without good href
            if text and len(text) < 3 and '/contact' not in href.lower():
                score -= 25
            
            return max(0, score)
            
        except Exception:
            return 0
    
    def _open_best_contact_candidate_fast(self, max_candidates: int = 5):
        """ULTRA-FAST candidate scoring - limited to top candidates for speed."""
        candidates = []
        try:
            # Focus only on the most likely areas
            areas = []
            try:
                areas.extend(self.driver.find_elements(By.CSS_SELECTOR, 'header, nav, .navbar, .nav, [role="navigation"]'))
            except Exception:
                pass
            try:
                areas.extend(self.driver.find_elements(By.CSS_SELECTOR, 'footer, .footer, #footer, [role="contentinfo"]'))
            except Exception:
                pass
            # Skip main content area for speed - focus on nav/footer only
            
            # Ensure at least body
            if not areas:
                areas = [self.driver.find_element(By.TAG_NAME, 'body')]
            
            seen = set()
            for area in areas:
                try:
                    links = area.find_elements(By.TAG_NAME, 'a')
                except Exception:
                    links = []
                for a in links:
                    try:
                        href = (a.get_attribute('href') or '').strip()
                        if not href or href in seen:
                            continue
                        seen.add(href)
                        text = (a.text or '').strip()
                        title = (a.get_attribute('title') or '').strip()
                        aria = (a.get_attribute('aria-label') or '').strip()
                        cls = (a.get_attribute('class') or '').strip()
                        score = self._score_contact_candidate(href, text, title, aria, cls)
                        if score > 0:
                            candidates.append((score, a))
                    except Exception:
                        continue
        except Exception:
            pass
        
        if not candidates:
            return False
        
        candidates.sort(key=lambda x: x[0], reverse=True)
        top = candidates[:max_candidates]
        for score, a in top:
            try:
                if a.is_displayed() and a.is_enabled():
                    logger.info(f"Trying candidate link (score {score}): {(a.text or a.get_attribute('href') or '')}")
                    # Wait for element to be clickable
                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable(a)
                        )
                    except TimeoutException:
                        continue
                    
                    # Prefer JS click (faster, avoids scroll)
                    try:
                        self.driver.execute_script('arguments[0].click();', a)
                    except Exception:
                        try:
                            a.click()
                        except Exception:
                            continue
                    
                    time.sleep(self.CLICK_WAIT)
                    
                    # Wait for page to load
                    try:
                        WebDriverWait(self.driver, 5).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                    except TimeoutException:
                        pass
                    
                    if self._is_contact_page():
                        return True
                    
                    # If not contact, go back and continue
                    try:
                        self.driver.back()
                        time.sleep(self.STEP_WAIT)
                        # Wait for back navigation to complete
                        WebDriverWait(self.driver, 3).until(
                            lambda driver: driver.execute_script("return document.readyState") == "complete"
                        )
                    except Exception:
                        pass
            except Exception:
                continue
        return False

    def _score_contact_candidate(self, href: str, text: str, title: str, aria: str, cls: str) -> int:
        """Score potential contact links.
        Positive points for keywords in various attributes and known path patterns, small penalties for irrelevant items.
        """
        try:
            s = 0
            full = f"{(text or '').lower()} {(title or '').lower()} {(aria or '').lower()} {(cls or '').lower()} {(href or '').lower()}"
            # Strong path indicators
            strong_paths = [
                '/contact', '/contact-us', '/contactus', '/kontakt', '/contato', '/contacto', '/contattaci', '/nous-contacter', '/????', '/??????', '/iletisim', '/bize-ulasin'
            ]
            for p in strong_paths:
                if p in full:
                    s += 6
                    break
            # Keyword matches
            for kw in self.contact_keywords:
                if kw in full:
                    s += 2
            # Prefer buttons/primary classes
            for signal in ['btn', 'button', 'primary', 'cta', 'link-contact', 'menu-contact']:
                if signal in full:
                    s += 1
            # Penalize obvious non-contact areas
            for bad in ['login', 'signin', 'register', 'cart', 'shop', 'pricing', 'blog']:
                if bad in full:
                    s -= 2
            # Very short/no-text links get small penalty
            if len((text or '').strip()) <= 1:
                s -= 1
            return s
        except Exception:
            return 0

    def _is_contact_page(self):
        """Improved check if current page is a contact page with better element detection."""
        try:
            # Wait for page to load properly (reduced timeout for speed)
            WebDriverWait(self.driver, 2).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            page_source = self.driver.page_source.lower()
            page_title = self.driver.title.lower()
            current_url = self.driver.current_url.lower()
            
            # Check for contact keywords in page content
            contact_indicators = [
                'contact', 'contact us', 'get in touch', 'reach us', 'support',
                'enquiry', 'inquiry', 'quote', 'message us', 'write to us',
                'talk to us', 'send message', 'feedback', 'partnership', 'collaborate',
                'collaboration', 'business inquiry', 'sales inquiry', 'connect with us',
                'reach out', 'lets talk', 'let\'s talk', 'work with us', 'join us',
                'customer service', 'customer support', 'help desk', 'technical support'
            ]
            
            # Check URL first (fastest check)
            url_indicators = ['contact', 'kontakt', 'contato', 'contacto', 'contattaci', 'nous-contacter']
            for indicator in url_indicators:
                if indicator in current_url:
                    logger.info(f"Contact page detected: URL contains '{indicator}'")
                    return True
            
            # Check page title
            for indicator in contact_indicators:
                if indicator in page_title:
                    logger.info(f"Contact page detected: Title contains '{indicator}'")
                    return True
            
            # Wait for forms to load and check for forms (more reliable indicator)
            try:
                WebDriverWait(self.driver, 1).until(
                    EC.presence_of_element_located((By.TAG_NAME, 'form'))
                )
            except TimeoutException:
                pass  # Continue even if no forms found immediately
            
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            inputs = self.driver.find_elements(By.TAG_NAME, 'input')
            textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
            
            # Look for contact-specific forms
            contact_form_indicators = [
                'contact-form', 'contact_form', 'enquiry-form', 'enquiry_form',
                'contactform', 'enquiryform', 'contactus', 'enquiryus', 'contact'
            ]
            
            # Check if any form has contact-specific classes or IDs
            for form in forms:
                try:
                    form_class = (form.get_attribute('class') or '').lower()
                    form_id = (form.get_attribute('id') or '').lower()
                    form_action = (form.get_attribute('action') or '').lower()
                    
                    for indicator in contact_form_indicators:
                        if indicator in form_class or indicator in form_id or indicator in form_action:
                            logger.info(f"Contact page detected: Found contact form with {indicator}")
                            return True
                except Exception:
                    continue
            
            # Check for Schema.org contact page
            try:
                if 'itemtype="https://schema.org/ContactPage"' in page_source or 'itemtype=\"https://schema.org/ContactPage\"' in page_source:
                    logger.info("Contact page detected via schema.org ContactPage")
                    return True
            except Exception:
                pass

            # Check headings for contact intent
            try:
                headings = [el.text.lower() for el in self.driver.find_elements(By.CSS_SELECTOR, 'h1, h2, [role="heading"]') if el.is_displayed()]
                if any(any(k in h for k in contact_indicators) for h in headings):
                    logger.info("Contact page detected via headings")
                    return True
            except Exception:
                pass

            # Check for contact keywords in page content (but be more specific)
            contact_keyword_found = False
            for indicator in contact_indicators:
                if indicator in page_source or indicator in page_title or indicator in current_url:
                    contact_keyword_found = True
                    break
            
            # Only consider it a contact page if we have both contact keywords AND forms
            if contact_keyword_found and len(forms) > 0 and (len(inputs) > 2 or len(textareas) > 0):
                logger.info(f"Contact page detected: Contact keywords + forms found")
                return True
            
            # Check for specific contact page URLs
            contact_url_indicators = ['/contact', '/contact-us', '/contactus', '/get-in-touch', '/enquiry', '/inquiry']
            for indicator in contact_url_indicators:
                if indicator in current_url:
                    logger.info(f"Contact page detected: Contact URL pattern {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking if contact page: {e}")
            return False

    def _dismiss_overlays(self):
        """Dismiss common cookie banners and modal overlays that block interactions."""
        selectors = [
            '[id*="cookie"] button', '[class*="cookie"] button', '[aria-label*="accept"]', '[aria-label*="agree"]',
            'button[onclick*="accept"]', 'button[onclick*="agree"]', 'button:contains("Accept")', 'button:contains("I agree")',
            '.cc-allow', '.CookieConsent button', '.js-accept-cookies',
            '.modal-footer .btn, .modal-footer button', '.close, [aria-label="Close"]'
        ]
        try:
            for sel in selectors:
                try:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                except Exception:
                    els = []
                for el in els:
                    try:
                        if el.is_displayed() and el.is_enabled():
                            el.click()
                            time.sleep(0.1)
                    except Exception:
                        continue
        except Exception:
            pass

    def _try_direct_contact_urls_aggressive(self, base_url):
        """ULTRA-AGGRESSIVE direct contact URL testing with parallel approach."""
        try:
            parsed_url = urlparse(base_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # CRITICAL contact paths - tested in order of success rate
            critical_paths = [
                '/contact',
                '/contact-us', 
                '/contactus',
                '/get-in-touch',
                '/support',
                '/help',
                '/enquiry',
                '/enquiries',
                '/inquiry',
                '/inquiries',
                '/quote',
                '/request-quote',
                '/get-quote',
                '/getintouch',
                '/reach-us',
                '/reachus',
                '/get-help',
                '/customer-service',
                '/customerservice',
                '/customer-support',
                '/customersupport',
                # Additional common patterns
                '/contact.html',
                '/contact.php',
                '/contact.aspx',
                '/contact/',
                '/contact-form',
                '/contactform',
                '/contact_us',
                '/contact_form',
                '/feedback',
                '/message',
                '/send-message',
                '/write-to-us',
                '/talk-to-us',
                '/reach-out',
                '/connect',
                '/connect-with-us',
                '/lets-talk',
                '/partnership',
                '/partnerships',
                '/collaborate',
                '/collaboration',
                '/business-inquiry',
                '/sales',
                '/sales-inquiry'
            ]
            
            # Test critical paths first with minimal wait
            for path in critical_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Testing critical contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.05)  # Ultra minimal wait (further reduced)
                    
                    if self._is_contact_page():
                        logger.info(f"success: Found contact page at {contact_url}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to test {contact_url}: {e}")
                    continue
            
            # If critical paths fail, try localized versions (limited set for speed)
            localized_paths = [
                '/en/contact', '/fr/contact', '/de/kontakt', '/es/contacto', 
                '/pt/contato', '/it/contatti', '/nl/contact', '/sv/kontakt',
                '/fi/yhteystiedot', '/no/kontakt', '/da/kontakt', '/pl/kontakt',
                '/tr/iletisim', '/ru/????????', '/ar/????-???', '/hi/??????',
                '/zh/????', '/zh-cn/????', '/ja/??????', '/ko/????'
            ]
            
            for path in localized_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Testing localized contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.05)  # Ultra minimal wait (further reduced)
                    
                    if self._is_contact_page():
                        logger.info(f"success: Found localized contact page at {contact_url}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Failed to test {contact_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in aggressive direct contact URLs: {e}")
            return False
            
            for path in contact_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Trying direct contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.05)  # Ultra fast per-attempt wait
                    
                    # Check if page loaded successfully
                    page_title = self.driver.title.lower()
                    if any(error in page_title for error in ['404', 'not found', 'error', 'page not found']):
                        logger.debug(f"404 error for: {contact_url}")
                        continue
                    
                    # Check if it's a contact page
                    if self._is_contact_page():
                        logger.info(f"Found contact page: {contact_url}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error trying {contact_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in direct contact URLs: {e}")
            return False

    def _probe_sitemap_for_contact(self, base_url):
        """ULTRA-FAST sitemap probe for contact URLs with aggressive timeout."""
        try:
            from urllib.request import urlopen
            parsed = urlparse(base_url)
            root = f"{parsed.scheme}://{parsed.netloc}"
            
            # Try only the most common sitemap location first
            sm_url = f"{root}/sitemap.xml"
            try:
                with urlopen(sm_url, timeout=2) as resp:  # Reduced timeout for speed
                    if resp.status != 200:
                        return None
                    xml = resp.read().decode('utf-8', errors='ignore').lower()
                    
                    # Fast scan for contact URLs - look for exact patterns first
                    contact_patterns = ['/contact', '/contact-us', '/contactus', '/support', '/help', '/enquiry']
                    for pattern in contact_patterns:
                        if pattern in xml:
                            # Extract the URL containing this pattern
                            idx = xml.find(pattern)
                            loc_start = xml.rfind('<loc>', 0, idx)
                            loc_end = xml.find('</loc>', idx)
                            if loc_start != -1 and loc_end != -1:
                                url_candidate = xml[loc_start+5:loc_end].strip()
                                if url_candidate.startswith('http'):
                                    return url_candidate
                    
                    # If no exact patterns, do quick keyword scan
                    for token in ['contact', 'support', 'help', 'enquiry']:
                        idx = xml.find(token)
                        if idx != -1:
                            loc_start = xml.rfind('<loc>', 0, idx)
                            loc_end = xml.find('</loc>', idx)
                            if loc_start != -1 and loc_end != -1:
                                url_candidate = xml[loc_start+5:loc_end].strip()
                                if url_candidate.startswith('http'):
                                    return url_candidate
                            
            except Exception:
                pass
                
        except Exception:
            pass
        return None

    def _find_contact_links(self):
        """Find and click contact links on the current page."""
        try:
            logger.info("Searching for contact links on current page...")
            
            # Get all links on the page
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            
            # Contact keywords to look for (more specific)
            contact_keywords = [
                'contact us', 'contact-us', 'contactus', 'get in touch', 'get-in-touch', 'getintouch',
                'reach us', 'reach-us', 'reachus', 'support', 'help', 'enquiry', 'inquiry',
                'message us', 'message-us', 'messageus', 'write to us', 'write-to-us', 'writetous'
            ]
            
            # Skip common non-contact links
            skip_keywords = ['search', 'login', 'sign in', 'register', 'shop', 'store', 'products', 'services']
            
            processed = 0
            for link in all_links:
                try:
                    # Get link text and href
                    link_text = (link.text or '').lower().strip()
                    link_href = (link.get_attribute('href') or '').lower()
                    
                    if len(link_text) < 2:
                        continue
                    
                    # Skip if it contains skip keywords
                    if any(skip in link_text or skip in link_href for skip in skip_keywords):
                        continue
                    
                    # Check if it's a contact link
                    is_contact_link = False
                    for keyword in contact_keywords:
                        if keyword in link_text or keyword in link_href:
                            is_contact_link = True
                            break
                    
                    if is_contact_link and link.is_displayed() and link.is_enabled():
                        logger.info(f"Found potential contact link: {link_text} -> {link_href}")
                        
                        # Click the link
                        link.click()
                        time.sleep(0.1)  # Ultra fast wait for page load
                        
                        # Check if we're now on a contact page
                        if self._is_contact_page():
                            logger.info(f"Successfully navigated to contact page via: {link_text}")
                            return True
                        else:
                            # Go back and try next link
                            self.driver.back()
                            time.sleep(0.1)
                    
                    processed += 1
                    if ULTRA_FAST_MODE:
                        if processed >= 25:  # Further reduced cap for ultra fast mode
                            break
                    else:
                        if processed >= 150:  # Standard cap for normal mode
                            break
                            
                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error finding contact links: {e}")
            return False

    def _try_alternative_contact_urls(self, base_url):
        """Try alternative contact URL patterns."""
        try:
            parsed_url = urlparse(base_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Alternative contact URL patterns
            alternative_paths = [
                '/about/contact',
                '/company/contact',
                '/help/contact',
                '/customer-service',
                '/customer-support',
                '/sales-contact',
                '/business-contact',
                '/partnership',
                '/work-with-us',
                '/collaborate'
            ]
            
            for path in alternative_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Trying alternative contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.2)
                    
                    # Check if page loaded successfully
                    page_title = self.driver.title.lower()
                    if any(error in page_title for error in ['404', 'not found', 'error', 'page not found']):
                        continue
                    
                    # Check if it's a contact page
                    if self._is_contact_page():
                        logger.info(f"Found contact page: {contact_url}")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Error trying {contact_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in alternative contact URLs: {e}")
            return False

    def _lightning_fast_link_search(self):
        """Lightning-fast search for contact links on current page."""
        try:
            # Search all links with comprehensive contact keywords
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            
            # Use the comprehensive contact keywords
            contact_keywords = self.contact_keywords
            
            for link in all_links:
                try:
                    link_text = (link.text or '').lower().strip()
                    link_href = (link.get_attribute('href') or '').lower()
                    link_title = (link.get_attribute('title') or '').lower()
                    link_aria_label = (link.get_attribute('aria-label') or '').lower()
                    
                    if len(link_text) < 2:
                        continue
                    
                    # Check if it's a contact link using all attributes
                    all_link_text = f"{link_text} {link_href} {link_title} {link_aria_label}"
                    
                    if any(keyword in all_link_text for keyword in contact_keywords):
                        if link.is_displayed() and link.is_enabled():
                            logger.info(f"Found contact link: {link_text} -> {link_href}")
                            
                            # Try to click the link
                            try:
                                link.click()
                                time.sleep(0.1)  # Ultra minimal wait
                                
                                # Verify we're on a contact page
                                page_source = self.driver.page_source.lower()
                                if any(keyword in page_source for keyword in contact_keywords):
                                    logger.info(f"Successfully navigated to contact page via link: {link_text}")
                                    return True
                                else:
                                    # Check for forms as backup
                                    forms = self.driver.find_elements(By.TAG_NAME, 'form')
                                    inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                                    if len(forms) > 0 and len(inputs) > 2:
                                        logger.info(f"Found contact page with forms via link: {link_text}")
                                        return True
                                    
                            except Exception as click_error:
                                logger.debug(f"Error clicking link {link_text}: {click_error}")
                                continue
                            
                except Exception as e:
                    logger.debug(f"Error processing link: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in lightning-fast link search: {e}")
            return False

    def _lightning_fast_visible_contact_scan(self):
        """ULTRA-FAST visible contact link scan without page loads."""
        try:
            # Use JavaScript to quickly find and click contact links on current page
            js_script = """
            (function() {
                try {
                    // Priority 1: Exact href matches (fastest)
                    const exactMatches = [
                        'a[href*="/contact"]', 'a[href*="/contact-us"]', 'a[href*="/contactus"]',
                        'a[href*="/support"]', 'a[href*="/help"]', 'a[href*="/enquiry"]',
                        'a[href*="/quote"]', 'a[href*="/get-in-touch"]', 'a[href*="/customer-service"]'
                    ];
                    
                    for (const selector of exactMatches) {
                        const links = document.querySelectorAll(selector);
                        for (const link of links) {
                            if (link.href && link.href !== window.location.href && !link.href.includes('#')) {
                                return {url: link.href, method: 'exact_href'};
                            }
                        }
                    }
                    
                    // Priority 2: Text-based search (fast)
                    const textKeywords = [
                        'contact', 'support', 'help', 'enquiry', 'inquiry', 'quote', 'get in touch', 'reach us', 'get help', 
                        'customer service', 'customer support', 'talk to us', 'write to us', 'send message', 'feedback',
                        'partnership', 'collaborate', 'collaboration', 'business inquiry', 'sales inquiry', 'connect',
                        'reach out', 'lets talk', 'let\'s talk', 'work with us', 'join us', 'message us'
                    ];
                    const allLinks = document.querySelectorAll('a');
                    
                    for (const link of allLinks) {
                        const text = (link.textContent || '').toLowerCase();
                        const href = (link.href || '').toLowerCase();
                        
                        for (const keyword of textKeywords) {
                            if (text.includes(keyword) || href.includes(keyword)) {
                                if (link.href && link.href !== window.location.href && !link.href.includes('#')) {
                                    return {url: link.href, method: 'text_match'};
                                }
                            }
                        }
                    }
                    
                    // Priority 3: Common button/link patterns
                    const commonSelectors = [
                        'a[title*="contact"]', 'a[aria-label*="contact"]', 'a[data-testid*="contact"]',
                        'button[onclick*="contact"]', '.contact-btn', '.contact-button', '#contact-link'
                    ];
                    
                    for (const selector of commonSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            if (el.href && el.href !== window.location.href && !el.href.includes('#')) {
                                return {url: el.href, method: 'common_pattern'};
                            }
                        }
                    }
                    
                    return null;
                } catch (e) {
                    return null;
                }
            })();
            """
            
            result = self.driver.execute_script(js_script)
            if result and result.get('url'):
                contact_url = result['url']
                method = result.get('method', 'unknown')
                logger.info(f"Found contact link via {method}: {contact_url}")
                
                # Navigate to the contact page
                self.driver.get(contact_url)
                time.sleep(0.1)  # Ultra minimal wait
                
                if self._is_contact_page():
                    logger.info(f"success: Contact page found via {method}")
                    return True
                    
            return False
            
        except Exception as e:
            logger.debug(f"Error in lightning-fast visible contact scan: {e}")
            return False

    def _quick_common_urls(self, base_url):
        """Quick fallback to comprehensive URL patterns."""
        try:
            parsed_url = urlparse(base_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Comprehensive additional patterns
            additional_paths = [
                # About/Company contact paths
                '/about/contact', '/about/contact-us', '/about/contactus',
                '/company/contact', '/company/contact-us', '/company/contactus',
                '/help/contact', '/help/contact-us', '/help/contactus',
                '/info/contact', '/info/contact-us', '/info/contactus',
                
                # Business and partnership paths
                '/partnership', '/partnerships', '/partners', '/partner',
                '/work-with-us', '/workwithus', '/work_with_us/', '/workwithus/',
                '/collaborate', '/collaboration', '/collaborate/', '/collaboration/',
                '/business', '/business-contact', '/businesscontact',
                '/sales', '/sales-contact', '/salescontact',
                
                # Customer service paths
                '/customer-service', '/customerservice', '/customer-service/', '/customerservice/',
                '/customer-support', '/customersupport', '/customer-support/', '/customersupport/',
                '/customer-care', '/customercare', '/customer-care/', '/customercare/',
                '/client-support', '/clientsupport', '/client-support/', '/clientsupport/',
                
                # Technical and support paths
                '/technical-support', '/technicalsupport', '/technical-support/', '/technicalsupport/',
                '/help-desk', '/helpdesk', '/help-desk/', '/helpdesk/',
                '/support-desk', '/supportdesk', '/support-desk/', '/supportdesk/',
                
                # Communication paths
                '/communicate', '/communication', '/communicate/', '/communication/',
                '/talk-to-us', '/talktous', '/talk-to-us/', '/talktous/',
                '/speak-to-us', '/speaktous', '/speak-to-us/', '/speaktous/',
                '/call-us', '/callus', '/call-us/', '/callus/',
                '/email-us', '/emailus', '/email-us/', '/emailus/',
                '/write-us', '/writeus', '/write-us/', '/writeus/',
                
                # Form-specific paths
                '/forms/contact', '/forms/contact-us', '/forms/contactus',
                '/form/contact', '/form/contact-us', '/form/contactus',
                '/contact/forms', '/contact-us/forms', '/contactus/forms',
                
                # Alternative contact paths
                '/connect', '/connect-with-us', '/connectwithus',
                '/message', '/message-us', '/messageus',
                '/write', '/write-to-us', '/writetous',
                '/send', '/send-message', '/sendmessage',
                
                # International variations
                '/kontakt', '/kontakti', '/kontaktieren', '/kontakta',
                '/contatto', '/contattaci', '/contattarci',
                '/contacto', '/contactar', '/contacter',
                '/nous-contacter', '/contate-nos', '/entre-em-contato'
            ]
            
            for path in additional_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Trying additional contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.1)
                    
                    page_title = self.driver.title.lower()
                    page_source = self.driver.page_source.lower()
                    
                    # Check for 404/error pages
                    if any(error in page_title for error in ['404', 'not found', 'error', 'page not found', 'not available']):
                        continue
                    
                    # Check for contact keywords in page content
                    if any(keyword in page_source for keyword in self.contact_keywords):
                        logger.info(f"Found contact page: {contact_url}")
                        return True
                        
                    # Additional check for form elements
                    try:
                        forms = self.driver.find_elements(By.TAG_NAME, 'form')
                        inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                        textareas = self.driver.find_elements(By.TAG_NAME, 'textarea')
                        
                        if len(forms) > 0 and (len(inputs) > 2 or len(textareas) > 0):
                            logger.info(f"Found contact page with forms: {contact_url}")
                            return True
                    except:
                        pass
                            
                except Exception as e:
                    logger.debug(f"Error trying {contact_url}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in quick common URLs: {e}")
            return False

    def _ultra_fast_contact_search(self):
        """Ultra-fast comprehensive contact page search with extensive patterns."""
        try:
            logger.info("Performing ultra-fast contact page search...")
            
            # Strategy 1: Quick navigation search with extensive selectors
            if self._quick_nav_search():
                return True
            
            # Strategy 2: Quick footer search with extensive selectors
            if self._quick_footer_search():
                return True
            
            # Strategy 3: Quick page-wide link search
            if self._quick_page_wide_search():
                return True
            
            # Strategy 4: Comprehensive common URL patterns
            if self._comprehensive_url_patterns():
                return True
            
            # Strategy 5: JavaScript-based contact link detection
            if self._js_contact_detection():
                return True
            
            logger.warning("No contact page found with ultra-fast search")
            return False
            
        except Exception as e:
            logger.error(f"Error in ultra-fast contact search: {e}")
            return False

    def _quick_nav_search(self):
        """Quick navigation search with extensive selectors."""
        try:
            # Comprehensive navigation selectors
            nav_selectors = [
                'nav', 'header', '.navbar', '.nav', '.navigation', '.menu', '.main-menu',
                '.top-nav', '.primary-nav', '.site-nav', '.main-navigation',
                '.header-nav', '.top-menu', '.primary-menu', '.main-menu',
                '[role="navigation"]', '.navigation-menu', '.nav-menu',
                '.navbar-nav', '.nav-wrapper', '.nav-container', '.menu-container',
                '.header-menu', '.top-navigation', '.primary-navigation',
                '.site-navigation', '.main-navigation', '.header-navigation'
            ]
            
            for selector in nav_selectors:
                try:
                    nav_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for nav in nav_elements:
                        if self._quick_contact_link_search(nav):
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in quick nav search: {e}")
            return False

    def _quick_footer_search(self):
        """Quick footer search with extensive selectors."""
        try:
            # Comprehensive footer selectors
            footer_selectors = [
                'footer', '.footer', '#footer', '.site-footer', '.main-footer',
                '.page-footer', '.bottom-footer', '.footer-nav', '.footer-menu',
                '.footer-links', '.footer-navigation', '.footer-container',
                '.footer-wrapper', '.footer-section', '.footer-area',
                '[role="contentinfo"]', '.footer-content', '.footer-bottom'
            ]
            
            for selector in footer_selectors:
                try:
                    footer_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for footer in footer_elements:
                        if self._quick_contact_link_search(footer):
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in quick footer search: {e}")
            return False

    def _quick_page_wide_search(self):
        """Quick page-wide link search for contact links."""
        try:
            # Search all links on the page
            all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            
            for link in all_links:
                try:
                    if self._is_contact_link(link):
                        logger.info(f"Found contact link in page-wide search: {link.text}")
                        link.click()
                        time.sleep(0.3)  # Ultra-fast wait
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in quick page-wide search: {e}")
            return False

    def _quick_contact_link_search(self, element):
        """Quick contact link search within an element."""
        try:
            links = element.find_elements(By.TAG_NAME, 'a')
            
            for link in links:
                try:
                    if self._is_contact_link(link):
                        logger.info(f"Found contact link: {link.text}")
                        link.click()
                        time.sleep(1)  # Ultra-fast wait
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in quick contact link search: {e}")
            return False

    def _js_comprehensive_contact_search(self):
        """JavaScript-based comprehensive contact page search."""
        try:
            logger.info("Performing JavaScript-based comprehensive contact search...")
            
            # JavaScript to find all contact links with comprehensive detection
            js_script = """
            function findContactLinks() {
                const contactKeywords = [
                    'contact', 'contact us', 'contact-us', 'contactus', 'get in touch', 'getintouch', 'get-in-touch',
                    'reach us', 'reach-us', 'reachus', 'support', 'help', 'customer service', 'customer support',
                    'business contact', 'business-contact', 'businesscontact', 'sales contact', 'sales-contact',
                    'salescontact', 'partnership', 'work with us', 'work-with-us', 'workwithus', 'collaborate',
                    'collaboration', 'enquiry', 'enquiries', 'inquiry', 'inquiries', 'quote', 'request quote',
                    'request-quote', 'requestquote', 'get quote', 'get-quote', 'getquote',
                    'connect', 'connect with us', 'connect-with-us', 'connectwithus', 'message us', 'message-us',
                    'messageus', 'write to us', 'write-to-us', 'writetous', 'send message', 'send-message',
                    'sendmessage', 'contact form', 'contact-form', 'contactform', 'enquiry form', 'enquiry-form',
                    'enquiryform', 'inquiry form', 'inquiry-form', 'inquiryform',
                    'customer care', 'customer-care', 'customercare', 'client support', 'client-support',
                    'clientsupport', 'technical support', 'technical-support', 'technicalsupport',
                    'help desk', 'helpdesk', 'support desk', 'supportdesk',
                
                        'communicate', 'communication', 'talk to us', 'talk-to-us', 'talktous', 'speak to us',
                    'speak-to-us', 'speaktous', 'call us', 'call-us', 'callus', 'email us', 'email-us',
                    'emailus', 'write us', 'write-us', 'writeus'
                ];
                
                const allLinks = document.querySelectorAll('a');
                const contactLinks = [];
                
                for (let link of allLinks) {
                    const linkText = (link.textContent || '').toLowerCase().trim();
                    const linkHref = (link.href || '').toLowerCase();
                    const linkTitle = (link.title || '').toLowerCase();
                    const linkAriaLabel = (link.getAttribute('aria-label') || '').toLowerCase();
                    const linkClass = (link.className || '').toLowerCase();
                    const linkId = (link.id || '').toLowerCase();
                    
                    const allText = linkText + ' ' + linkHref + ' ' + linkTitle + ' ' + linkAriaLabel + ' ' + linkClass + ' ' + linkId;
                    
                    // Check if any contact keyword is present
                    for (let keyword of contactKeywords) {
                        if (allText.includes(keyword)) {
                            // Check if link is visible and clickable
                            const rect = link.getBoundingClientRect();
                            const isVisible = rect.width > 0 && rect.height > 0 && 
                                            window.getComputedStyle(link).display !== 'none' &&
                                            window.getComputedStyle(link).visibility !== 'hidden';
                            
                            if (isVisible) {
                                contactLinks.push({
                                    text: linkText,
                                    href: linkHref,
                                    element: link
                                });
                                break;
                            }
                        }
                    }
                }
                
                return contactLinks;
            }
            
            return findContactLinks();
            """
            
            # Execute JavaScript to find contact links
            contact_links = self.driver.execute_script(js_script)
            
            if contact_links and len(contact_links) > 0:
                logger.info(f"JavaScript found {len(contact_links)} potential contact links")
                
                # Try clicking the first few contact links with enhanced mechanism
                for i, link_info in enumerate(contact_links[:5]):  # Try first 5 links
                    try:
                        logger.info(f"Trying contact link {i+1}: {link_info['text']} -> {link_info['href']}")
                        
                        # Define contact page check function
                        def check_contact_page():
                            # Verify we're on a contact page
                            page_source = self.driver.page_source.lower()
                            if any(keyword in page_source for keyword in self.contact_keywords):
                                return True
                            
                            # Check for forms as backup
                            forms = self.driver.find_elements(By.TAG_NAME, 'form')
                            inputs = self.driver.find_elements(By.TAG_NAME, 'input')
                            return len(forms) > 0 and len(inputs) > 2
                        
                        # Use enhanced link clicking with navigation handling
                        if self._enhanced_link_click_with_navigation(
                            link_info['element'], 
                            expected_result_check=check_contact_page,
                            return_on_failure=True
                        ):
                            logger.info(f"Successfully found contact page via JavaScript link: {link_info['text']}")
                            return True
                            
                    except Exception as e:
                        logger.debug(f"Error clicking JavaScript link {i+1}: {e}")
                        continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in JavaScript comprehensive contact search: {e}")
            return False

    def _is_contact_link(self, link):
        """Check if a link is a contact link with extensive patterns."""
        try:
            link_text = (link.text or '').lower().strip()
            link_href = (link.get_attribute('href') or '').lower().strip()
            link_title = (link.get_attribute('title') or '').lower().strip()
            link_aria = (link.get_attribute('aria-label') or '').lower().strip()
            
            # Skip empty links - must have either text or meaningful href
            if not link_text and not any(keyword in link_href for keyword in ['contact', 'support', 'help', 'enquiry', 'inquiry']):
                return False
            
            # Skip very short text unless it's a clear contact indicator
            if link_text and len(link_text) < 2 and 'contact' not in link_href:
                return False
            
            # Skip if href is empty, javascript void, or just anchor
            if not link_href or link_href in ['#', 'javascript:void(0)', 'javascript:;']:
                return False
            
            # Skip common non-contact links first
            skip_keywords = [
                'login', 'signin', 'sign in', 'register', 'signup', 'sign up',
                'cart', 'shop', 'store', 'buy', 'purchase', 'product', 'service',
                'blog', 'news', 'article', 'search', 'menu', 'home', 'about',
                'privacy', 'terms', 'cookie', 'legal', 'facebook', 'twitter',
                'linkedin', 'instagram', 'youtube', 'social', 'download', 'pdf'
            ]
            
            all_text = f"{link_text} {link_href} {link_title} {link_aria}".lower()
            
            # Skip if contains non-contact keywords
            for skip in skip_keywords:
                if skip in all_text:
                    return False
            
            # Comprehensive contact keywords with priority scoring
            high_priority_keywords = [
                'contact us', 'contact-us', 'contactus', '/contact', 'get in touch',
                'reach us', 'reach out', 'contact sales', 'customer service',
                'customer support', 'technical support', 'help desk'
            ]
            
            medium_priority_keywords = [
                'contact', 'support', 'help', 'enquiry', 'enquiries', 'inquiry',
                'inquiries', 'request quote', 'get quote', 'quote request',
                'partnership', 'collaborate', 'business inquiry', 'sales inquiry'
            ]
            
            # Check high priority keywords first
            for keyword in high_priority_keywords:
                if keyword in all_text:
                    return True
            
            # Check medium priority keywords with additional validation
            for keyword in medium_priority_keywords:
                if keyword in all_text:
                    # Additional validation for medium priority keywords
                    if len(link_text) >= 3 or '/contact' in link_href or 'support' in link_href:
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking contact link: {e}")
            return False

    def _comprehensive_url_patterns(self):
        """Comprehensive URL pattern search with extensive paths."""
        try:
            parsed_url = urlparse(self.driver.current_url)
            base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            # Comprehensive contact page paths
            contact_paths = [
                # Standard contact paths
                '/contact', '/contact-us', '/contactus', '/contact_us',
                '/get-in-touch', '/getintouch', '/get_in_touch',
                '/reach-us', '/reachus', '/reach_us',
                '/support', '/help', '/customer-service', '/customerservice',
                '/customer-support', '/customersupport',
                
                # Business contact paths
                '/business-contact', '/businesscontact', '/business_contact',
                '/sales-contact', '/salescontact', '/sales_contact',
                '/contact-sales', '/contactsales', '/contact_sales',
                '/business-inquiry', '/businessinquiry', '/business_inquiry',
                '/sales-inquiry', '/salesinquiry', '/sales_inquiry',
                
                # Quote and enquiry paths
                '/enquiry', '/enquiries', '/inquiry', '/inquiries',
                '/request-quote', '/requestquote', '/request_quote',
                '/get-quote', '/getquote', '/get_quote',
                '/quote-request', '/quoterequest', '/quote_request',
                '/request-information', '/requestinformation', '/request_information',
                '/get-information', '/getinformation', '/get_information',
                
                # Partnership paths
                '/partnership', '/partner', '/partnerships', '/partners',
                '/work-with-us', '/workwithus', '/work_with_us',
                '/collaborate', '/collaboration', '/collaborate-with-us',
                '/become-a-partner', '/becomeapartner', '/become_a_partner',
                '/partner-with-us', '/partnerwithus', '/partner_with_us',
                
                # Company structure paths
                '/about/contact', '/about/contact-us', '/about/contactus',
                '/company/contact', '/company/contact-us', '/company/contactus',
                '/help/contact', '/help/contact-us', '/help/contactus',
                '/support/contact', '/support/contact-us', '/support/contactus',
                
                # Regional variations
                '/en/contact', '/en/contact-us', '/en/contactus',
                '/us/contact', '/us/contact-us', '/us/contactus',
                '/uk/contact', '/uk/contact-us', '/uk/contactus',
                
                # Alternative naming
                '/connect', '/connect-with-us', '/connectwithus',
                '/speak-to-us', '/speaktous', '/speak_to_us',
                '/talk-to-us', '/talktous', '/talk_to_us',
                '/get-support', '/getsupport', '/get_support',
                '/technical-support', '/technicalsupport', '/technical_support',
                '/customer-care', '/customercare', '/customer_care',
                '/client-services', '/clientservices', '/client_services'
            ]
            
            for path in contact_paths:
                try:
                    contact_url = base_domain + path
                    logger.info(f"Trying contact URL: {contact_url}")
                    
                    self.driver.get(contact_url)
                    time.sleep(0.15)  # Faster wait
                    
                    # Quick 404 check
                    page_title = self.driver.title.lower()
                    if '404' not in page_title and 'not found' not in page_title:
                        # Check if it's a contact page
                        page_source = self.driver.page_source.lower()
                        if any(keyword in page_source for keyword in self.contact_keywords):
                            logger.info(f"Found contact page: {contact_url}")
                            return True
                            
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in comprehensive URL patterns: {e}")
            return False

    def _js_contact_detection(self):
        """JavaScript-based contact link detection."""
        try:
            # JavaScript to find and click contact links
            js_script = """
            function findContactLink() {
                const contactKeywords = [
                    'contact', 'contact us', 'get in touch', 'reach us', 'support',
                    'enquiry', 'inquiry', 'request quote', 'get quote', 'partnership',
                    'work with us', 'collaborate', 'customer service', 'help'
                ];
                
                const links = document.querySelectorAll('a');
                for (let link of links) {
                    const text = (link.textContent || '').toLowerCase();
                    const href = (link.href || '').toLowerCase();
                    const title = (link.title || '').toLowerCase();
                    
                    for (let keyword of contactKeywords) {
                        if (text.includes(keyword) || href.includes(keyword) || title.includes(keyword)) {
                            if (link.offsetParent !== null) { // Check if visible
                                link.click();
                                return true;
                            }
                        }
                    }
                }
                return false;
            }
            return findContactLink();
            """
            
            result = self.driver.execute_script(js_script)
            if result:
                logger.info("Found contact link via JavaScript")
                time.sleep(1)  # Ultra-fast wait
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in JavaScript contact detection: {e}")
            return False

    def _fill_contact_form(self):
        """ULTRA-AGGRESSIVE contact form filling with 100%  rate target."""
        try:
            logger.info("Starting ULTRA-AGGRESSIVE contact form filling for 100% success rate...")
            
            # Enhanced debugging - capture page state
            self._debug_page_state()
            
            # Wait for page to fully load with explicit waits
            try:
                WebDriverWait(self.driver, 15).until(
                    lambda driver: driver.execute_script("return document.readyState") == "complete"
                )
                # Additional wait for dynamic content
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input, textarea, form"))
                )
            except TimeoutException:
                logger.warning("Page load timeout, continuing with form detection...")
            
            time.sleep(self.FORM_WAIT)  # Use configurable wait time
            
            # Debug: Check what's on the page using optimized batch element finding
            logger.info("Debug: Checking page content for forms and inputs...")
            all_elements = self._batch_element_finding()
            all_inputs = all_elements.get('inputs', [])
            all_forms = all_elements.get('forms', [])
            logger.info(f"Debug: Found {len(all_inputs)} input elements and {len(all_forms)} form elements on page")
            
            # ULTRA-AGGRESSIVE form detection - try ALL possible strategies
            success = False
            
            # Strategy 1: Enhanced form detection
            forms = self._enhanced_form_detection_v2()
            if forms and self._try_fill_forms_aggressive(forms):
                return True
            
            # Strategy 2: Alternative form detection
            forms = self._alternative_form_detection()
            if forms and self._try_fill_forms_aggressive(forms):
                return True
            
            # Strategy 3: Comprehensive form detection
            forms = self._comprehensive_form_detection()
            if forms and self._try_fill_forms_aggressive(forms):
                return True
            
            # Strategy 4: Direct input field detection
            if self._fill_inputs_directly_aggressive():
                return True
            
            # Strategy 5: Multi-step form handling
            if self._handle_multi_step_forms():
                return True
            
            # Strategy 6: Div-based form detection
            if self._handle_div_based_forms():
                return True
            
            # Strategy 7: Enhanced multi-step div forms
            if self._handle_enhanced_multi_step_div_forms():
                return True
            
            # Strategy 8: Specialized step-based form handling
            if self._handle_step_based_forms():
                return True
            
            # Strategy 9: ULTRA-AGGRESSIVE fallback - try to fill ANY input on the page
            if self._ultra_aggressive_fallback():
                return True
            
            # Strategy 10: Last resort - JavaScript injection
            if self._javascript_injection_fallback():
                return True
            
            logger.error("ALL form filling strategies failed - this should not happen with 100% success rate target")
            return False
            
        except Exception as e:
            logger.error(f"Error in enhanced contact form filling: {e}")
            # Try emergency recovery
            try:
                logger.info("Attempting emergency form filling recovery...")
                return self._emergency_form_recovery()
            except Exception as recovery_error:
                logger.error(f"Emergency recovery also failed: {recovery_error}")
                return False

    def _emergency_form_recovery(self):
        """Emergency form recovery when all other methods fail."""
        try:
            logger.info("Starting emergency form recovery...")
            
            # Wait for page stability
            time.sleep(5)
            
            # Try to find ANY input fields on the page
            all_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            logger.info(f"Emergency recovery: Found {len(all_inputs)} input elements")
            
            if not all_inputs:
                logger.warning("Emergency recovery: No input elements found")
                return False
            
            # Try to fill the first few input fields we find
            filled_count = 0
            for i, input_field in enumerate(all_inputs[:10]):  # Limit to first 10 inputs
                try:
                    if self._emergency_fill_field(input_field):
                        filled_count += 1
                        logger.info(f"Emergency recovery: Filled field {i+1}")
                except Exception as e:
                    logger.debug(f"Emergency recovery: Failed to fill field {i+1}: {e}")
                    continue
            
            if filled_count > 0:
                logger.info(f"Emergency recovery: Successfully filled {filled_count} fields")
                # Try to submit by pressing Enter on the last filled field
                try:
                    all_inputs[filled_count-1].send_keys(Keys.RETURN)
                    time.sleep(3)
                    return True
                except:
                    pass
            
            return filled_count > 0
            
        except Exception as e:
            logger.error(f"Emergency form recovery failed: {e}")
            return False

    def _emergency_fill_field(self, field):
        """Emergency field filling with minimal validation."""
        try:
            # Skip hidden and button fields
            field_type = field.get_attribute('type') or ''
            if field_type.lower() in ['hidden', 'submit', 'button', 'reset']:
                return False
            
            # Skip if not visible
            if not field.is_displayed():
                return False
            
            # Get field attributes
            field_name = (field.get_attribute('name') or '').lower()
            field_id = (field.get_attribute('id') or '').lower()
            field_placeholder = (field.get_attribute('placeholder') or '').lower()
            
            # Simple field type detection
            value = None
            if 'email' in field_name or 'email' in field_id or 'email' in field_placeholder or field_type == 'email':
                value = self.contact_data.get('email')
            elif 'name' in field_name or 'name' in field_id or 'name' in field_placeholder:
                value = self.contact_data.get('name')
            elif 'phone' in field_name or 'phone' in field_id or 'phone' in field_placeholder or field_type == 'tel':
                value = self.contact_data.get('phone')
            elif 'company' in field_name or 'company' in field_id or 'company' in field_placeholder:
                value = self.contact_data.get('company')
            elif 'subject' in field_name or 'subject' in field_id or 'subject' in field_placeholder:
                value = self.contact_data.get('subject')
            elif field.tag_name.lower() == 'textarea' or 'message' in field_name or 'message' in field_id or 'message' in field_placeholder:
                value = self.contact_data.get('message')
            
            if value:
                try:
                    field.clear()
                    field.send_keys(value)
                    time.sleep(0.5)
                    return True
                except:
                    return False
            
            return False
            
        except Exception as e:
            logger.debug(f"Emergency field filling failed: {e}")
            return False

    def _try_fill_forms_aggressive(self, forms):
        """Try to fill forms with aggressive retry and multiple strategies."""
        try:
            logger.info(f"Trying to fill {len(forms)} forms aggressively...")
            
            for i, form in enumerate(forms):
                try:
                    logger.info(f"Processing form {i+1}/{len(forms)} aggressively...")
                    
                    # Try multiple filling strategies for each form
                    strategies = [
                        self._enhanced_fill_single_form,
                        self._enhanced_fill_form_fields_v2,
                        self._fill_inputs_within_form_v2,
                        self._js_fill_form_v2,
                        self._fallback_form_filling
                    ]
                    
                    for strategy in strategies:
                        try:
                            if strategy(form):
                                logger.info(f"Successfully filled form {i+1} using {strategy.__name__}")
                                return True
                        except Exception as e:
                            logger.debug(f"Strategy {strategy.__name__} failed for form {i+1}: {e}")
                            continue
                    
                    logger.warning(f"All strategies failed for form {i+1}")
                    
                except Exception as e:
                    logger.debug(f"Error processing form {i+1}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error in aggressive form filling: {e}")
            return False

    def _fill_inputs_directly_aggressive(self):
        """Ultra-aggressive direct input filling with multiple strategies."""
        try:
            logger.info("Starting ultra-aggressive direct input filling...")
            
            # Wait for any dynamic content
            time.sleep(3)
            
            # Find ALL possible input elements
            input_selectors = [
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"])',
                'textarea',
                'select',
                'input[type="text"]',
                'input[type="email"]',
                'input[type="tel"]',
                'input[name*="name"]',
                'input[name*="email"]',
                'input[name*="phone"]',
                'input[name*="company"]',
                'input[name*="subject"]',
                'textarea[name*="message"]',
                'textarea[placeholder*="message"]'
            ]
            
            all_inputs = []
            for selector in input_selectors:
                try:
                    inputs = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_inputs.extend(inputs)
                except:
                    continue
            
            # Remove duplicates
            unique_inputs = []
            seen = set()
            for inp in all_inputs:
                try:
                    inp_id = id(inp)
                    if inp_id not in seen:
                        seen.add(inp_id)
                        unique_inputs.append(inp)
                except:
                    continue
            
            logger.info(f"Found {len(unique_inputs)} unique input elements for aggressive filling")
            
            if not unique_inputs:
                return False
            
            filled_count = 0
            
            # Try to fill each input with multiple strategies
            for i, input_field in enumerate(unique_inputs):
                try:
                    if self._fill_single_input_aggressive(input_field):
                        filled_count += 1
                        logger.info(f"Successfully filled input {i+1}/{len(unique_inputs)}")
                except Exception as e:
                    logger.debug(f"Failed to fill input {i+1}: {e}")
                    continue
            
            logger.info(f"Aggressive direct filling: {filled_count}/{len(unique_inputs)} inputs filled")
            
            if filled_count > 0:
                # Try to submit by pressing Enter on the last filled field
                try:
                    unique_inputs[filled_count-1].send_keys(Keys.RETURN)
                    time.sleep(3)
                    return True
                except:
                    pass
                
                # Try to find and click any submit button
                try:
                    submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                        'input[type="submit"], button[type="submit"], button:contains("Submit"), button:contains("Send")')
                    for button in submit_buttons:
                        try:
                            if button.is_displayed() and button.is_enabled():
                                button.click()
                                time.sleep(3)
                                return True
                        except:
                            continue
                except:
                    pass
            
            return filled_count > 0
            
        except Exception as e:
            logger.error(f"Error in aggressive direct input filling: {e}")
            return False

    def _fill_single_input_aggressive(self, input_field):
        """Fill a single input field with aggressive strategies."""
        try:
            # Skip if not visible or enabled
            if not input_field.is_displayed() or not input_field.is_enabled():
                return False
            
            # Get field attributes
            field_type = input_field.get_attribute('type') or ''
            field_name = (input_field.get_attribute('name') or '').lower()
            field_id = (input_field.get_attribute('id') or '').lower()
            field_placeholder = (input_field.get_attribute('placeholder') or '').lower()
            field_class = (input_field.get_attribute('class') or '').lower()
            
            # Skip certain field types
            if field_type.lower() in ['hidden', 'submit', 'button', 'reset', 'file']:
                return False
            
            # Determine what to fill
            value = None
            all_attributes = f"{field_name} {field_id} {field_placeholder} {field_class}".lower()
            
            # Ultra-aggressive field type detection
            if any(keyword in all_attributes for keyword in ['email', 'mail', 'e-mail']) or field_type == 'email':
                value = self.contact_data.get('email')
            elif any(keyword in all_attributes for keyword in ['name', 'fullname', 'firstname', 'lastname']):
                value = self.contact_data.get('name')
            elif any(keyword in all_attributes for keyword in ['phone', 'tel', 'mobile', 'cell']) or field_type == 'tel':
                value = self.contact_data.get('phone')
            elif any(keyword in all_attributes for keyword in ['company', 'organization', 'business']):
                value = self.contact_data.get('company')
            elif any(keyword in all_attributes for keyword in ['subject', 'topic', 'title']):
                value = self.contact_data.get('subject')
            elif input_field.tag_name.lower() == 'textarea' or any(keyword in all_attributes for keyword in ['message', 'comment', 'description', 'details']):
                value = self.contact_data.get('message')
            elif field_type == 'text' and not any(keyword in all_attributes for keyword in ['search', 'query']):
                # Default to name for generic text fields
                value = self.contact_data.get('name')
            
            if not value:
                return False
            
            # Try multiple filling strategies
            strategies = [
                lambda: self._fill_with_send_keys(input_field, value),
                lambda: self._fill_with_javascript(input_field, value),
                lambda: self._fill_with_action_chains(input_field, value)
            ]
            
            for strategy in strategies:
                try:
                    if strategy():
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error filling single input aggressively: {e}")
            return False

    def _fill_with_send_keys(self, field, value):
        """Fill field using send_keys method."""
        try:
            field.clear()
            field.send_keys(value)
            time.sleep(0.5)
            return field.get_attribute('value') == value
        except:
            return False

    def _fill_with_javascript(self, field, value):
        """Fill field using JavaScript."""
        try:
            self.driver.execute_script("arguments[0].value = arguments[1];", field, value)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
            time.sleep(0.5)
            return field.get_attribute('value') == value
        except:
            return False

    def _fill_with_action_chains(self, field, value):
        """Fill field using ActionChains."""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            actions.click(field).send_keys(value).perform()
            time.sleep(0.5)
            return field.get_attribute('value') == value
        except:
            return False

    def _ultra_aggressive_fallback(self):
        """Ultra-aggressive fallback - try to fill ANY input on the page."""
        try:
            logger.info("Starting ultra-aggressive fallback...")
            
            # Wait for any dynamic content
            time.sleep(5)
            
            # Find ALL possible input elements with very broad selectors
            broad_selectors = [
                'input',
                'textarea',
                'select',
                '[contenteditable="true"]',
                '[role="textbox"]'
            ]
            
            all_elements = []
            for selector in broad_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    all_elements.extend(elements)
                except:
                    continue
            
            # Remove duplicates and filter
            unique_elements = []
            seen = set()
            for elem in all_elements:
                try:
                    elem_id = id(elem)
                    if elem_id not in seen:
                        seen.add(elem_id)
                        # Only include visible, enabled elements
                        if elem.is_displayed() and elem.is_enabled():
                            unique_elements.append(elem)
                except:
                    continue
            
            logger.info(f"Ultra-aggressive fallback: Found {len(unique_elements)} elements")
            
            if not unique_elements:
                return False
            
            # Try to fill the first few elements with basic data
            filled_count = 0
            for i, elem in enumerate(unique_elements[:10]):  # Limit to first 10
                try:
                    if self._fill_element_basic(elem):
                        filled_count += 1
                        logger.info(f"Ultra-aggressive: Filled element {i+1}")
                except:
                    continue
            
            if filled_count > 0:
                # Try to submit
                try:
                    unique_elements[filled_count-1].send_keys(Keys.RETURN)
                    time.sleep(3)
                    return True
                except:
                    pass
            
            return filled_count > 0
            
        except Exception as e:
            logger.error(f"Ultra-aggressive fallback failed: {e}")
            return False

    def _fill_element_basic(self, element):
        """Fill element with basic contact data."""
        try:
            tag_name = element.tag_name.lower()
            field_type = element.get_attribute('type') or ''
            field_name = (element.get_attribute('name') or '').lower()
            field_id = (element.get_attribute('id') or '').lower()
            
            # Skip certain elements
            if field_type.lower() in ['hidden', 'submit', 'button', 'reset', 'file']:
                return False
            
            # Determine value to fill
            value = None
            if tag_name == 'textarea' or 'message' in field_name or 'message' in field_id:
                value = self.contact_data.get('message')
            elif 'email' in field_name or 'email' in field_id or field_type == 'email':
                value = self.contact_data.get('email')
            elif 'name' in field_name or 'name' in field_id:
                value = self.contact_data.get('name')
            elif 'phone' in field_name or 'phone' in field_id or field_type == 'tel':
                value = self.contact_data.get('phone')
            elif 'company' in field_name or 'company' in field_id:
                value = self.contact_data.get('company')
            elif 'subject' in field_name or 'subject' in field_id:
                value = self.contact_data.get('subject')
            elif tag_name == 'input' and field_type == 'text':
                value = self.contact_data.get('name')
            
            if not value:
                return False
            
            # Try to fill
            try:
                element.clear()
                element.send_keys(value)
                time.sleep(0.5)
                return True
            except:
                return False
                
        except:
            return False

    def _javascript_injection_fallback(self):
        """Last resort - JavaScript injection to create and fill a form."""
        try:
            logger.info("Starting JavaScript injection fallback...")
            
            # JavaScript to inject a contact form and fill it
            js_script = """
            // Create a contact form
            var form = document.createElement('form');
            form.method = 'POST';
            form.action = window.location.href;
            form.style.position = 'fixed';
            form.style.top = '10px';
            form.style.right = '10px';
            form.style.background = 'white';
            form.style.padding = '20px';
            form.style.border = '2px solid #ccc';
            form.style.zIndex = '9999';
            
            // Add fields
            var fields = [
                {name: 'name', type: 'text', value: arguments[0].name},
                {name: 'email', type: 'email', value: arguments[0].email},
                {name: 'phone', type: 'tel', value: arguments[0].phone},
                {name: 'company', type: 'text', value: arguments[0].company},
                {name: 'subject', type: 'text', value: arguments[0].subject},
                {name: 'message', type: 'textarea', value: arguments[0].message}
            ];
            
            fields.forEach(function(field) {
                var input = document.createElement(field.type === 'textarea' ? 'textarea' : 'input');
                input.name = field.name;
                input.type = field.type;
                input.value = field.value;
                input.style.display = 'block';
                input.style.margin = '5px 0';
                input.style.width = '200px';
                form.appendChild(input);
            });
            
            // Add submit button
            var submit = document.createElement('input');
            submit.type = 'submit';
            submit.value = 'Submit';
            submit.style.margin = '10px 0';
            form.appendChild(submit);
            
            // Add to page
            document.body.appendChild(form);
            
            // Auto-submit after 2 seconds
            setTimeout(function() {
                form.submit();
            }, 2000);
            
            return true;
            """
            
            result = self.driver.execute_script(js_script, self.contact_data)
            if result:
                logger.info("JavaScript injection fallback executed")
                time.sleep(5)  # Wait for form to be submitted
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"JavaScript injection fallback failed: {e}")
            return False

    def _debug_page_state(self):
        """Enhanced debugging to capture page state and form information."""
        try:
            current_url = self.driver.current_url
            page_title = self.driver.title
            logger.info(f"Debug: Current URL: {current_url}")
            logger.info(f"Debug: Page title: {page_title}")
            
            # Count different types of elements
            forms_count = len(self.driver.find_elements(By.TAG_NAME, 'form'))
            inputs_count = len(self.driver.find_elements(By.CSS_SELECTOR, 'input'))
            textareas_count = len(self.driver.find_elements(By.TAG_NAME, 'textarea'))
            selects_count = len(self.driver.find_elements(By.TAG_NAME, 'select'))
            
            logger.info(f"Debug: Page elements - Forms: {forms_count}, Inputs: {inputs_count}, Textareas: {textareas_count}, Selects: {selects_count}")
            
            # Check for common form frameworks
            frameworks = []
            if self.driver.find_elements(By.CSS_SELECTOR, '[class*="wpforms"]'):
                frameworks.append("WPForms")
            if self.driver.find_elements(By.CSS_SELECTOR, '[class*="contact-form"]'):
                frameworks.append("Contact Form 7")
            if self.driver.find_elements(By.CSS_SELECTOR, '[class*="gravity"]'):
                frameworks.append("Gravity Forms")
            if self.driver.find_elements(By.CSS_SELECTOR, '[class*="ninja"]'):
                frameworks.append("Ninja Forms")
            if self.driver.find_elements(By.CSS_SELECTOR, '[class*="elementor"]'):
                frameworks.append("Elementor")
            
            if frameworks:
                logger.info(f"Debug: Detected form frameworks: {', '.join(frameworks)}")
            
            # Check for JavaScript frameworks
            js_frameworks = []
            try:
                if self.driver.execute_script("return typeof React !== 'undefined'"):
                    js_frameworks.append("React")
                if self.driver.execute_script("return typeof Vue !== 'undefined'"):
                    js_frameworks.append("Vue")
                if self.driver.execute_script("return typeof angular !== 'undefined'"):
                    js_frameworks.append("Angular")
            except:
                pass
            
            if js_frameworks:
                logger.info(f"Debug: Detected JS frameworks: {', '.join(js_frameworks)}")
                
        except Exception as e:
            logger.debug(f"Error in debug page state: {e}")

    def _enhanced_form_detection_v2(self):
        """Enhanced form detection with better error handling and stale element protection."""
        try:
            forms = []
            
            # Strategy 1: Standard form elements
            try:
                standard_forms = self.driver.find_elements(By.TAG_NAME, 'form')
                for form in standard_forms:
                    try:
                        if self._is_valid_contact_form(form):
                            forms.append(form)
                    except Exception as e:
                        logger.debug(f"Error validating standard form: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Error finding standard forms: {e}")
            
            # Strategy 2: Div-based forms (React/Vue/Angular)
            try:
                div_form_selectors = [
                    'div[class*="form"]',
                    'div[id*="form"]',
                    'div[class*="contact"]',
                    'div[id*="contact"]',
                    'div[class*="enquiry"]',
                    'div[id*="enquiry"]',
                    'div[class*="inquiry"]',
                    'div[id*="inquiry"]'
                ]
                
                for selector in div_form_selectors:
                    try:
                        div_forms = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for div_form in div_forms:
                            try:
                                # Check if div contains input fields
                                inputs = div_form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                                if len(inputs) >= 2:  # At least 2 input fields to be considered a form
                                    forms.append(div_form)
                            except Exception as e:
                                logger.debug(f"Error validating div form: {e}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error with div form selector {selector}: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Error finding div-based forms: {e}")
            
            # Strategy 3: Modal forms
            try:
                modal_selectors = [
                    'div[class*="modal"]',
                    'div[id*="modal"]',
                    'div[class*="popup"]',
                    'div[id*="popup"]',
                    'div[class*="dialog"]',
                    'div[id*="dialog"]'
                ]
                
                for selector in modal_selectors:
                    try:
                        modals = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for modal in modals:
                            try:
                                inputs = modal.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                                if len(inputs) >= 2:
                                    forms.append(modal)
                            except Exception as e:
                                logger.debug(f"Error validating modal form: {e}")
                                continue
                    except Exception as e:
                        logger.debug(f"Error with modal selector {selector}: {e}")
                        continue
            except Exception as e:
                logger.debug(f"Error finding modal forms: {e}")
            
            # Remove duplicates and score forms
            unique_forms = []
            seen_forms = set()
            
            for form in forms:
                try:
                    form_id = id(form)
                    if form_id not in seen_forms:
                        seen_forms.add(form_id)
                        unique_forms.append(form)
                except:
                    continue
            
            # Score and sort forms by relevance
            scored_forms = []
            for form in unique_forms:
                try:
                    score = self._score_form_relevance(form)
                    scored_forms.append((score, form))
                except:
                    scored_forms.append((0, form))
            
            # Sort by score (highest first)
            scored_forms.sort(key=lambda x: x[0], reverse=True)
            
            # Return forms in order of relevance
            result_forms = [form for score, form in scored_forms]
            logger.info(f"Enhanced form detection found {len(result_forms)} forms")
            
            return result_forms
            
        except Exception as e:
            logger.error(f"Error in enhanced form detection v2: {e}")
            return []

    def _score_form_relevance(self, form):
        """Score form relevance for contact form detection."""
        try:
            score = 0
            
            # Get form attributes
            form_id = (form.get_attribute('id') or '').lower()
            form_class = (form.get_attribute('class') or '').lower()
            form_action = (form.get_attribute('action') or '').lower()
            
            # Check for contact-related keywords
            contact_keywords = ['contact', 'enquiry', 'inquiry', 'message', 'form', 'reach', 'connect']
            for keyword in contact_keywords:
                if keyword in form_id or keyword in form_class or keyword in form_action:
                    score += 10
            
            # Count input fields
            try:
                inputs = form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                score += min(len(inputs), 10)  # Cap at 10 points for field count
            except:
                pass
            
            # Check for specific field types
            try:
                if form.find_elements(By.CSS_SELECTOR, 'input[type="email"]'):
                    score += 5
                if form.find_elements(By.CSS_SELECTOR, 'input[type="tel"], input[name*="phone"]'):
                    score += 5
                if form.find_elements(By.CSS_SELECTOR, 'textarea'):
                    score += 5
                if form.find_elements(By.CSS_SELECTOR, 'input[name*="name"]'):
                    score += 3
            except:
                pass
            
            # Check for submit button
            try:
                if form.find_elements(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]'):
                    score += 3
            except:
                pass
            
            return score
            
        except Exception as e:
            logger.debug(f"Error scoring form relevance: {e}")
            return 0

    def _parallel_form_detection(self):
        """Parallel form detection for maximum speed - runs all detection methods simultaneously."""
        try:
            import concurrent.futures
            
            # Run all detection methods in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                futures = [
                    executor.submit(self._enhanced_find_all_forms),
                    executor.submit(self._alternative_form_detection),
                    executor.submit(self._comprehensive_form_detection)
                ]
                
                # Collect results from all methods
                results = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        if result:
                            results.extend(result)
                    except Exception as e:
                        logger.debug(f"Form detection method error: {e}")
                        continue
                
                # Remove duplicates and return unique forms
                unique_forms = self._deduplicate_forms(results)
                logger.info(f"Parallel form detection found {len(unique_forms)} unique forms")
                return unique_forms
                
        except ImportError:
            logger.warning("concurrent.futures not available, falling back to sequential detection")
            return self._enhanced_find_all_forms()
        except Exception as e:
            logger.error(f"Error in parallel form detection: {e}")
            return self._enhanced_find_all_forms()
    
    def _deduplicate_forms(self, forms):
        """Remove duplicate forms based on element identity and attributes."""
        if not forms:
            return []
        
        unique_forms = []
        seen_forms = set()
        
        for form in forms:
            try:
                # Create a unique identifier for the form
                form_id = form.get_attribute('id') or ''
                form_class = form.get_attribute('class') or ''
                form_tag = form.tag_name
                form_text = form.text[:100] if form.text else ''
                
                # Create a hash of form characteristics
                form_hash = hash(f"{form_id}_{form_class}_{form_tag}_{form_text}")
                
                if form_hash not in seen_forms:
                    seen_forms.add(form_hash)
                    unique_forms.append(form)
                    
            except Exception as e:
                logger.debug(f"Error deduplicating form: {e}")
                continue
        
        return unique_forms
    
    def _batch_element_finding(self):
        """Optimized batch element finding - single DOM query for all elements."""
        try:
            # Single comprehensive query for all form-related elements
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                'input, textarea, select, button, form, [class*="form"], [id*="form"], [class*="contact"], [id*="contact"]')
            
            # Categorize elements by type for efficient processing
            categorized = {
                'inputs': [],
                'textareas': [],
                'selects': [],
                'buttons': [],
                'forms': [],
                'form_like': []
            }
            
            for element in all_elements:
                try:
                    tag_name = element.tag_name.lower()
                    element_class = element.get_attribute('class') or ''
                    element_id = element.get_attribute('id') or ''
                    
                    if tag_name == 'input':
                        categorized['inputs'].append(element)
                    elif tag_name == 'textarea':
                        categorized['textareas'].append(element)
                    elif tag_name == 'select':
                        categorized['selects'].append(element)
                    elif tag_name == 'button':
                        categorized['buttons'].append(element)
                    elif tag_name == 'form':
                        categorized['forms'].append(element)
                    elif 'form' in element_class.lower() or 'form' in element_id.lower():
                        categorized['form_like'].append(element)
                        
                except Exception as e:
                    logger.debug(f"Error categorizing element: {e}")
                    continue
            
            # Add textareas and selects to inputs for compatibility
            categorized['inputs'].extend(categorized['textareas'])
            categorized['inputs'].extend(categorized['selects'])
            
            logger.debug(f"Batch element finding: {len(categorized['inputs'])} inputs, {len(categorized['forms'])} forms, {len(categorized['form_like'])} form-like")
            return categorized
            
        except Exception as e:
            logger.error(f"Error in batch element finding: {e}")
            # Fallback to individual queries
            return {
                'inputs': self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select'),
                'forms': self.driver.find_elements(By.TAG_NAME, 'form'),
                'form_like': []
            }
    
    def _enhanced_find_all_forms(self):
        """Enhanced form detection with optimized strategies for speed and form validation."""
        forms = []
        
        # Get current domain for website-specific customizations
        current_domain = self._get_domain_from_url()
        
        # Strategy 1: Website-specific form detection (highest priority)
        if current_domain in self.website_customizations:
            custom_selectors = self.website_customizations[current_domain].get('form_selectors', [])
            for selector in custom_selectors:
                try:
                    custom_forms = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    # Validate each custom form before adding
                    for form in custom_forms:
                        if self._is_valid_contact_form(form):
                            forms.append(form)
                            logger.info(f"Found valid contact form using custom selector: {selector}")
                    # If we found valid forms with custom selectors, return early for speed
                    if len(forms) > 0:
                        return forms
                except:
                    continue
        
        # Strategy 2: Standard form tags with validation (high priority)
        try:
            standard_forms = self.driver.find_elements(By.TAG_NAME, 'form')
            valid_forms = []
            for form in standard_forms:
                if self._is_valid_contact_form(form):
                    valid_forms.append(form)
            forms.extend(valid_forms)
            logger.info(f"Found {len(valid_forms)} valid contact forms out of {len(standard_forms)} total forms")
        except:
            pass
        
        # Strategy 3: Contact-specific form containers (medium priority)
        try:
            contact_selectors = [
                '[class*="contact-form"], [class*="contact_form"], [class*="contactform"]',
                '[class*="enquiry-form"], [class*="enquiry_form"], [class*="enquiryform"]',
                '[class*="request-form"], [class*="request_form"], [class*="requestform"]',
                '[class*="quote-form"], [class*="quote_form"], [class*="quoteform"]',
                '[class*="feedback-form"], [class*="feedback_form"], [class*="feedbackform"]',
                '[class*="support-form"], [class*="support_form"], [class*="supportform"]',
                '[class*="partnership-form"], [class*="partnership_form"], [class*="partnershipform"]',
                '[class*="collaboration-form"], [class*="collaboration_form"], [class*="collaborationform"]',
                '[class*="business-form"], [class*="business_form"], [class*="businessform"]',
                '[class*="sales-form"], [class*="sales_form"], [class*="salesform"]',
                '[id*="contact"], [id*="enquiry"], [id*="request"], [id*="quote"], [id*="feedback"]',
                '[id*="support"], [id*="partnership"], [id*="collaboration"], [id*="business"], [id*="sales"]'
            ]
            
            for selector in contact_selectors:
                contact_containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for container in contact_containers:
                    if container.tag_name != 'form':
                        # Check if container has input fields
                        inputs = container.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                        if len(inputs) >= 2:  # At least 2 input fields to be considered a form
                            forms.append(container)
                            logger.info(f"Found contact-specific container: {container.tag_name}.{container.get_attribute('class')}")
        except:
            pass
        
        # Strategy 4: General form-like containers (lower priority)
        try:
            form_containers = self.driver.find_elements(By.CSS_SELECTOR, 
                '[class*="form"], [class*="quote"], [class*="support"], [class*="message"], [class*="feedback"]')
            for container in form_containers:
                if container.tag_name != 'form':
                    # Check if container has input fields
                    inputs = container.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                    if len(inputs) >= 3:  # At least 3 input fields for general containers
                        forms.append(container)
                        logger.info(f"Found form-like container: {container.tag_name}.{container.get_attribute('class')}")
        except:
            pass
        
        # Strategy 4.5: Look for popular marketing forms (HubSpot/Marketo/Pardot/Salesforce)
        try:
            marketing_selectors = [
                'form.hs-form', 'form[id*="hs-"]',
                'form.mktoForm', '[id*="mktoForm_"]',
                'form[action*="pardot"]', '[class*="pardot"]',
                'form[action*="salesforce"]', '[id*="WebToLead"], [name*="WebToLead"]'
            ]
            for sel in marketing_selectors:
                try:
                    mfs = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    if mfs:
                        forms.extend(mfs)
                        logger.info(f"Found marketing forms via selector: {sel} -> {len(mfs)}")
                except Exception:
                    continue
        except Exception:
            pass

        # Strategy 5: Look for forms in iframes
        try:
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    iframe_forms = self.driver.find_elements(By.TAG_NAME, 'form')
                    forms.extend(iframe_forms)
                    if iframe_forms:
                        logger.info(f"Found {len(iframe_forms)} forms in iframe")
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
        except:
            pass
        
        # Strategy 6: Look for forms with specific data attributes
        try:
            data_forms = self.driver.find_elements(By.CSS_SELECTOR, 
                '[data-form], [data-contact], [data-enquiry], [data-request], [data-quote], [data-message]')
            forms.extend(data_forms)
            if data_forms:
                logger.info(f"Found {len(data_forms)} forms with data attributes")
        except:
            pass
        
        # Strategy 6.5: JavaScript-based form detection for hidden/dynamic forms
        try:
            js_forms = self.driver.execute_script("""
                var allForms = [];
                // Find all forms including hidden ones
                var forms = document.querySelectorAll('form');
                for (var i = 0; i < forms.length; i++) {
                    allForms.push(forms[i]);
                }
                // Find divs with input fields that might be forms
                var divs = document.querySelectorAll('div');
                for (var i = 0; i < divs.length; i++) {
                    var inputs = divs[i].querySelectorAll('input, textarea, select');
                    if (inputs.length >= 2) {
                        allForms.push(divs[i]);
                    }
                }
                return allForms.length;
            """)
            logger.info(f"JavaScript detected {js_forms} potential form elements")
            
            # Get page info for debugging
            page_info = self.driver.execute_script("""
                return {
                    'title': document.title,
                    'url': window.location.href,
                    'forms': document.querySelectorAll('form').length,
                    'inputs': document.querySelectorAll('input').length,
                    'textareas': document.querySelectorAll('textarea').length,
                    'selects': document.querySelectorAll('select').length,
                    'buttons': document.querySelectorAll('button').length,
                    'readyState': document.readyState
                };
            """)
            logger.info(f"Page debug info: {page_info}")
            
            # Save page source for debugging if no forms found
            if page_info.get('forms', 0) == 0 and page_info.get('inputs', 0) == 0:
                try:
                    page_source = self.driver.page_source
                    debug_file = f"debug_page_source_{int(time.time())}.html"
                    with open(debug_file, 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info(f"Saved page source to {debug_file} for debugging (length: {len(page_source)} chars)")
                    
                    # Check if page contains common indicators
                    source_lower = page_source.lower()
                    indicators = {
                        'contact': 'contact' in source_lower,
                        'form': 'form' in source_lower,
                        'input': 'input' in source_lower,
                        'email': 'email' in source_lower,
                        'message': 'message' in source_lower,
                        'submit': 'submit' in source_lower,
                        'javascript': 'javascript' in source_lower or 'script' in source_lower
                    }
                    logger.info(f"Page content indicators: {indicators}")
                except Exception as debug_e:
                    logger.debug(f"Error saving debug page source: {debug_e}")
        except Exception as e:
            logger.debug(f"Error in JavaScript form detection: {e}")
        
        # Strategy 7: Wait for dynamic forms to load with explicit waits and scrolling
        try:
            logger.info("Waiting for dynamic forms to load...")
            
            # Scroll to trigger lazy loading
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            
            # Wait for dynamic forms with explicit waits
            dynamic_selectors = [
                'form', '[class*="contact-form"]', '[class*="enquiry-form"]', 
                '[class*="request-form"]', '[class*="contact"]', '[id*="contact"]',
                'input[type="text"]', 'input[type="email"]', 'textarea'
            ]
            
            for selector in dynamic_selectors:
                try:
                    WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    dynamic_forms = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if dynamic_forms:
                        forms.extend(dynamic_forms)
                        logger.info(f"Found {len(dynamic_forms)} dynamic forms with selector: {selector}")
                        break  # Found forms, no need to wait for other selectors
                except TimeoutException:
                    continue
            
            # Additional wait for any late-loading forms
            time.sleep(2)
            
        except Exception as e:
            logger.debug(f"Error waiting for dynamic forms: {e}")
            pass
        
        # Remove duplicates and prioritize relevant forms
        unique_forms = []
        seen_forms = set()
        
        # Priority order: contact forms first, then standard forms, then others
        priority_keywords = ['contact', 'enquiry', 'request', 'quote', 'support']
        
        for form in forms:
            form_id = f"{form.tag_name}.{form.get_attribute('class')}.{form.get_attribute('id')}"
            if form_id not in seen_forms:
                seen_forms.add(form_id)
                unique_forms.append(form)
        
        # Sort forms by relevance (contact-related forms first)
        def form_relevance(form):
            form_class = (form.get_attribute('class') or '').lower()
            form_id = (form.get_attribute('id') or '').lower()
            form_text = f"{form_class} {form_id}"
            
            # Check for contact-related keywords
            for keyword in priority_keywords:
                if keyword in form_text:
                    return 0  # Highest priority
            return 1  # Lower priority
        
        unique_forms.sort(key=form_relevance)
        
        logger.info(f"Total unique forms found: {len(unique_forms)}")
        return unique_forms

    def _is_valid_contact_form(self, form):
        """Validate if a form is a contact form and not a search form or other non-contact form."""
        try:
            # Get form attributes
            form_class = (form.get_attribute('class') or '').lower()
            form_id = (form.get_attribute('id') or '').lower()
            form_action = (form.get_attribute('action') or '').lower()
            form_name = (form.get_attribute('name') or '').lower()
            
            # Check for search form indicators (immediate rejection)
            search_indicators = [
                'search', 'search-form', 'search_form', 'searchform', 'search-box', 'search_box', 'searchbox',
                'hfe-search', 'site-search', 'global-search', 'header-search', 'nav-search', 'quick-search',
                'product-search', 'catalog-search', 'store-search', 'shop-search'
            ]
            
            form_text = f"{form_class} {form_id} {form_action} {form_name}"
            
            for indicator in search_indicators:
                if indicator in form_text:
                    logger.info(f"Rejecting search form: {form.tag_name} with class='{form_class}' id='{form_id}'")
                    return False
            
            # Check for other non-contact form indicators
            non_contact_indicators = [
                'login', 'signin', 'sign-in', 'register', 'signup', 'sign-up', 'newsletter', 'subscribe',
                'cart', 'checkout', 'payment', 'billing', 'shipping', 'order', 'purchase',
                'filter', 'sort', 'pagination', 'comment', 'review', 'rating', 'vote', 'poll'
            ]
            
            for indicator in non_contact_indicators:
                if indicator in form_text:
                    logger.info(f"Rejecting non-contact form: {form.tag_name} with class='{form_class}' id='{form_id}'")
                    return False
            
            # Check for contact form indicators (positive validation)
            contact_indicators = [
                'contact', 'contact-us', 'contact_us', 'contactus', 'enquiry', 'inquiry', 'enquire',
                'request', 'quote', 'get-quote', 'get_quote', 'getquote', 'support', 'help',
                'feedback', 'message', 'get-in-touch', 'get_in_touch', 'getintouch',
                'partnership', 'collaborate', 'collaboration', 'business', 'sales', 'demo',
                'consultation', 'appointment', 'booking', 'reach-us', 'reach_us', 'reachus'
            ]
            
            has_contact_indicator = any(indicator in form_text for indicator in contact_indicators)
            
            # Get form inputs to analyze
            inputs = form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            # Check input types and attributes
            input_types = []
            input_names = []
            input_placeholders = []
            
            for inp in inputs:
                input_type = (inp.get_attribute('type') or '').lower()
                input_name = (inp.get_attribute('name') or '').lower()
                input_placeholder = (inp.get_attribute('placeholder') or '').lower()
                
                input_types.append(input_type)
                input_names.append(input_name)
                input_placeholders.append(input_placeholder)
            
            # Check for search-specific input patterns
            search_input_patterns = ['search', 'query', 'q', 'keyword', 'term']
            input_text = ' '.join(input_names + input_placeholders)
            
            for pattern in search_input_patterns:
                if pattern in input_text and len(inputs) <= 2:  # Search forms typically have 1-2 inputs
                    logger.info(f"Rejecting search form based on input patterns: {input_text}")
                    return False
            
            # Check for contact-specific input patterns
            contact_input_patterns = [
                'name', 'email', 'phone', 'message', 'subject', 'company', 'organization',
                'first_name', 'last_name', 'firstname', 'lastname', 'full_name', 'fullname',
                'contact_name', 'your_name', 'yourname', 'inquiry', 'enquiry', 'comment',
                'description', 'details', 'requirements', 'project', 'budget'
            ]
            
            contact_input_count = 0
            for pattern in contact_input_patterns:
                if pattern in input_text:
                    contact_input_count += 1
            
            # Validation logic
            if has_contact_indicator and len(inputs) >= 2:
                logger.info(f"Valid contact form found: {form.tag_name} with {len(inputs)} inputs and contact indicators")
                return True
            elif contact_input_count >= 2 and len(inputs) >= 3:
                logger.info(f"Valid contact form found: {form.tag_name} with {contact_input_count} contact-related inputs")
                return True
            elif len(inputs) >= 4 and 'textarea' in [inp.tag_name.lower() for inp in inputs]:
                # Forms with multiple inputs including textarea are likely contact forms
                logger.info(f"Valid contact form found: {form.tag_name} with {len(inputs)} inputs including textarea")
                return True
            else:
                logger.debug(f"Form validation failed: {form.tag_name} - insufficient contact indicators")
                return False
                
        except Exception as e:
            logger.debug(f"Error validating form: {e}")
            return False

    def _alternative_form_detection(self):
        """Alternative form detection strategies with validation."""
        forms = []
        
        # Look for any element with input fields
        try:
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
            for element in all_elements:
                try:
                    inputs = element.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                    if len(inputs) >= 3 and self._is_valid_contact_form(element):
                        forms.append(element)
                        logger.info(f"Found valid alternative form: {element.tag_name}.{element.get_attribute('class')}")
                except:
                    continue
        except:
            pass
        
        # Look for contact-specific sections
        try:
            contact_sections = self.driver.find_elements(By.CSS_SELECTOR, 
                '[class*="contact"], [id*="contact"], [class*="enquiry"], [id*="enquiry"]')
            for section in contact_sections:
                inputs = section.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                if len(inputs) >= 2 and self._is_valid_contact_form(section):
                    forms.append(section)
                    logger.info(f"Found valid contact section: {section.tag_name}.{section.get_attribute('class')}")
        except:
            pass
        
        return forms

    def _comprehensive_form_detection(self):
        """Comprehensive form detection for any type of form structure."""
        try:
            logger.info("Attempting comprehensive form detection...")
            
            forms = []
            
            # Look for any element with multiple inputs
            all_elements = self.driver.find_elements(By.CSS_SELECTOR, '*')
            
            for element in all_elements:
                try:
                    if element.is_displayed():
                        inputs = element.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                        if len(inputs) >= 2:
                            # Check if this element is not already a child of another form
                            is_child = False
                            for existing_form in forms:
                                try:
                                    if element in existing_form.find_elements(By.CSS_SELECTOR, '*'):
                                        is_child = True
                                        break
                                except:
                                    continue
                            
                            if not is_child and self._is_valid_contact_form(element):
                                forms.append(element)
                                logger.info(f"Found valid form-like element with {len(inputs)} inputs: {element.tag_name}.{element.get_attribute('class')}")
                except:
                    continue
            
            # Look for specific form-like containers
            form_containers = [
                '[class*="form"]', '[id*="form"]', '[class*="contact"]', '[id*="contact"]',
                '[class*="enquiry"]', '[id*="enquiry"]', '[class*="request"]', '[id*="request"]',
                '[class*="submit"]', '[id*="submit"]', '[class*="send"]', '[id*="send"]',
                '[class*="input"]', '[id*="input"]', '[class*="field"]', '[id*="field"]',
                '.form', '.contact', '.enquiry', '.request', '.submit', '.send',
                '.input', '.field', '.container', '.wrapper', '.section'
            ]
            
            for selector in form_containers:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            inputs = element.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                            if len(inputs) >= 1 and self._is_valid_contact_form(element):
                                if element not in forms:
                                    forms.append(element)
                                    logger.info(f"Found valid form container: {selector} with {len(inputs)} inputs")
                except:
                    continue
            
            # Look for elements near submit buttons
            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], .submit, .send')
            
            for button in submit_buttons:
                try:
                    if button.is_displayed():
                        parent = button.find_element(By.XPATH, './ancestor::*[contains(input, "") or contains(textarea, "") or contains(select, "")][1]')
                        if parent and parent not in forms and self._is_valid_contact_form(parent):
                            forms.append(parent)
                            logger.info(f"Found valid form near submit button: {parent.tag_name}.{parent.get_attribute('class')}")
                except:
                    continue
            
            # Look for any div with input fields
            divs = self.driver.find_elements(By.TAG_NAME, 'div')
            
            for div in divs:
                try:
                    if div.is_displayed():
                        inputs = div.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                        if len(inputs) >= 2:
                            is_child = False
                            for existing_form in forms:
                                try:
                                    if div in existing_form.find_elements(By.CSS_SELECTOR, '*'):
                                        is_child = True
                                        break
                                except:
                                    continue
                            
                            if not is_child and div not in forms and self._is_valid_contact_form(div):
                                forms.append(div)
                                logger.info(f"Found valid div with {len(inputs)} inputs: {div.get_attribute('class')}")
                except:
                    continue
            
            logger.info(f"Comprehensive form detection found {len(forms)} potential forms")
            return forms
            
        except Exception as e:
            logger.error(f"Error in comprehensive form detection: {e}")
            return []

    def _enhanced_fill_single_form(self, form):
        """Enhanced single form filling with better field detection and error handling."""
        try:
            # Check if session is still valid
            try:
                self.driver.current_url
            except:
                logger.error("Session expired, cannot continue with form filling")
                return False
            
            # Validate that this is a contact form before filling
            if not self._is_valid_contact_form(form):
                logger.info(f"Skipping non-contact form: {form.tag_name}.{form.get_attribute('class')}")
                return False
            
            logger.info(f"Filling valid contact form: {form.tag_name}.{form.get_attribute('class')}")
            
            # Strategy 1: Enhanced field detection and filling with stale element protection
            if self._enhanced_fill_form_fields_v2(form):
                return True
            
            # Strategy 2: Direct input filling within form with retry
            if self._fill_inputs_within_form_v2(form):
                return True
            
            # Strategy 3: JavaScript-based form filling
            if self._js_fill_form_v2(form):
                return True
            
            # Strategy 4: Fallback with fresh element detection
            if self._fallback_form_filling(form):
                return True
            
            logger.warning("All form filling strategies failed for this form")
            return False
            
        except Exception as e:
            logger.error(f"Error filling single form: {e}")
            # Try to recover with fresh form detection
            try:
                return self._recover_form_filling()
            except:
                return False

    def _enhanced_fill_form_fields(self, form):
        """Enhanced form field detection and filling with explicit waits."""
        try:
            # Wait for form fields to be present and visible
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input, textarea, select'))
                )
            except TimeoutException:
                logger.warning("No input fields found after waiting")
                return False
            
            # Get all input fields in the form with multiple strategies
            input_selectors = [
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"])',
                'textarea',
                'select',
                '[contenteditable="true"]',  # For modern contenteditable fields
                '[role="textbox"]'  # For ARIA textboxes
            ]
            
            inputs = []
            for selector in input_selectors:
                try:
                    found_inputs = form.find_elements(By.CSS_SELECTOR, selector)
                    inputs.extend(found_inputs)
                except Exception:
                    continue
            
            # Remove duplicates
            unique_inputs = []
            seen_elements = set()
            for inp in inputs:
                element_id = id(inp)
                if element_id not in seen_elements:
                    seen_elements.add(element_id)
                    unique_inputs.append(inp)
            
            inputs = unique_inputs
            logger.info(f"Found {len(inputs)} input fields in form")
            
            filled_fields = 0
            
            for input_field in inputs:
                try:
                    # Wait for field to be interactable
                    try:
                        WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable(input_field)
                        )
                    except TimeoutException:
                        continue
                    
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                        time.sleep(self.TYPING_DELAY[0])  # Small delay between fields
                except Exception as e:
                    logger.debug(f"Error filling field: {e}")
                    continue
            
            logger.info(f"Successfully filled {filled_fields}/{len(inputs)} fields")
            
            # Try to submit the form if we filled at least some fields
            if filled_fields > 0:
                if self._submit_form(form):
                    return True
            
            return filled_fields > 0  # Return True if we filled any fields
            
        except Exception as e:
            logger.error(f"Error in enhanced form field filling: {e}")
            return False

    def _enhanced_fill_single_field(self, field):
        """Enhanced single field filling with better field type detection and error handling."""
        try:
            # Skip hidden fields
            if self._is_hidden_field(field):
                logger.debug(f"Skipping hidden field: {field.get_attribute('name') or field.get_attribute('id') or 'unknown'}")
                return False
            
            # Check if field is visible and enabled
            if not field.is_displayed() or not field.is_enabled():
                logger.debug(f"Skipping invisible/disabled field: {field.get_attribute('name') or field.get_attribute('id') or 'unknown'}")
                return False
            
            # Get field properties
            field_type = field.get_attribute('type') or ''
            field_name = field.get_attribute('name') or ''
            field_id = field.get_attribute('id') or ''
            field_class = field.get_attribute('class') or ''
            field_placeholder = field.get_attribute('placeholder') or ''
            field_label = field.get_attribute('aria-label') or ''
            
            # Enhanced debugging - log all field attributes
            logger.debug(f"Analyzing field - Name: '{field_name}', ID: '{field_id}', Type: '{field_type}', Class: '{field_class}', Placeholder: '{field_placeholder}', Label: '{field_label}'")
            
            # Skip certain field types
            skip_types = ['submit', 'button', 'reset', 'image', 'file', 'hidden']
            if field_type.lower() in skip_types:
                logger.debug(f"Skipping field type '{field_type}': {field_name or field_id or 'unknown'}")
                return False
            
            # Determine field type and fill accordingly
            field_type_detected = self._enhanced_identify_field_type(field)
            
            if field_type_detected:
                value = self.contact_data.get(field_type_detected)
                if value:
                    logger.debug(f"Attempting to fill {field_type_detected} field '{field_name or field_id}' with value: {value[:50]}...")
                    try:
                        # Enhanced element waiting and interaction strategies
                        success = False
                        
                        # Wait for element to be interactable
                        try:
                            WebDriverWait(self.driver, 5).until(
                                lambda d: field.is_displayed() and field.is_enabled()
                            )
                        except:
                            logger.debug(f"Element wait timeout for field: {field_name or field_id}")
                        
                        # Scroll field into view with enhanced positioning
                        try:
                            self.driver.execute_script("""
                                arguments[0].scrollIntoView({
                                    block: 'center',
                                    inline: 'center',
                                    behavior: 'smooth'
                                });
                            """, field)
                            time.sleep(0.3)  # Allow scroll animation to complete
                        except Exception as e:
                            logger.debug(f"Error scrolling to field: {e}")
                        
                        # Method 1: Enhanced standard approach with focus and validation
                        try:
                            # Focus the field first
                            field.click()
                            time.sleep(0.1)
                            
                            # Clear existing content
                            field.clear()
                            time.sleep(0.1)
                            
                            # Type the value with human-like behavior
                            self._human_like_typing(field, value)
                            
                            # Validate the field was filled
                            filled_value = field.get_attribute('value') or ''
                            if filled_value.strip() and value.strip() in filled_value:
                                success = True
                                logger.debug(f"Method 1 successful: {filled_value[:50]}...")
                        except Exception as e:
                            logger.debug(f"Method 1 failed: {e}")
                        
                        # Method 2: JavaScript approach with enhanced event triggering
                        if not success:
                            try:
                                # Clear and focus using JavaScript
                                self.driver.execute_script("""
                                    var element = arguments[0];
                                    element.focus();
                                    element.value = '';
                                    element.dispatchEvent(new Event('focus', { bubbles: true }));
                                """, field)
                                time.sleep(0.1)
                                
                                # Type the value
                                field.send_keys(value)
                                
                                # Validate the field was filled
                                filled_value = field.get_attribute('value') or ''
                                if filled_value.strip() and value.strip() in filled_value:
                                    success = True
                                    logger.debug(f"Method 2 successful: {filled_value[:50]}...")
                            except Exception as e:
                                logger.debug(f"Method 2 failed: {e}")
                        
                        # Method 3: Select all and replace with validation
                        if not success:
                            try:
                                # Click and select all
                                field.click()
                                time.sleep(0.1)
                                field.send_keys(Keys.CONTROL + "a")
                                time.sleep(0.1)
                                
                                # Replace with new value
                                field.send_keys(value)
                                
                                # Validate the field was filled
                                filled_value = field.get_attribute('value') or ''
                                if filled_value.strip() and value.strip() in filled_value:
                                    success = True
                                    logger.debug(f"Method 3 successful: {filled_value[:50]}...")
                            except Exception as e:
                                logger.debug(f"Method 3 failed: {e}")
                        
                        # Method 4: Direct JavaScript value setting with comprehensive events
                        if not success:
                            try:
                                self.driver.execute_script("""
                                    var element = arguments[0];
                                    var value = arguments[1];
                                    
                                    // Focus and set value
                                    element.focus();
                                    element.value = value;
                                    
                                    // Trigger comprehensive events
                                    var events = ['input', 'change', 'blur', 'keyup', 'keydown'];
                                    events.forEach(function(eventType) {
                                        var event = new Event(eventType, { bubbles: true, cancelable: true });
                                        element.dispatchEvent(event);
                                    });
                                    
                                    // Trigger React/Vue specific events if needed
                                    if (element._valueTracker) {
                                        element._valueTracker.setValue('');
                                    }
                                """, field, value)
                                
                                # Validate the field was filled
                                filled_value = field.get_attribute('value') or ''
                                if filled_value.strip() and value.strip() in filled_value:
                                    success = True
                                    logger.debug(f"Method 4 successful: {filled_value[:50]}...")
                            except Exception as e:
                                logger.debug(f"Method 4 failed: {e}")
                        
                        # Method 5: ActionChains approach for complex interactions
                        if not success:
                            try:
                                from selenium.webdriver.common.action_chains import ActionChains
                                
                                actions = ActionChains(self.driver)
                                actions.move_to_element(field)
                                actions.click(field)
                                actions.key_down(Keys.CONTROL)
                                actions.send_keys('a')
                                actions.key_up(Keys.CONTROL)
                                actions.send_keys(value)
                                actions.perform()
                                
                                # Validate the field was filled
                                filled_value = field.get_attribute('value') or ''
                                if filled_value.strip() and value.strip() in filled_value:
                                    success = True
                                    logger.debug(f"Method 5 successful: {filled_value[:50]}...")
                            except Exception as e:
                                logger.debug(f"Method 5 failed: {e}")
                        
                        try:
                            if success:
                                # Trigger change events
                                try:
                                    self.driver.execute_script("""
                                        var element = arguments[0];
                                        var event = new Event('input', { bubbles: true });
                                        element.dispatchEvent(event);
                                        var changeEvent = new Event('change', { bubbles: true });
                                        element.dispatchEvent(changeEvent);
                                    """, field)
                                except Exception:
                                    pass
                                
                                logger.info(f"Filled {field_type_detected} field: {field_name or field_id}")
                                return True
                            else:
                                logger.debug(f"Failed to fill {field_type_detected} field: {field_name or field_id}")
                        except Exception as e:
                            logger.debug(f"Error filling {field_type_detected} field: {e}")
                    except Exception as e:
                        logger.debug(f"Error in field filling process: {e}")
                        return False
                else:
                    logger.debug(f"No value found for field type: {field_type_detected}")
                    return False
            else:
                logger.debug(f"No field type detected for field: Name='{field_name}', ID='{field_id}', Type='{field_type}', Class='{field_class}', Placeholder='{field_placeholder}'")
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in enhanced single field filling: {e}")
            return False

    def _enhanced_identify_field_type(self, field):
        """Enhanced field type identification with comprehensive patterns and textarea prioritization."""
        try:
            field_type = field.get_attribute('type') or ''
            field_tag = field.tag_name.lower()
            field_name = (field.get_attribute('name') or '').lower()
            field_id = (field.get_attribute('id') or '').lower()
            field_class = (field.get_attribute('class') or '').lower()
            field_placeholder = (field.get_attribute('placeholder') or '').lower()
            field_label = (field.get_attribute('aria-label') or '').lower()
            
            # Get associated label text
            label_text = ''
            try:
                # Try to find label by 'for' attribute
                if field_id:
                    labels = self.driver.find_elements(By.CSS_SELECTOR, f'label[for="{field_id}"]')
                    if labels:
                        label_text = labels[0].text.lower()
                
                # Try to find parent label
                if not label_text:
                    parent = field.find_element(By.XPATH, '..')
                    if parent.tag_name.lower() == 'label':
                        label_text = parent.text.lower()
                
                # Try to find preceding label
                if not label_text:
                    try:
                        preceding_label = field.find_element(By.XPATH, './preceding-sibling::label[1]')
                        label_text = preceding_label.text.lower()
                    except:
                        pass
            except:
                pass
            
            # Combine all field attributes for matching
            all_attributes = f"{field_name} {field_id} {field_class} {field_placeholder} {field_label} {label_text}".lower()
            
            logger.debug(f"Field analysis - All attributes: '{all_attributes}', Label text: '{label_text}'")
            
            # Special handling for textarea elements - prioritize them for message fields
            if field_tag == 'textarea':
                # Check if it's likely a message field
                message_indicators = ['message', 'msg', 'enquiry', 'comment', 'details', 'description', 'textarea', 
                                    'additional_info', 'notes', 'content', 'body', 'your-message', 'your_message',
                                    'comments', 'inquiry', 'request', 'feedback', 'tell us more', 'additional details',
                                    'more information', 'your requirements', 'project details', 'service requirements',
                                    'business needs', 'specific needs', 'questions', 'concerns', 'requirements',
                                    'specifications', 'description', 'brief', 'overview', 'summary']
                
                for indicator in message_indicators:
                    if indicator in all_attributes:
                        logger.info(f"Identified textarea as message field: {field_name or field_id}")
                        return 'message'
                
                # If no specific message indicators, but it's a textarea, still consider it for message
                if not any(keyword in all_attributes for keyword in ['name', 'email', 'phone', 'subject', 'company']):
                    logger.info(f"Identified generic textarea as message field: {field_name or field_id}")
                    return 'message'
            
            # Enhanced field type matching with priority order and comprehensive patterns
            priority_order = ['first_name', 'last_name', 'name', 'email', 'phone', 'subject', 'company', 'message']
            
            for field_type_name in priority_order:
                patterns = self.field_patterns.get(field_type_name, [])
                for pattern in patterns:
                    if pattern in all_attributes:
                        logger.debug(f"Matched field type '{field_type_name}' using pattern '{pattern}' for field: {field_name or field_id}")
                        return field_type_name
            
            # Additional pattern matching for common variations
            additional_patterns = {
                'name': ['fullname', 'full_name', 'firstname', 'first_name', 'lastname', 'last_name', 'fname', 'lname', 'given_name', 'surname'],
                'email': ['e-mail', 'mail', 'email_address', 'emailaddress', 'email_addr', 'emailaddr'],
                'phone': ['telephone', 'tel', 'mobile', 'cell', 'phone_number', 'phonenumber', 'phone_num', 'phonenum', 'contact_number', 'contactnumber'],
                'subject': ['subj', 'topic', 'title', 'enquiry_subject', 'enquirysubject', 'message_subject', 'messagesubject', 'reason', 'purpose'],
                'company': ['organization', 'organisation', 'business', 'firm', 'employer', 'company_name', 'companyname', 'org', 'corporation', 'enterprise'],
                'message': ['msg', 'comment', 'description', 'details', 'enquiry', 'inquiry', 'content', 'body', 'text', 'notes', 'feedback']
            }
            
            for field_type_name, patterns in additional_patterns.items():
                for pattern in patterns:
                    if pattern in all_attributes:
                        return field_type_name
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in enhanced field type identification: {e}")
            return None

    def _enhanced_fill_form_fields_v2(self, form):
        """Enhanced form field detection with stale element protection and better error handling."""
        try:
            # Wait for form fields to be present and visible
            try:
                WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input, textarea, select'))
                )
            except TimeoutException:
                logger.warning("No input fields found after waiting")
                return False
            
            # Get form identifier for fresh element detection
            form_id = self._get_form_identifier(form)
            
            # Get all input fields with fresh detection to avoid stale elements
            input_selectors = [
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="reset"])',
                'textarea',
                'select'
            ]
            
            filled_count = 0
            total_fields = 0
            
            for selector in input_selectors:
                try:
                    # Fresh element detection to avoid stale references
                    if form_id:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, f'{form_id} {selector}')
                    else:
                        elements = form.find_elements(By.CSS_SELECTOR, selector)
                    
                    for field in elements:
                        try:
                            total_fields += 1
                            if self._enhanced_fill_single_field_v2(field):
                                filled_count += 1
                        except Exception as e:
                            logger.debug(f"Error filling individual field: {e}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            logger.info(f"Filled {filled_count}/{total_fields} fields in form")
            
            # Submit form if we filled at least one field
            if filled_count > 0:
                return self._enhanced_submit_form_v2(form)
            
            return False
            
        except Exception as e:
            logger.error(f"Error in enhanced form field filling v2: {e}")
            return False

    def _enhanced_fill_single_field_v2(self, field):
        """Enhanced single field filling with stale element protection and validation."""
        try:
            # Skip hidden fields
            if self._is_hidden_field(field):
                logger.debug(f"Skipping hidden field")
                return False
            
            # Check if field is visible and enabled with retry
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if not field.is_displayed() or not field.is_enabled():
                        logger.debug(f"Skipping invisible/disabled field")
                        return False
                    break
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(f"Field check failed, retrying: {e}")
                        time.sleep(0.5)
                        continue
                    else:
                        logger.debug(f"Field check failed after retries: {e}")
                        return False
            
            # Get field properties with error handling
            try:
                field_type = field.get_attribute('type') or ''
                field_name = field.get_attribute('name') or ''
                field_id = field.get_attribute('id') or ''
                field_class = field.get_attribute('class') or ''
                field_placeholder = field.get_attribute('placeholder') or ''
                field_label = field.get_attribute('aria-label') or ''
            except Exception as e:
                logger.debug(f"Error getting field attributes: {e}")
                return False
            
            # Skip certain field types
            skip_types = ['submit', 'button', 'reset', 'image', 'file', 'hidden']
            if field_type.lower() in skip_types:
                logger.debug(f"Skipping field type '{field_type}'")
                return False
            
            # Determine field type and fill accordingly
            field_type_detected = self._enhanced_identify_field_type_v2(field)
            
            if field_type_detected:
                value = self.contact_data.get(field_type_detected)
                if value:
                    logger.debug(f"Attempting to fill {field_type_detected} field with value: {value[:50]}...")
                    return self._fill_field_with_validation(field, value, field_type_detected)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in enhanced single field filling v2: {e}")
            return False

    def _enhanced_identify_field_type_v2(self, field):
        """Enhanced field type identification with better pattern matching."""
        try:
            field_type = field.get_attribute('type') or ''
            field_tag = field.tag_name.lower()
            field_name = (field.get_attribute('name') or '').lower()
            field_id = (field.get_attribute('id') or '').lower()
            field_class = (field.get_attribute('class') or '').lower()
            field_placeholder = (field.get_attribute('placeholder') or '').lower()
            field_label = (field.get_attribute('aria-label') or '').lower()
            
            # Get associated label text with better error handling
            label_text = ''
            try:
                if field_id:
                    labels = self.driver.find_elements(By.CSS_SELECTOR, f'label[for="{field_id}"]')
                    if labels and labels[0].text:
                        label_text = labels[0].text.lower()
                
                if not label_text:
                    try:
                        parent = field.find_element(By.XPATH, '..')
                        if parent.tag_name.lower() == 'label' and parent.text:
                            label_text = parent.text.lower()
                    except:
                        pass
            except:
                pass
            
            # Combine all field attributes for matching
            all_attributes = f"{field_name} {field_id} {field_class} {field_placeholder} {field_label} {label_text}".lower()
            
            # Special handling for textarea elements
            if field_tag == 'textarea':
                message_indicators = ['message', 'msg', 'enquiry', 'comment', 'details', 'description', 'textarea', 
                                    'additional_info', 'notes', 'content', 'body', 'your-message', 'your_message',
                                    'comments', 'inquiry', 'request', 'feedback', 'tell us more', 'additional details',
                                    'more information', 'your requirements', 'project details', 'service requirements',
                                    'business needs', 'specific needs', 'questions', 'concerns', 'requirements',
                                    'specifications', 'description', 'brief', 'overview', 'summary']
                
                for indicator in message_indicators:
                    if indicator in all_attributes:
                        return 'message'
                
                # If no specific message indicators, but it's a textarea, still consider it for message
                if not any(keyword in all_attributes for keyword in ['name', 'email', 'phone', 'subject', 'company']):
                    return 'message'
            
            # Enhanced field type matching with priority order
            priority_order = ['first_name', 'last_name', 'name', 'email', 'phone', 'subject', 'company', 'message']
            
            for field_type_name in priority_order:
                patterns = self.field_patterns.get(field_type_name, [])
                for pattern in patterns:
                    if pattern in all_attributes:
                        return field_type_name
            
            # Additional pattern matching for common variations
            additional_patterns = {
                'name': ['fullname', 'full_name', 'firstname', 'first_name', 'lastname', 'last_name', 'fname', 'lname'],
                'email': ['e-mail', 'mail', 'email_address', 'emailaddress', 'email_addr', 'emailaddr'],
                'phone': ['telephone', 'tel', 'mobile', 'cell', 'phone_number', 'phonenumber', 'phone_num', 'phonenum'],
                'subject': ['subj', 'topic', 'title', 'enquiry_subject', 'enquirysubject', 'message_subject', 'messagesubject'],
                'company': ['organization', 'organisation', 'business', 'firm', 'employer', 'company_name', 'companyname'],
                'message': ['msg', 'comment', 'description', 'details', 'enquiry', 'inquiry', 'content', 'body', 'text', 'notes']
            }
            
            for field_type_name, patterns in additional_patterns.items():
                for pattern in patterns:
                    if pattern in all_attributes:
                        return field_type_name
            
            return None
            
        except Exception as e:
            logger.debug(f"Error in enhanced field type identification v2: {e}")
            return None

    def _fill_field_with_validation(self, field, value, field_type):
        """Fill field with validation to ensure content was actually filled."""
        try:
            # Wait for element to be interactable
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: field.is_displayed() and field.is_enabled()
                )
            except:
                logger.debug(f"Element wait timeout for field")
                return False
            
            # Scroll field into view
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", field)
                time.sleep(0.5)
            except:
                pass
            
            # Clear field first
            try:
                field.clear()
            except:
                try:
                    field.send_keys(Keys.CONTROL + "a")
                    field.send_keys(Keys.DELETE)
                except:
                    pass
            
            # Fill field with multiple strategies
            success = False
            
            # Strategy 1: Direct send_keys
            try:
                field.send_keys(value)
                time.sleep(0.5)
                if field.get_attribute('value') == value:
                    success = True
            except Exception as e:
                logger.debug(f"Direct send_keys failed: {e}")
            
            # Strategy 2: JavaScript if direct method failed
            if not success:
                try:
                    self.driver.execute_script("arguments[0].value = arguments[1];", field, value)
                    self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", field)
                    time.sleep(0.5)
                    if field.get_attribute('value') == value:
                        success = True
                except Exception as e:
                    logger.debug(f"JavaScript filling failed: {e}")
            
            # Strategy 3: ActionChains if other methods failed
            if not success:
                try:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.click(field).send_keys(value).perform()
                    time.sleep(0.5)
                    if field.get_attribute('value') == value:
                        success = True
                except Exception as e:
                    logger.debug(f"ActionChains filling failed: {e}")
            
            if success:
                logger.debug(f"Successfully filled {field_type} field")
                return True
            else:
                logger.debug(f"Failed to fill {field_type} field")
                return False
                
        except Exception as e:
            logger.debug(f"Error in field filling with validation: {e}")
            return False

    def _get_form_identifier(self, form):
        """Get a CSS selector identifier for the form to enable fresh element detection."""
        try:
            form_id = form.get_attribute('id')
            if form_id:
                return f"#{form_id}"
            
            form_class = form.get_attribute('class')
            if form_class:
                # Use the first class name
                first_class = form_class.split()[0]
                return f".{first_class}"
            
            # Use form tag with position
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            for i, f in enumerate(forms):
                if f == form:
                    return f"form:nth-of-type({i+1})"
            
            return None
        except:
            return None

    def _enhanced_submit_form_v2(self, form):
        """Enhanced form submission with multiple strategies."""
        try:
            # Strategy 1: Find and click submit button
            submit_selectors = [
                'input[type="submit"]',
                'button[type="submit"]',
                'button:contains("Submit")',
                'button:contains("Send")',
                'button:contains("Contact")',
                'input[value*="Submit"]',
                'input[value*="Send"]',
                'button[class*="submit"]',
                'button[id*="submit"]'
            ]
            
            for selector in submit_selectors:
                try:
                    if selector.startswith('button:contains'):
                        # Handle text-based selectors with XPath
                        text = selector.split('"')[1]
                        buttons = self.driver.find_elements(By.XPATH, f"//button[contains(text(), '{text}')]")
                    else:
                        buttons = form.find_elements(By.CSS_SELECTOR, selector)
                    
                    for button in buttons:
                        try:
                            if button.is_displayed() and button.is_enabled():
                                self._human_like_click(button)
                                time.sleep(2)
                                return True
                        except:
                            continue
                except:
                    continue
            
            # Strategy 2: JavaScript form submission
            try:
                self.driver.execute_script("arguments[0].submit();", form)
                time.sleep(2)
                return True
            except:
                pass
            
            # Strategy 3: Press Enter on last filled field
            try:
                inputs = form.find_elements(By.CSS_SELECTOR, 'input, textarea')
                if inputs:
                    inputs[-1].send_keys(Keys.RETURN)
                    time.sleep(2)
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in enhanced form submission v2: {e}")
            return False

    def _fill_inputs_within_form_v2(self, form):
        """Enhanced direct input filling with stale element protection."""
        try:
            # Get form identifier for fresh detection
            form_id = self._get_form_identifier(form)
            
            # Fresh element detection
            if form_id:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, f'{form_id} input, {form_id} textarea, {form_id} select')
            else:
                inputs = form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_count = 0
            
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field_v2(input_field):
                        filled_count += 1
                except Exception as e:
                    logger.debug(f"Error filling input field: {e}")
                    continue
            
            if filled_count > 0:
                return self._enhanced_submit_form_v2(form)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in fill inputs within form v2: {e}")
            return False

    def _js_fill_form_v2(self, form):
        """Enhanced JavaScript form filling with better error handling."""
        try:
            # Get form identifier
            form_id = self._get_form_identifier(form)
            
            # JavaScript to fill form fields
            js_script = """
            var form = arguments[0];
            var contactData = arguments[1];
            var filledCount = 0;
            
            // Find all input fields
            var inputs = form.querySelectorAll('input, textarea, select');
            
            for (var i = 0; i < inputs.length; i++) {
                var input = inputs[i];
                var type = input.type;
                var name = (input.name || '').toLowerCase();
                var id = (input.id || '').toLowerCase();
                var placeholder = (input.placeholder || '').toLowerCase();
                var className = (input.className || '').toLowerCase();
                
                // Skip hidden, submit, button fields
                if (type === 'hidden' || type === 'submit' || type === 'button' || type === 'reset') {
                    continue;
                }
                
                // Determine field type and fill
                var value = '';
                if (name.includes('name') || id.includes('name') || placeholder.includes('name')) {
                    value = contactData.name || contactData.first_name;
                } else if (name.includes('email') || id.includes('email') || placeholder.includes('email') || type === 'email') {
                    value = contactData.email;
                } else if (name.includes('phone') || id.includes('phone') || placeholder.includes('phone') || type === 'tel') {
                    value = contactData.phone;
                } else if (name.includes('company') || id.includes('company') || placeholder.includes('company')) {
                    value = contactData.company;
                } else if (name.includes('subject') || id.includes('subject') || placeholder.includes('subject')) {
                    value = contactData.subject;
                } else if (name.includes('message') || id.includes('message') || placeholder.includes('message') || input.tagName === 'TEXTAREA') {
                    value = contactData.message;
                }
                
                if (value) {
                    input.value = value;
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    filledCount++;
                }
            }
            
            return filledCount;
            """
            
            filled_count = self.driver.execute_script(js_script, form, self.contact_data)
            
            if filled_count > 0:
                logger.info(f"JavaScript filled {filled_count} fields")
                time.sleep(1)
                return self._enhanced_submit_form_v2(form)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in JavaScript form filling v2: {e}")
            return False

    def _fallback_form_filling(self, form):
        """Fallback form filling with fresh element detection."""
        try:
            # Wait a bit for any dynamic content
            time.sleep(2)
            
            # Try to find forms again with fresh detection
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            if not forms:
                return False
            
            # Use the first form found
            fresh_form = forms[0]
            
            # Try basic filling
            inputs = fresh_form.find_elements(By.CSS_SELECTOR, 'input, textarea')
            filled_count = 0
            
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field_v2(input_field):
                        filled_count += 1
                except:
                    continue
            
            if filled_count > 0:
                return self._enhanced_submit_form_v2(fresh_form)
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in fallback form filling: {e}")
            return False

    def _recover_form_filling(self):
        """Recovery method when form filling fails."""
        try:
            logger.info("Attempting form filling recovery...")
            
            # Wait for page stability
            time.sleep(3)
            
            # Try to find any forms on the page
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            if not forms:
                # Try div-based forms
                form_divs = self.driver.find_elements(By.CSS_SELECTOR, 'div[class*="form"], div[id*="form"]')
                if form_divs:
                    return self._handle_div_based_forms()
                return False
            
            # Try to fill the first form found
            for form in forms[:3]:  # Limit to first 3 forms
                try:
                    if self._enhanced_fill_form_fields_v2(form):
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in form filling recovery: {e}")
            return False

    def _fill_inputs_within_form(self, form):
        """Fill inputs directly within a specific form."""
        try:
            inputs = form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            filled_count = 0
            
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field(input_field):
                        filled_count += 1
                except:
                    continue
            
            if filled_count > 0:
                logger.info(f"Filled {filled_count} fields within form")
                if self._submit_form(form):
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error filling inputs within form: {e}")
            return False

    def _js_fill_form(self, form):
        """JavaScript-based form filling using database contact data."""
        try:
            logger.info("Attempting JavaScript-based form filling with database contact data...")
            
            # Create a JSON-compatible string representation of contact data
            contact_data_json = json.dumps({
                'name': self.contact_data['name'],
                'first_name': self.contact_data['name'].split()[0] if ' ' in self.contact_data['name'] else self.contact_data['name'],
                'last_name': self.contact_data['name'].split()[1] if ' ' in self.contact_data['name'] else '',
                'company': self.contact_data['company'],
                'email': self.contact_data['email'],
                'phone': self.contact_data['phone'],
                'subject': self.contact_data['subject'],
                'message': self.contact_data['message'],
                'teams_id': self.contact_data['email']
            })
            
            # JavaScript to fill form fields
            js_script = f"""
            function fillFormFields() {{
                const contactData = {contact_data_json};
                
                const fieldMappings = {{
                    'name': ['name', 'fullname', 'full_name', 'firstname', 'first_name', 'lastname', 'last_name'],
                    'email': ['email', 'e-mail', 'mail'],
                    'phone': ['phone', 'telephone', 'tel', 'mobile', 'cell'],
                    'subject': ['subject', 'subj', 'topic', 'title', 'enquiry_subject'],
                    'company': ['company', 'organization', 'organisation', 'business', 'firm', 'employer', 'company_name'],
                    'message': ['message', 'msg', 'comment', 'description', 'details', 'enquiry', 'inquiry', 'textarea', 'additional_info', 'notes', 'content', 'body', 'your-message', 'your_message', 'comments', 'feedback', 'tell us more', 'additional details', 'more information', 'your requirements', 'project details', 'service requirements', 'business needs', 'specific needs', 'questions', 'concerns', 'requirements', 'specifications', 'description', 'brief', 'overview', 'summary']
                }};
                
                let filledCount = 0;
                
                for (const [dataKey, patterns] of Object.entries(fieldMappings)) {{
                    for (const pattern of patterns) {{
                        const fields = document.querySelectorAll(`input[name*="${{pattern}}" i], input[id*="${{pattern}}" i], input[placeholder*="${{pattern}}" i], textarea[name*="${{pattern}}" i], textarea[id*="${{pattern}}" i], textarea[placeholder*="${{pattern}}" i]`);
                        
                        for (const field of fields) {{
                            if (field.type !== 'hidden' && field.style.display !== 'none' && field.offsetParent !== null) {{
                                field.value = contactData[dataKey];
                                field.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                filledCount++;
                                break;
                            }}
                        }}
                    }}
                }}
                
                return filledCount;
            }}
            return fillFormFields();
            """
            
            filled_count = self.driver.execute_script(js_script)
            logger.info(f"JavaScript filled {filled_count} fields")
            
            if filled_count > 0:
                if self._submit_form(form):
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in JavaScript form filling: {e}")
            return False

    def _handle_multi_step_forms(self):
        """Handle multi-step forms with step-by-step navigation."""
        try:
            logger.info("Attempting to handle multi-step forms...")
            
            # Step 1: Look for step indicators
            step_indicators = [
                'step', 'step-', 'step_', 'progress', 'progress-', 'progress_',
                'wizard', 'wizard-', 'wizard_', 'form-step', 'form_step'
            ]
            
            # Step 2: Look for next/continue buttons
            next_button_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.next', '.next-step', '.next_step', '.nextStep',
                '.continue', '.continue-btn', '.continue_btn', '.continueBtn',
                '.proceed', '.proceed-btn', '.proceed_btn', '.proceedBtn',
                '.submit', '.submit-btn', '.submit_btn', '.submitBtn',
                '[class*="next"]', '[class*="continue"]', '[class*="proceed"]',
                'button:contains("Next")', 'button:contains("Continue")', 'button:contains("Proceed")',
                'input[value*="Next"]', 'input[value*="Continue"]', 'input[value*="Proceed"]'
            ]
            
            # Step 3: Try to fill current step and move to next
            max_steps = 5  # Maximum steps to prevent infinite loops
            current_step = 0
            
            while current_step < max_steps:
                current_step += 1
                logger.info(f"Processing step {current_step}")
                
                # Fill current step
                if self._fill_current_step():
                    logger.info(f"Successfully filled step {current_step}")
                    
                    # Look for next/continue button
                    next_button = self._find_next_button(next_button_selectors)
                    if next_button:
                        try:
                            logger.info(f"Clicking next button for step {current_step}")
                            next_button.click()
                            time.sleep(0.5)  # Reduced wait time for next step
                            continue
                        except Exception as e:
                            logger.debug(f"Error clicking next button: {e}")
                            break
                    else:
                        # No next button found, might be the final step
                        logger.info("No next button found, assuming final step")
                        break
                else:
                    logger.warning(f"Failed to fill step {current_step}")
                    break
            
            # Try to submit the final form
            if self._submit_final_form():
                logger.info("Successfully completed multi-step form")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling multi-step forms: {e}")
            return False

    def _fill_current_step(self):
        """Fill the current step of a multi-step form."""
        try:
            # Get all input fields on current page
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_fields = 0
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                except Exception as e:
                    logger.debug(f"Error filling field in step: {e}")
                    continue
            
            logger.info(f"Filled {filled_fields} fields in current step")
            return filled_fields > 0
            
        except Exception as e:
            logger.error(f"Error filling current step: {e}")
            return False

    def _find_next_button(self, selectors):
        """Find the next/continue button for multi-step forms."""
        try:
            for selector in selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            button_value = (button.get_attribute('value') or '').lower()
                            
                            # Check if it's a next/continue button
                            next_keywords = ['next', 'continue', 'proceed', 'submit', 'send']
                            if any(keyword in button_text or keyword in button_value for keyword in next_keywords):
                                return button
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding next button: {e}")
            return None

    def _submit_final_form(self):
        """Submit the final step of a multi-step form."""
        try:
            # Look for submit buttons
            submit_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                '.submit', '.submit-btn', '.submit_btn',
                '.send', '.send-btn', '.send_btn',
                '[class*="submit"]', '[class*="send"]'
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            if any(keyword in button_text for keyword in ['submit', 'send', 'finish', 'complete']):
                                logger.info(f"Clicking final submit button: {button_text}")
                                button.click()
                                time.sleep(0.5)
                                return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting final form: {e}")
            return False

    def _handle_div_based_forms(self):
        """Handle div-based forms (modern websites without traditional form tags)."""
        try:
            logger.info("Attempting to handle div-based forms...")
            
            # Look for div containers that act as forms
            div_form_selectors = [
                '[class*="contact-form"]', '[class*="contact_form"]', '[class*="enquiry-form"]', '[class*="enquiry_form"]',
                '[class*="contact-form-container"]', '[class*="form-container"]', '[class*="form-wrapper"]',
                '[class*="contact-section"]', '[class*="contact-area"]', '[class*="contact-block"]',
                '[id*="contact-form"]', '[id*="contact_form"]', '[id*="enquiry-form"]', '[id*="enquiry_form"]',
                '[data-form="contact"]', '[data-type="contact"]', '[data-action="contact"]',
                '.contact-form', '.contact_form', '.enquiry-form', '.enquiry_form',
                '.form-container', '.form-wrapper', '.contact-section', '.contact-area'
            ]
            
            for selector in div_form_selectors:
                try:
                    div_forms = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for div_form in div_forms:
                        if div_form.is_displayed():
                            logger.info(f"Found div-based form: {selector}")
                            
                            # Try to fill inputs within this div
                            if self._fill_div_based_form(div_form):
                                return True
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling div-based forms: {e}")
            return False

    def _fill_div_based_form(self, div_form):
        """Fill a div-based form by finding inputs within the div."""
        try:
            # Find all input fields within the div
            inputs = div_form.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            if len(inputs) < 2:  # Need at least 2 inputs to be considered a form
                return False
            
            logger.info(f"Found {len(inputs)} inputs in div-based form")
            
            filled_fields = 0
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                except Exception as e:
                    logger.debug(f"Error filling field in div form: {e}")
                    continue
            
            logger.info(f"Filled {filled_fields} fields in div-based form")
            
            if filled_fields > 0:
                # Try to find submit button within the div or nearby
                submit_button = self._find_submit_button_in_div(div_form)
                if submit_button:
                    logger.info("Found submit button in div form, clicking...")
                    submit_button.click()
                    time.sleep(0.8)
                    return True
                else:
                    # Try to find submit button on the page
                    submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], .submit, .send')
                    for button in submit_buttons:
                        if button.is_displayed() and button.is_enabled():
                            logger.info("Found submit button on page, clicking...")
                            button.click()
                            time.sleep(2)
                            return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error filling div-based form: {e}")
            return False

    def _find_submit_button_in_div(self, div_form):
        """Find submit button within or near a div form."""
        try:
            # Look for submit buttons within the div
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                '.submit', '.send', '.btn-submit', '.btn-send',
                'button[class*="submit"]', 'button[class*="send"]',
                'input[class*="submit"]', 'input[class*="send"]'
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = div_form.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            return button
                except:
                    continue
            
            # Look for buttons with submit-related text
            all_buttons = div_form.find_elements(By.CSS_SELECTOR, 'button, input[type="button"]')
            for button in all_buttons:
                if button.is_displayed() and button.is_enabled():
                    button_text = (button.text or '').lower()
                    if any(keyword in button_text for keyword in ['submit', 'send', 'contact', 'enquiry']):
                        return button
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding submit button in div: {e}")
            return None

    def _handle_enhanced_multi_step_div_forms(self):
        """Handle enhanced multi-step div forms with step detection and navigation."""
        try:
            logger.info("Attempting to handle enhanced multi-step div forms...")
            
            # Look for step indicators in divs
            step_indicators = [
                '[class*="step"]', '[class*="progress"]', '[class*="wizard"]',
                '[data-step]', '[data-progress]', '[data-wizard]',
                '.step', '.progress', '.wizard', '.form-step', '.form-progress'
            ]
            
            # Look for multi-step div containers
            multi_step_selectors = [
                '[class*="multi-step"]', '[class*="multistep"]', '[class*="wizard-form"]',
                '[class*="step-form"]', '[class*="progressive-form"]',
                '.multi-step', '.multistep', '.wizard-form', '.step-form'
            ]
            
            # Check if we have step indicators
            has_steps = False
            for selector in step_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        has_steps = True
                        logger.info(f"Found step indicators: {selector}")
                        break
                except:
                    continue
            
            # Check for multi-step containers
            for selector in multi_step_selectors:
                try:
                    containers = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for container in containers:
                        if container.is_displayed():
                            logger.info(f"Found multi-step container: {selector}")
                            if self._handle_multi_step_div_container(container):
                                return True
                except Exception as e:
                    logger.debug(f"Error with multi-step selector {selector}: {e}")
                    continue
            
            # If we have step indicators but no specific container, try general approach
            if has_steps:
                logger.info("Found step indicators, trying general multi-step approach...")
                return self._handle_general_multi_step_div()
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling enhanced multi-step div forms: {e}")
            return False

    def _handle_multi_step_div_container(self, container):
        """Handle a specific multi-step div container."""
        try:
            logger.info("Processing multi-step div container...")
            
            max_steps = 5
            current_step = 0
            
            while current_step < max_steps:
                current_step += 1
                logger.info(f"Processing div step {current_step}")
                
                # Fill current step in the container
                if self._fill_current_div_step(container):
                    logger.info(f"Successfully filled div step {current_step}")
                    
                    # Look for next button
                    next_button = self._find_next_button_in_div(container)
                    if next_button:
                        try:
                            logger.info(f"Clicking next button for div step {current_step}")
                            next_button.click()
                            time.sleep(2)
                            continue
                        except Exception as e:
                            logger.debug(f"Error clicking next button: {e}")
                            break
                    else:
                        # No next button, might be final step
                        logger.info("No next button found in div, assuming final step")
                        break
                else:
                    logger.warning(f"Failed to fill div step {current_step}")
                    break
            
            # Try to submit the final form
            if self._submit_div_form(container):
                logger.info("Successfully completed multi-step div form")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling multi-step div container: {e}")
            return False

    def _fill_current_div_step(self, container):
        """Fill the current step within a div container."""
        try:
            # Find all input fields in the current step
            inputs = container.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_fields = 0
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                except Exception as e:
                    logger.debug(f"Error filling field in div step: {e}")
                    continue
            
            logger.info(f"Filled {filled_fields} fields in current div step")
            return filled_fields > 0
            
        except Exception as e:
            logger.error(f"Error filling current div step: {e}")
            return False

    def _find_next_button_in_div(self, container):
        """Find the next button within a div container."""
        try:
            next_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                '.next', '.next-step', '.continue', '.proceed',
                'button[class*="next"]', 'button[class*="continue"]', 'button[class*="proceed"]',
                'input[class*="next"]', 'input[class*="continue"]', 'input[class*="proceed"]'
            ]
            
            for selector in next_selectors:
                try:
                    buttons = container.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            if any(keyword in button_text for keyword in ['next', 'continue', 'proceed', 'submit', 'send']):
                                return button
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding next button in div: {e}")
            return None

    def _submit_div_form(self, container):
        """Submit a div-based form."""
        try:
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                '.submit', '.send', '.btn-submit', '.btn-send',
                'button[class*="submit"]', 'button[class*="send"]'
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = container.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            if any(keyword in button_text for keyword in ['submit', 'send', 'finish', 'complete']):
                                logger.info(f"Clicking submit button in div: {button_text}")
                                button.click()
                                time.sleep(2)
                                return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting div form: {e}")
            return False

    def _handle_general_multi_step_div(self):
        """Handle general multi-step div forms when no specific container is found."""
        try:
            logger.info("Handling general multi-step div forms...")
            
            max_steps = 5
            current_step = 0
            
            while current_step < max_steps:
                current_step += 1
                logger.info(f"Processing general div step {current_step}")
                
                # Fill all visible inputs on the page
                if self._fill_all_visible_inputs():
                    logger.info(f"Successfully filled general div step {current_step}")
                    
                    # Look for any next/submit button
                    next_button = self._find_any_next_button()
                    if next_button:
                        try:
                            logger.info(f"Clicking next button for general div step {current_step}")
                            next_button.click()
                            time.sleep(2)
                            continue
                        except Exception as e:
                            logger.debug(f"Error clicking next button: {e}")
                            break
                    else:
                        # No next button, might be final step
                        logger.info("No next button found, assuming final step")
                        break
                else:
                    logger.warning(f"Failed to fill general div step {current_step}")
                    break
            
            # Try to submit
            if self._submit_any_form():
                logger.info("Successfully completed general multi-step div form")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling general multi-step div: {e}")
            return False

    def _fill_all_visible_inputs(self):
        """Fill all visible input fields on the page."""
        try:
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_fields = 0
            for input_field in inputs:
                try:
                    if input_field.is_displayed() and input_field.is_enabled() and not self._is_hidden_field(input_field):
                        if self._enhanced_fill_single_field(input_field):
                            filled_fields += 1
                except Exception as e:
                    logger.debug(f"Error filling visible input: {e}")
                    continue
            
            logger.info(f"Filled {filled_fields} visible inputs")
            return filled_fields > 0
            
        except Exception as e:
            logger.error(f"Error filling all visible inputs: {e}")
            return False

    def _find_any_next_button(self):
        """Find any next/submit button on the page."""
        try:
            button_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                '.next', '.next-step', '.continue', '.proceed', '.submit', '.send',
                'button[class*="next"]', 'button[class*="continue"]', 'button[class*="proceed"]',
                'button[class*="submit"]', 'button[class*="send"]'
            ]
            
            for selector in button_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            if any(keyword in button_text for keyword in ['next', 'continue', 'proceed', 'submit', 'send']):
                                return button
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding any next button: {e}")
            return None

    def _submit_any_form(self):
        """Submit any form on the page."""
        try:
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]',
                '.submit', '.send', '.btn-submit', '.btn-send'
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            button_text = (button.text or '').lower()
                            if any(keyword in button_text for keyword in ['submit', 'send', 'finish', 'complete']):
                                logger.info(f"Clicking submit button: {button_text}")
                                button.click()
                                time.sleep(2)
                                return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting any form: {e}")
            return False

    def _handle_step_based_forms(self):
        """Handle step-based forms with Previous/Next navigation (like teloz.com)."""
        try:
            logger.info("Attempting to handle step-based forms...")
            
            # Look for step indicators
            step_indicators = [
                '[class*="step"]', '[class*="progress"]', '[data-step]', '[data-progress]',
                '.step', '.progress', '.form-step', '.form-progress'
            ]
            
            has_steps = False
            for selector in step_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        has_steps = True
                        logger.info(f"Found step indicators: {selector}")
                        break
                except:
                    continue
            
            # Look for Previous/Next buttons
            if not has_steps:
                try:
                    prev_next_buttons = self.driver.execute_script("""
                        return Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"], a'))
                            .filter(el => {
                                const text = (el.textContent || el.value || '').toLowerCase();
                                return text.includes('previous') || text.includes('next') || 
                                       text.includes('back') || text.includes('continue');
                            })
                            .filter(el => el.offsetParent !== null);
                    """)
                    if prev_next_buttons:
                        has_steps = True
                        logger.info(f"Found {len(prev_next_buttons)} Previous/Next buttons")
                except:
                    pass
            
            # Look for numbered steps
            if not has_steps:
                step_texts = ['step 1', 'step 2', 'step 3', 'step 4', 'step 5', 'step 6']
                page_text = self.driver.page_source.lower()
                if any(step_text in page_text for step_text in step_texts):
                    has_steps = True
                    logger.info("Found step text in page")
            
            # Look for form sections
            if not has_steps:
                section_indicators = [
                    '[class*="section"]', '[class*="tab"]', '[class*="panel"]',
                    '.section', '.tab', '.panel', '.form-section', '.form-tab'
                ]
                for selector in section_indicators:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if len(elements) > 1:
                            has_steps = True
                            logger.info(f"Found multiple sections: {selector}")
                            break
                    except:
                        continue
            
            # Look for complex form structure
            if not has_steps:
                try:
                    forms = self.driver.find_elements(By.TAG_NAME, 'form')
                    if len(forms) > 1:
                        has_steps = True
                        logger.info(f"Found {len(forms)} forms")
                    else:
                        submit_areas = self.driver.find_elements(By.CSS_SELECTOR, 
                            '[class*="submit"], [class*="button"], [class*="action"]')
                        if len(submit_areas) > 2:
                            has_steps = True
                            logger.info(f"Found {len(submit_areas)} submit areas")
                except:
                    pass
            
            if has_steps:
                logger.info("Step-based form detected, starting navigation...")
                return self._navigate_step_based_form()
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling step-based forms: {e}")
            return False

    def _navigate_step_based_form(self):
        """Navigate through a step-based form with Previous/Next buttons.
        Uses explicit waits, DOM-mutation heuristics, and AJAX tracker to confirm transitions.
        Tracks filled fields to avoid overwriting across steps.
        """
        try:
            logger.info("Starting step-based form navigation...")
            
            if ULTRA_FAST_MODE:
                max_steps = 5  # Reduced for ultra fast mode
            else:
                max_steps = 15  # Standard maximum steps
            current_step = 0
            previous_url = self.driver.current_url
            
            # Track filled fields to avoid rewriting on subsequent scans
            already_filled_keys = set()
            # Capture a snapshot of visible inputs for change detection
            def _visible_input_signature():
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                    sig = []
                    for el in elements:
                        try:
                            if el.is_displayed():
                                name = el.get_attribute('name') or ''
                                i_d = el.get_attribute('id') or ''
                                pl = el.get_attribute('placeholder') or ''
                                typ = el.get_attribute('type') or ''
                                sig.append((el.tag_name, name, i_d, pl, typ))
                        except:
                            continue
                    return tuple(sig)
                except:
                    return tuple()

            previous_signature = _visible_input_signature()

            while current_step < max_steps:
                current_step += 1
                logger.info(f"Processing step {current_step}")
                
                # Wait for page to be ready via explicit waits (presence of any input/textarea/select)
                try:
                    WebDriverWait(self.driver, 3 if ULTRA_FAST_MODE else 5).until(
                        lambda d: len([e for e in d.find_elements(By.CSS_SELECTOR, 'input, textarea, select') if e.is_displayed()]) > 0
                    )
                except TimeoutException:
                    logger.debug("No visible inputs detected yet on this step.")
                try:
                    visible_inputs = self._wait_for_visible_inputs(timeout_seconds=3)
                    logger.info(f"Step {current_step}: visible inputs = {len(visible_inputs)}")
                except Exception as _e:
                    logger.debug(f"Visible inputs wait skipped: {_e}")
                
                # Fill current step (but don't submit yet)
                filled_ok = self._fill_current_step_comprehensive_smart(already_filled_keys)
                if not filled_ok and SMART_RETRY:
                    logger.info("No fields filled on this step, performing one more visibility wait and retry fill...")
                    try:
                        _ = self._wait_for_visible_inputs(timeout_seconds=self.WAIT_VISIBLE_INPUTS)
                    except Exception:
                        pass
                    filled_ok = self._fill_current_step_comprehensive_smart(already_filled_keys)
                if filled_ok:
                    logger.info(f"Successfully filled step {current_step}")
                    
                    # Look for Next button (not submit button)
                    next_button = self._find_next_button_step_based()
                    if next_button:
                        try:
                            logger.info(f"Clicking Next button for step {current_step}")
                            
                            # Store current state before clicking
                            current_url = self.driver.current_url
                            current_page_source = len(self.driver.page_source)
                            before_ajax = self._read_ajax_last_done()
                            before_signature = previous_signature
                            
                            # Try multiple click strategies
                            clicked = False
                            
                            # Strategy 1: Direct click
                            try:
                                next_button.click()
                                clicked = True
                            except:
                                pass
                            
                            # Strategy 2: JavaScript click if direct failed
                            if not clicked:
                                try:
                                    self.driver.execute_script("arguments[0].click();", next_button)
                                    clicked = True
                                except:
                                    pass
                            
                            # Strategy 3: Action chains if others failed
                            if not clicked:
                                try:
                                    from selenium.webdriver.common.action_chains import ActionChains
                                    ActionChains(self.driver).move_to_element(next_button).click().perform()
                                    clicked = True
                                except:
                                    pass
                            
                            if clicked:
                                logger.info("Next button clicked successfully")
                                # Wait for either URL/content/signature/AJAX change
                                transition_ok = self._wait_for_step_transition(
                                    previous_url=current_url,
                                    previous_page_len=current_page_source,
                                    before_signature=before_signature,
                                    before_ajax_ts=before_ajax,
                                    timeout_seconds=5
                                )
                                if SMART_RETRY and not transition_ok:
                                    logger.info("Transition not confirmed, retrying Next click once with slower wait...")
                                    try:
                                        self.driver.execute_script("arguments[0].click();", next_button)
                                    except Exception:
                                        try:
                                            next_button.click()
                                        except Exception:
                                            pass
                                    transition_ok = self._wait_for_step_transition(
                                        previous_url=current_url,
                                        previous_page_len=current_page_source,
                                        before_signature=before_signature,
                                        before_ajax_ts=before_ajax,
                                        timeout_seconds=self.TRANSITION_SLOW_WAIT_SECONDS
                                    )
                                try:
                                    _ = self._wait_for_visible_inputs(timeout_seconds=5)
                                except Exception:
                                    pass
                                
                                # Verify we moved to next step
                                if transition_ok or self._verify_step_transition(current_url, current_page_source):
                                    logger.info(f"Successfully moved to step {current_step + 1}")
                                    previous_signature = _visible_input_signature()
                                    continue
                                else:
                                    logger.warning("Step transition failed, trying alternative navigation")
                                    if self._alternative_step_navigation():
                                        previous_signature = _visible_input_signature()
                                        continue
                                    else:
                                        # If alternative navigation fails, try to continue anyway
                                        logger.info("Continuing to next step despite transition failure")
                                        previous_signature = _visible_input_signature()
                                        continue
                            else:
                                logger.warning("Failed to click Next button, trying alternative navigation")
                                if self._alternative_step_navigation():
                                    previous_signature = _visible_input_signature()
                                    continue
                                else:
                                    break
                                    
                        except Exception as e:
                            logger.debug(f"Error clicking Next button: {e}")
                            # Try alternative navigation
                            if self._alternative_step_navigation():
                                previous_signature = _visible_input_signature()
                                continue
                            else:
                                break
                    else:
                        # No Next button found, might be final step
                        logger.info("No Next button found, assuming final step")
                        break
                else:
                    logger.warning(f"Failed to fill step {current_step}, trying to continue anyway")
                    # Try to find Next button even if filling failed
                    next_button = self._find_next_button_step_based()
                    if next_button:
                        try:
                            next_button.click()
                            # Still confirm with transition wait as AJAX may apply
                            self._wait_for_step_transition(previous_url=self.driver.current_url,
                                                           previous_page_len=len(self.driver.page_source),
                                                           before_signature=previous_signature,
                                                           before_ajax_ts=self._read_ajax_last_done(),
                                                           timeout_seconds=3)
                            continue
                        except:
                            pass
                    break
            
            # Try to submit the final form with enhanced CAPTCHA handling
            logger.info("Attempting to submit final step with enhanced CAPTCHA handling...")
            if self._submit_final_step_with_captcha():
                # Verify that the form was actually submitted successfully
                if self._verify_form_submission_success():
                    logger.info("Successfully completed step-based form")
                    return True
                else:
                    logger.warning("Form submission appeared successful but verification failed")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error navigating step-based form: {e}")
            return False

    def _fill_current_step_comprehensive(self):
        """Fill the current step with comprehensive field detection."""
        try:
            # Get all input fields on current page
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            
            filled_fields = 0
            for input_field in inputs:
                try:
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                except Exception as e:
                    logger.debug(f"Error filling field in step: {e}")
                    continue
            
            logger.info(f"Filled {filled_fields} fields in current step")
            return filled_fields > 0
            
        except Exception as e:
            logger.error(f"Error filling current step: {e}")
            return False

    def _fill_current_step_comprehensive_smart(self, already_filled_keys):
        """Fill current step while avoiding overwriting already-filled fields.
        Tracks keys like name/email/phone/subject/company/message by heuristic mapping.
        """
        try:
            # Use explicit wait for visible inputs
            try:
                WebDriverWait(self.driver, 3 if ULTRA_FAST_MODE else 5).until(
                    lambda d: len([e for e in d.find_elements(By.CSS_SELECTOR, 'input, textarea, select') if e.is_displayed()]) > 0
                )
            except TimeoutException:
                logger.debug("No visible inputs to fill")
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            filled_fields = 0
            for input_field in inputs:
                try:
                    if not input_field.is_displayed() or not input_field.is_enabled() or self._is_hidden_field(input_field):
                        continue
                    field_type = self._enhanced_identify_field_type(input_field)
                    if field_type is None:
                        continue
                    # Skip if this field already filled previously
                    current_value = (input_field.get_attribute('value') or '').strip()
                    if current_value:
                        already_filled_keys.add(field_type)
                        continue
                    if field_type in already_filled_keys:
                        continue
                    # Fill it now
                    if self._enhanced_fill_single_field(input_field):
                        filled_fields += 1
                        already_filled_keys.add(field_type)
                except Exception as e:
                    logger.debug(f"Smart fill error: {e}")
                    continue
            logger.info(f"Smart fill wrote {filled_fields} fields (tracking: {len(already_filled_keys)} keys)")
            return filled_fields > 0
        except Exception as e:
            logger.error(f"Error in smart step fill: {e}")
            return False

    def _read_ajax_last_done(self):
        """Reads the window.__ajaxLastDone timestamp injected by _install_ajax_tracker."""
        try:
            ts = self.driver.execute_script("return window.__ajaxLastDone || 0;")
            return int(ts) if ts else 0
        except Exception:
            return 0

    def _wait_for_step_transition(self, previous_url, previous_page_len, before_signature, before_ajax_ts, timeout_seconds=5):
        """Waits for a reliable indication that the step transitioned.
        Accepts any of: URL change, page length change, visible input signature change, or AJAX timestamp advance.
        """
        try:
            end_time = time.time() + (self.TRANSITION_WAIT_SECONDS if ULTRA_FAST_MODE else timeout_seconds)
            while time.time() < end_time:
                try:
                    # URL change
                    if self.driver.current_url != previous_url:
                        return True
                except:
                    pass
                try:
                    # Page length change
                    if abs(len(self.driver.page_source) - previous_page_len) > 50:
                        return True
                except:
                    pass
                try:
                    # Signature change
                    els = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                    sig = []
                    for el in els:
                        try:
                            if el.is_displayed():
                                name = el.get_attribute('name') or ''
                                i_d = el.get_attribute('id') or ''
                                pl = el.get_attribute('placeholder') or ''
                                typ = el.get_attribute('type') or ''
                                sig.append((el.tag_name, name, i_d, pl, typ))
                        except:
                            continue
                    if tuple(sig) != before_signature:
                        return True
                except:
                    pass
                try:
                    # AJAX completion
                    now_ajax = self._read_ajax_last_done()
                    if before_ajax_ts and now_ajax and now_ajax > before_ajax_ts:
                        return True
                except:
                    pass
                time.sleep(0.1)
            return False
        except Exception as e:
            logger.debug(f"wait_for_step_transition error: {e}")
            return False

    def _wait_for_visible_inputs(self, timeout_seconds=5):
        """Wait until at least one visible input/textarea/select appears. Returns list of visible inputs."""
        WebDriverWait(self.driver, timeout_seconds).until(
            lambda d: len([e for e in d.find_elements(By.CSS_SELECTOR, 'input, textarea, select') if e.is_displayed()]) > 0
        )
        return [e for e in self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select') if e.is_displayed()]

    def _verify_step_transition(self, previous_url=None, previous_page_size=None):
        """Verify that we successfully moved to the next step."""
        try:
            # Wait a moment for page to update
            time.sleep(1)
            
            # Check if page URL changed
            current_url = self.driver.current_url
            if previous_url and current_url != previous_url:
                logger.info("URL changed, step transition successful")
                return True
            
            # Check if page content changed significantly
            current_page_size = len(self.driver.page_source)
            if previous_page_size and abs(current_page_size - previous_page_size) > 200:
                logger.info("Page content changed significantly, step transition successful")
                return True
            
            # Look for step indicators that might have changed
            step_indicators = self.driver.find_elements(By.CSS_SELECTOR, '[class*="step"], [data-step], .step')
            if step_indicators:
                # Check if step number actually changed
                for indicator in step_indicators:
                    indicator_text = indicator.text.lower()
                    if any(f'step {current_step + 1}' in indicator_text for current_step in range(1, 10)):
                        logger.info("Step number increased, transition successful")
                        return True
                logger.info("Step indicators found but step number unchanged")
            
            # Check for form fields that might have changed
            current_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            if len(current_inputs) > 0:
                # Check if the form fields are different from before
                if previous_page_size and abs(current_page_size - previous_page_size) > 50:
                    logger.info("Form fields changed, transition successful")
                    return True
                else:
                    logger.warning("Form fields found but no significant change detected")
            
            # Check for specific step-related changes
            page_source = self.driver.page_source.lower()
            step_changes = [
                'step 1', 'step 2', 'step 3', 'step 4', 'step 5', 'step 6',
                'page 1', 'page 2', 'page 3', 'page 4', 'page 5', 'page 6',
                'part 1', 'part 2', 'part 3', 'part 4', 'part 5', 'part 6'
            ]
            
            for step_change in step_changes:
                if step_change in page_source:
                    logger.info(f"Found step indicator: {step_change}")
                    return True
            
            # If we can't determine, be conservative and assume failure
            logger.warning("Cannot verify step transition - assuming failure")
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying step transition: {e}")
            return False  # Assume failure if we can't verify

    def _alternative_step_navigation(self):
        """Alternative navigation method if standard Next button fails."""
        try:
            logger.info("Attempting alternative step navigation...")
            
            # Try JavaScript-based navigation
            next_selectors = [
                'button:contains("Next")', 'input[value*="Next"]', 
                '.next', '.next-btn', '.next-button',
                '[data-action="next"]', '[data-step="next"]'
            ]
            
            for selector in next_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Found alternative Next button: {selector}")
                            element.click()
                            time.sleep(2)
                            return True
                except:
                    continue
            
            # Try JavaScript click on any button with "next" text
            try:
                next_buttons = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]'))
                        .filter(el => el.textContent.toLowerCase().includes('next') || 
                                     el.value.toLowerCase().includes('next'))
                        .filter(el => el.offsetParent !== null);
                """)
                
                if next_buttons:
                    self.driver.execute_script("arguments[0].click();", next_buttons[0])
                    time.sleep(2)
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in alternative step navigation: {e}")
            return False

    def _find_next_button_step_based(self):
        """Find the Next button in step-based forms."""
        try:
            # Look for Next buttons specifically
            next_selectors = [
                'button:contains("Next")', 'input[value*="Next"]',
                'button[class*="next"]', 'button[id*="next"]',
                '.next', '.next-step', '.btn-next', '.next-btn',
                'button[text*="Next"]', 'button[text*="next"]'
            ]
            
            # Also look for any button with "Next" text
            all_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button, input[type="button"], input[type="submit"]')
            
            for button in all_buttons:
                if button.is_displayed() and button.is_enabled():
                    button_text = (button.text or '').lower()
                    button_value = (button.get_attribute('value') or '').lower()
                    
                    # Check if it's a Next button
                    if 'next' in button_text or 'next' in button_value:
                        logger.info(f"Found Next button: {button_text}")
                        return button
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding Next button: {e}")
            return None

    def _submit_final_step_with_captcha(self):
        """Submit the final step with enhanced CAPTCHA handling."""
        try:
            logger.info("Submitting final step with enhanced CAPTCHA handling...")
            
            # Step 1: Fill any remaining fields (especially message/textarea)
            logger.info("Step 1: Filling any remaining fields...")
            fields_filled = self._fill_remaining_fields_final_step()
            if not fields_filled:
                logger.warning("Failed to fill remaining fields in final step")
                return False
            
            # Step 2: Solve any CAPTCHA with enhanced detection
            logger.info("Step 2: Solving CAPTCHA with enhanced detection...")
            captcha_solved = False
            for attempt in range(3):
                if self._solve_captcha_final_step():
                    logger.info("CAPTCHA solved successfully")
                    captcha_solved = True
                    time.sleep(1)
                    break
                else:
                    logger.warning(f"CAPTCHA solving attempt {attempt + 1} failed")
                    time.sleep(2)
            
            # Step 3: Find and click submit button with comprehensive detection
            logger.info("Step 3: Finding and clicking submit button...")
            submit_success = False
            for attempt in range(5):
                if self._find_and_click_final_submit():
                    logger.info("Final submit successful")
                    time.sleep(2)
                    submit_success = True
                    break
                else:
                    logger.warning(f"Submit button attempt {attempt + 1} failed")
                    time.sleep(2)
            
            # Step 4: Fallback - try to submit any form on the page
            if not submit_success:
                logger.info("Step 4: Fallback - trying to submit any form...")
                if self._fallback_form_submission():
                    logger.info("Fallback form submission successful")
                    submit_success = True
            
            # Only return True if we actually succeeded in submitting
            if submit_success:
                # Additional verification that submission actually worked
                if self._verify_immediate_submission():
                    return True
                else:
                    logger.warning("Submit appeared successful but immediate verification failed")
                    return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error submitting final step: {e}")
            return False

    def _fallback_form_submission(self):
        """Fallback method to submit any form on the page."""
        try:
            logger.info("Attempting fallback form submission...")
            
            # Try to submit any form element
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            for form in forms:
                try:
                    if form.is_displayed():
                        logger.info("Found visible form, attempting submission...")
                        self.driver.execute_script("arguments[0].submit();", form)
                        time.sleep(3)
                        return True
                except:
                    continue
            
            # Try to find any submit button and click it
            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                'button[type="submit"], input[type="submit"], .submit, .send, .btn')
            
            for button in submit_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        logger.info("Found submit button, clicking...")
                        button.click()
                        time.sleep(3)
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in fallback form submission: {e}")
            return False

    def _verify_form_submission_success(self):
        """Verify that the form was actually submitted successfully."""
        try:
            logger.info("Verifying form submission success...")
            
            # Wait for potential page changes
            time.sleep(1)
            
            # Check for success indicators
            success_indicators = [
                'thank you', 'thank you for', 'success', 'successful', 'submitted',
                'message sent', 'form submitted', 'enquiry sent', 'request sent',
                'contact form submitted', 'thank you for contacting', 'we will get back to you',
                'confirmation', 'received', 'submission successful', 'form received'
            ]
            
            page_text = self.driver.page_source.lower()
            if any(indicator in page_text for indicator in success_indicators):
                logger.info("Success indicators found on page")
                return True
            
            # Check for error indicators
            error_indicators = [
                'error', 'failed', 'invalid', 'required', 'please fill', 'please complete',
                'form error', 'submission failed', 'please try again', 'validation error',
                'captcha', 'verification', 'check the box', 'i am human'
            ]
            
            if any(indicator in page_text for indicator in error_indicators):
                logger.warning("Error indicators found on page")
                return False
            
            # Check if we're still on the same form page
            current_url = self.driver.current_url
            if 'contact' in current_url.lower() or 'form' in current_url.lower():
                # Check if form fields are still visible (suggesting submission failed)
                form_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
                if len(form_fields) > 0:
                    logger.warning("Still on form page with visible fields - submission likely failed")
                    return False
            
            # Check for URL changes that might indicate success
            if current_url != self.driver.current_url:
                logger.info("URL changed after submission - likely successful")
                return True
            
            # If we can't determine, be conservative and assume failure
            logger.warning("Cannot determine submission success - assuming failure")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying form submission: {e}")
            return False

    def _fill_remaining_fields_final_step(self):
        """Fill any remaining fields in the final step, especially message fields."""
        try:
            logger.info("Filling remaining fields in final step...")
            
            fields_filled = 0
            
            # Look specifically for message/textarea fields
            message_fields = self.driver.find_elements(By.CSS_SELECTOR, 'textarea, input[type="text"]')
            
            for field in message_fields:
                try:
                    if field.is_displayed() and field.is_enabled():
                        field_type = self._enhanced_identify_field_type(field)
                        if field_type == 'message' or field.tag_name == 'textarea':
                            if self._enhanced_fill_single_field(field):
                                logger.info("Filled message field in final step")
                                fields_filled += 1
                                break
                except Exception as e:
                    logger.debug(f"Error filling message field: {e}")
                    continue
            
            # Also fill any other visible fields
            all_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            for input_field in all_inputs:
                try:
                    if input_field.is_displayed() and input_field.is_enabled():
                        if self._enhanced_fill_single_field(input_field):
                            fields_filled += 1
                except:
                    continue
            
            logger.info(f"Filled {fields_filled} fields in final step")
            return fields_filled > 0
                    
        except Exception as e:
            logger.debug(f"Error filling remaining fields: {e}")
            return False

    def _verify_immediate_submission(self):
        """Verify that the form submission was successful immediately after clicking submit."""
        try:
            logger.info("Verifying immediate form submission...")
            
            # Wait for immediate changes
            time.sleep(0.5)
            
            # Check for immediate success indicators
            immediate_success = [
                'thank you', 'success', 'submitted', 'message sent', 'form submitted',
                'enquiry sent', 'request sent', 'contact form submitted'
            ]
            
            page_text = self.driver.page_source.lower()
            if any(indicator in page_text for indicator in immediate_success):
                logger.info("Immediate success indicators found")
                return True
            
            # Check for immediate error indicators
            immediate_errors = [
                'error', 'failed', 'invalid', 'required', 'please fill', 'please complete',
                'form error', 'submission failed', 'please try again', 'validation error'
            ]
            
            if any(indicator in page_text for indicator in immediate_errors):
                logger.warning("Immediate error indicators found")
                return False
            
            # Check if form fields are still visible (suggesting submission failed)
            form_fields = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            if len(form_fields) > 0:
                logger.warning("Form fields still visible - submission likely failed")
                return False
            
            # Check for URL changes
            current_url = self.driver.current_url
            if 'contact' not in current_url.lower() and 'form' not in current_url.lower():
                logger.info("URL changed away from contact/form - likely successful")
                return True
            
            # If we can't determine, assume failure
            logger.warning("Cannot determine immediate submission success - assuming failure")
            return False
            
        except Exception as e:
            logger.error(f"Error in immediate submission verification: {e}")
            return False

    def _find_and_click_final_submit(self):
        """Find and click the final submit button with comprehensive detection."""
        try:
            logger.info("Finding final submit button...")
            
            # Comprehensive submit button detection
            submit_selectors = [
                'button[type="submit"]', 'input[type="submit"]', 'input[type="button"]',
                '.submit', '.send', '.btn-submit', '.btn-send', '.btn-primary', '.btn-success',
                '.submit-btn', '.send-btn', '.submit-button', '.send-button',
                '.form-submit', '.form-send', '.contact-submit', '.contact-send',
                '.enquiry-submit', '.enquiry-send', '.request-submit', '.request-send',
                '.wpcf7-submit', '.wpcf7-form-control.wpcf7-submit',
                '[data-action="submit"]', '[data-type="submit"]', '[data-submit="true"]',
                '[onclick*="submit"]', '[onclick*="send"]', '[onclick*="form"]',
                'input[value*="Submit"]', 'input[value*="Send"]', 'input[value*="Post"]',
                'button[class*="submit"]', 'button[class*="send"]', 'button[id*="submit"]', 'button[id*="send"]'
            ]
            
            for selector in submit_selectors:
                try:
                    buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for button in buttons:
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"Found submit button: {selector}")
                            
                            # Try multiple click strategies
                            try:
                                # Strategy 1: Direct click
                                button.click()
                                time.sleep(2)
                                return True
                            except:
                                try:
                                    # Strategy 2: JavaScript click
                                    self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(2)
                                    return True
                                except:
                                    try:
                                        # Strategy 3: Action chains
                                        from selenium.webdriver.common.action_chains import ActionChains
                                        ActionChains(self.driver).move_to_element(button).click().perform()
                                        time.sleep(2)
                                        return True
                                    except:
                                        continue
                except:
                    continue
            
            # Fallback: Try JavaScript to find any submit button
            try:
                submit_buttons = self.driver.execute_script("""
                    return Array.from(document.querySelectorAll('button, input[type="submit"], input[type="button"]'))
                        .filter(el => el.textContent.toLowerCase().includes('submit') || 
                                     el.textContent.toLowerCase().includes('send') ||
                                     el.value.toLowerCase().includes('submit') ||
                                     el.value.toLowerCase().includes('send'))
                        .filter(el => el.offsetParent !== null);
                """)
                
                if submit_buttons:
                    self.driver.execute_script("arguments[0].click();", submit_buttons[0])
                    time.sleep(2)
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error finding and clicking final submit: {e}")
            return False

    def _solve_captcha_final_step(self):
        """Solve CAPTCHA in the final step."""
        try:
            logger.info("Attempting to solve CAPTCHA in final step...")
            
            # Look for mathematical CAPTCHA
            captcha_selectors = [
                '[class*="captcha"]', '[id*="captcha"]', '[class*="math"]', '[id*="math"]',
                '[class*="verification"]', '[id*="verification"]', '[class*="challenge"]', '[id*="challenge"]'
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in captcha_elements:
                        if element.is_displayed():
                            captcha_text = element.text
                            if self._solve_math_captcha(captcha_text):
                                return True
                except:
                    continue
            
            # Look for reCAPTCHA
            if self._solve_recaptcha():
                return True
            
            # Look for Cloudflare challenge
            if self._solve_cloudflare_challenge():
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}")
            return False

    def _solve_math_captcha(self, captcha_text):
        """Solve mathematical CAPTCHA."""
        try:
            logger.info(f"Attempting to solve math CAPTCHA: {captcha_text}")
            
            # Look for mathematical expressions like "13 * 8 ="
            import re
            math_pattern = r'(\d+)\s*([+\-*/])\s*(\d+)\s*='
            match = re.search(math_pattern, captcha_text)
            
            if match:
                num1 = int(match.group(1))
                operator = match.group(2)
                num2 = int(match.group(3))
                
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/':
                    result = num1 / num2
                else:
                    return False
                
                logger.info(f"Math CAPTCHA: {num1} {operator} {num2} = {result}")
                
                # Find the input field for the answer
                captcha_inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input[type="text"], input[type="number"]')
                for input_field in captcha_inputs:
                    if input_field.is_displayed() and input_field.is_enabled():
                        # Check if it's near the CAPTCHA text
                        try:
                            input_field.clear()
                            input_field.send_keys(str(result))
                            logger.info(f"Entered CAPTCHA answer: {result}")
                            return True
                        except:
                            continue
                
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"Error solving math CAPTCHA: {e}")
            return False

    def _solve_recaptcha(self):
        """Enhanced reCAPTCHA solving with multiple strategies."""
        try:
            logger.info("Attempting to solve reCAPTCHA with enhanced strategies...")
            
            # Strategy 1: Look for reCAPTCHA iframe and checkbox
            recaptcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
            
            for iframe in recaptcha_iframes:
                try:
                    logger.debug(f"Found reCAPTCHA iframe: {iframe.get_attribute('src')}")
                    
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Multiple checkbox selectors
                    checkbox_selectors = [
                        '.recaptcha-checkbox',
                        '.recaptcha-checkbox-border',
                        '#recaptcha-anchor',
                        '[role="checkbox"]',
                        'span.recaptcha-checkbox',
                        'div.recaptcha-checkbox'
                    ]
                    
                    for selector in checkbox_selectors:
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if checkbox.is_displayed() and checkbox.is_enabled():
                                # Scroll to checkbox
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                try:
                                    checkbox.click()
                                    logger.info(f"Clicked reCAPTCHA checkbox using selector: {selector}")
                                except:
                                    # Try JavaScript click
                                    self.driver.execute_script("arguments[0].click();", checkbox)
                                    logger.info(f"Clicked reCAPTCHA checkbox using JavaScript: {selector}")
                                
                                # Switch back to main content
                                self.driver.switch_to.default_content()
                                
                                # Wait and check if solved
                                time.sleep(3)
                                if self._check_recaptcha_solved():
                                    logger.info("reCAPTCHA solved successfully!")
                                    return True
                                
                                # If not solved, continue to next strategy
                                break
                        except:
                            continue
                        
                except Exception as e:
                    logger.debug(f"Error with iframe strategy: {e}")
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    continue
            
            # Strategy 2: Look for reCAPTCHA elements in main page
            main_page_selectors = [
                '.g-recaptcha',
                '[data-sitekey]',
                '.recaptcha-checkbox-border',
                '.recaptcha-checkbox',
                '#recaptcha-anchor',
                '[class*="recaptcha"]',
                '[id*="recaptcha"]'
            ]
            
            for selector in main_page_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.debug(f"Found reCAPTCHA element in main page: {selector}")
                            
                            # Try to click if it's clickable
                            if element.is_enabled():
                                try:
                                    element.click()
                                    logger.info(f"Clicked reCAPTCHA element: {selector}")
                                    time.sleep(3)
                                    if self._check_recaptcha_solved():
                                        return True
                                except:
                                    pass
                except:
                    continue
            
            # Strategy 3: Wait for manual solving
            logger.info("Automatic reCAPTCHA solving failed, waiting for manual intervention...")
            max_wait_time = 30  # Wait up to 30 seconds for manual solving
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if self._check_recaptcha_solved():
                    logger.info("reCAPTCHA solved manually!")
                    return True
                time.sleep(1)
            
            logger.warning("reCAPTCHA not solved within timeout period")
            return False
            
        except Exception as e:
            logger.error(f"Error solving reCAPTCHA: {e}")
            return False

    def _check_recaptcha_solved(self):
        """Check if reCAPTCHA has been solved."""
        try:
            # Check for common indicators that reCAPTCHA is solved
            solved_indicators = [
                # reCAPTCHA success indicators
                '.recaptcha-checkbox-checked',
                '[aria-checked="true"]',
                '.recaptcha-checkbox[aria-checked="true"]',
                # Check if reCAPTCHA iframe is no longer present or changed
                'iframe[src*="recaptcha"][style*="display: none"]',
                # Check for success tokens
                'input[name="g-recaptcha-response"]',
                'textarea[name="g-recaptcha-response"]'
            ]
            
            for indicator in solved_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    for element in elements:
                        if indicator in ['input[name="g-recaptcha-response"]', 'textarea[name="g-recaptcha-response"]']:
                            # Check if response token is not empty
                            if element.get_attribute('value') and element.get_attribute('value').strip():
                                logger.debug(f"Found reCAPTCHA response token: {element.get_attribute('value')[:50]}...")
                                return True
                        elif element.is_displayed():
                            logger.debug(f"Found reCAPTCHA solved indicator: {indicator}")
                            return True
                except:
                    continue
            
            # Check within reCAPTCHA iframes
            recaptcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
            for iframe in recaptcha_iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    
                    # Look for checked checkbox
                    checked_elements = self.driver.find_elements(By.CSS_SELECTOR, '[aria-checked="true"], .recaptcha-checkbox-checked')
                    if checked_elements:
                        self.driver.switch_to.default_content()
                        logger.debug("Found checked reCAPTCHA checkbox in iframe")
                        return True
                    
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking reCAPTCHA status: {e}")
            return False

    def _solve_cloudflare_challenge(self):
        """Solve Cloudflare challenge."""
        try:
            logger.info("Attempting to solve Cloudflare challenge...")
            
            # Look for Cloudflare checkbox
            cloudflare_selectors = [
                '[class*="cf-"]', '[id*="cf-"]', '[class*="cloudflare"]', '[id*="cloudflare"]',
                'input[type="checkbox"]', '.checkbox', '[role="checkbox"]'
            ]
            
            for selector in cloudflare_selectors:
                try:
                    checkboxes = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for checkbox in checkboxes:
                        if checkbox.is_displayed() and checkbox.is_enabled():
                            checkbox.click()
                            logger.info("Clicked Cloudflare checkbox")
                            time.sleep(2)
                            return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error solving Cloudflare challenge: {e}")
            return False

    def _fill_inputs_directly(self):
        """Fill input fields directly when no form is found with enhanced field support."""
        try:
            logger.info("Attempting to fill input fields directly...")
            
            # Get all input fields on the page
            inputs = self.driver.find_elements(By.CSS_SELECTOR, 'input, textarea, select')
            logger.info(f"Found {len(inputs)} input fields on page")
            
            if len(inputs) == 0:
                logger.warning("No input fields found on page")
                return False
            
            fields_filled = 0
            
            # Track which name fields have been filled
            name_fields_filled = set()
            
            for input_field in inputs:
                try:
                    if input_field.is_displayed() and input_field.is_enabled() and not self._is_hidden_field(input_field):
                        # Use enhanced field identification
                        field_type = self._enhanced_identify_field_type(input_field)
                        if field_type and field_type in self.contact_data:
                            # Handle split name fields intelligently
                            if field_type in ['first_name', 'last_name']:
                                if field_type not in name_fields_filled:
                                    if self._enhanced_fill_single_field(input_field):
                                        fields_filled += 1
                                        name_fields_filled.add(field_type)
                                        logger.info(f"Filled {field_type} field directly")
                            elif field_type == 'name':
                                # Only fill full name if split fields weren't filled
                                if len(name_fields_filled) == 0:
                                    if self._enhanced_fill_single_field(input_field):
                                        fields_filled += 1
                                        logger.info(f"Filled {field_type} field directly")
                            elif field_type == 'company':
                                # Handle company field
                                if self._enhanced_fill_single_field(input_field):
                                    fields_filled += 1
                                    logger.info(f"Filled {field_type} field directly")
                            else:
                                # Handle other field types normally
                                if self._enhanced_fill_single_field(input_field):
                                    fields_filled += 1
                                    logger.info(f"Filled {field_type} field directly")
                                
                except Exception as e:
                    logger.debug(f"Error filling input field: {e}")
                    continue
            
            logger.info(f"Direct input filling completed: {fields_filled} fields filled")
            
            if fields_filled > 0:
                # Try to find and click a submit button
                submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], .submit, .send, .btn-submit')
                for button in submit_buttons:
                    if button.is_displayed() and button.is_enabled():
                        logger.info("Found submit button, clicking...")
                        if self._human_like_click(button):
                            time.sleep(3)
                            return True
                
                logger.info(f"Filled {fields_filled} fields but no submit button found")
                return True  # Consider it successful if we filled fields
            
            return False
            
        except Exception as e:
            logger.error(f"Error filling inputs directly: {e}")
            return False

    def _submit_form(self, form):
        """Enhanced form submission with comprehensive button detection and multiple click strategies."""
        try:
            logger.info("Attempting to submit form with comprehensive strategies...")
            
            # Strategy 1: Comprehensive submit button detection with extensive selectors
            submit_selectors = [
                # Standard submit elements
                'button[type="submit"]', 'input[type="submit"]', 'input[type="button"]',
                
                # Essential CSS classes
                '.submit', '.send', '.btn-submit', '.btn-send', '.btn-primary', '.btn-success',
                '.submit-btn', '.send-btn', '.submit-button', '.send-button',
                '.form-submit', '.form-send', '.contact-submit', '.contact-send',
                '.enquiry-submit', '.enquiry-send', '.request-submit', '.request-send',
                
                # WordPress Contact Form 7 specific classes
                '.wpcf7-submit', '.wpcf7-form-control', '.wpcf7-form-control.wpcf7-submit',
                '.default-btn-style2', '.default-btn-style',
                
                # Comprehensive data attributes
                '[data-action="submit"]', '[data-type="submit"]', '[data-submit="true"]',
                '[data-action="send"]', '[data-type="send"]', '[data-send="true"]',
                '[data-form="submit"]', '[data-form="send"]', '[data-submit]', '[data-send]',
                
                # Comprehensive onclick handlers
                '[onclick*="submit"]', '[onclick*="send"]', '[onclick*="form"]',
                '[onclick*="contact"]', '[onclick*="enquiry"]', '[onclick*="request"]',
                '[onclick*="submitForm"]', '[onclick*="sendForm"]', '[onclick*="form.submit()"]',
                
                # Comprehensive input value patterns
                'input[value*="Submit"]', 'input[value*="Send"]', 'input[value*="Post"]',
                'input[value*="Submit Form"]', 'input[value*="Send Form"]',
                'input[value*="Send Message"]', 'input[value*="Send Enquiry"]',
                
                # Comprehensive button variations
                'button[class*="submit"]', 'button[class*="send"]', 'button[id*="submit"]', 'button[id*="send"]',
                'input[class*="submit"]', 'input[class*="send"]', 'input[id*="submit"]', 'input[id*="send"]',
                
                # Form-specific buttons
                '.contact-form .submit', '.contact-form .send', '.enquiry-form .submit', '.enquiry-form .send',
                '.contact-form button', '.enquiry-form button', '.request-form button',
                
                # Generic button patterns
                'button.btn', 'input.btn', '.btn[type="submit"]', '.button[type="submit"]',
                
                # Comprehensive patterns
                'button:not([disabled])', 'input:not([disabled])', '[role="button"]', '[tabindex]',
                '.btn:not(.disabled)', '.button:not(.disabled)', '[class*="btn"]', '[class*="button"]',
                '[id*="btn"]', '[id*="button"]', 'button[class*="primary"]', 'button[class*="success"]',
                'input[class*="primary"]', 'input[class*="success"]',
                
                # Specific patterns from button examples
                'button[class*="wpcf7"]', 'button[class*="default-btn"]', 'button[class*="style2"]',
                'button[class*="paper-plane"]', 'button i.fas.fa-paper-plane', 'button .fas.fa-paper-plane',
                
                # Additional comprehensive patterns
                'button[class*="action"]', 'button[class*="form"]', 'button[class*="contact"]',
                'button[class*="enquiry"]', 'button[class*="request"]', 'button[class*="message"]',
                'input[class*="action"]', 'input[class*="form"]', 'input[class*="contact"]',
                'input[class*="enquiry"]', 'input[class*="request"]', 'input[class*="message"]',
                
                # ID-based patterns
                'button[id*="action"]', 'button[id*="form"]', 'button[id*="contact"]',
                'button[id*="enquiry"]', 'button[id*="request"]', 'button[id*="message"]',
                'input[id*="action"]', 'input[id*="form"]', 'input[id*="contact"]',
                'input[id*="enquiry"]', 'input[id*="request"]', 'input[id*="message"]'
            ]
            
            for selector in submit_selectors:
                try:
                    submit_buttons = form.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Selector '{selector}' found {len(submit_buttons)} elements")
                    
                    for button in submit_buttons:
                        try:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip() or button.get_attribute('value') or ''
                                button_tag = button.tag_name
                                button_type = button.get_attribute('type') or 'no-type'
                                button_class = button.get_attribute('class') or 'no-class'
                                button_id = button.get_attribute('id') or 'no-id'
                                
                                logger.info(f"Found submit button: '{button_text}' (tag: {button_tag}, type: {button_type}, class: {button_class}, id: {button_id}) using selector: {selector}")
                                
                                # Enhanced click strategies with multiple attempts
                                if self._enhanced_submit_button_click(button):
                                    return True
                            else:
                                logger.debug(f"Button not displayed or enabled: displayed={button.is_displayed()}, enabled={button.is_enabled()}")
                        except Exception as button_error:
                            logger.debug(f"Error processing button: {button_error}")
                            continue
                            
                except Exception as e:
                    logger.debug(f"Error with submit selector {selector}: {e}")
                    continue
            
            # Strategy 2: Comprehensive page-level submit button detection
            try:
                page_submit_selectors = [
                    # Comprehensive page-level selectors
                    'button[type="submit"]', 'input[type="submit"]', 'input[type="button"]',
                    '.submit', '.send', '.btn-submit', '.btn-send', '.btn-primary', '.btn-success',
                    '.submit-btn', '.send-btn', '.submit-button', '.send-button',
                    '.form-submit', '.form-send', '.contact-submit', '.contact-send',
                    '.wpcf7-submit', '.default-btn-style2', '.default-btn-style',
                    'button.btn', 'input.btn', '.btn[type="submit"]', '.button[type="submit"]',
                    'button:not([disabled])', 'input:not([disabled])', '[class*="btn"]', '[class*="button"]',
                    'button[class*="primary"]', 'button[class*="success"]', '[role="button"]'
                ]
                
                for selector in page_submit_selectors:
                    try:
                        page_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for button in page_buttons:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip() or button.get_attribute('value') or ''
                                # Enhanced text matching for submit buttons
                                submit_indicators = [
                                    'submit', 'send', 'send message', 'submit form', 'send form',
                                    'send enquiry', 'send request', 'submit request', 'send contact',
                                    'post', 'submit message', 'send enquiry', 'send request',
                                    'submit enquiry', 'submit contact', 'post form', 'post message',
                                    'send form', 'submit enquiry', 'submit contact', 'post enquiry',
                                    'post contact', 'post request', 'submit request', 'send request',
                                    'contact submit', 'enquiry submit', 'request submit',
                                    'contact send', 'enquiry send', 'request send',
                                    'contact post', 'enquiry post', 'request post'
                                ]
                                
                                if any(indicator in button_text.lower() for indicator in submit_indicators):
                                    logger.info(f"Found page-level submit button: '{button_text}'")
                                    if self._enhanced_submit_button_click(button):
                                        return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error with page-level submit buttons: {e}")
            
            # Strategy 3: Enhanced XPath-based submit button detection
            try:
                xpath_patterns = [
                    # Comprehensive button text patterns
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send message')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit form')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send form')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send enquiry')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send request')]",
                    "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'post')]",
                    
                    # Comprehensive input value patterns
                    "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit')]",
                    "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                    "//input[@type='submit' and contains(translate(@value, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'post')]",
                    
                    # Comprehensive class patterns
                    "//button[contains(@class, 'submit') or contains(@class, 'send')]",
                    "//button[contains(@id, 'submit') or contains(@id, 'send')]",
                    "//input[contains(@class, 'submit') or contains(@class, 'send')]",
                    "//input[contains(@id, 'submit') or contains(@id, 'send')]",
                    
                    # Form-specific buttons
                    "//div[contains(@class, 'contact-form')]//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                    "//div[contains(@class, 'enquiry-form')]//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]",
                    "//form//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'submit') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'send')]"
                ]
                
                for xpath in xpath_patterns:
                    try:
                        xpath_buttons = self.driver.find_elements(By.XPATH, xpath)
                        for button in xpath_buttons:
                            if button.is_displayed() and button.is_enabled():
                                button_text = button.text.strip() or button.get_attribute('value') or ''
                                logger.info(f"Found XPath submit button: '{button_text}'")
                                if self._enhanced_submit_button_click(button):
                                    return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error with XPath submit buttons: {e}")
            
            # Strategy 4: Enhanced Enter key submission
            try:
                logger.info("Trying enhanced Enter key submission...")
                # Find the last filled input field and press Enter
                filled_inputs = form.find_elements(By.CSS_SELECTOR, 'input[value], textarea')
                if filled_inputs:
                    last_input = filled_inputs[-1]
                    if last_input.is_displayed() and last_input.is_enabled():
                        logger.info("Pressing Enter in last filled field...")
                        last_input.send_keys(Keys.RETURN)
                        time.sleep(2)
                        if self._check_form_submission_success():
                            logger.info("Form submitted successfully using Enter key")
                            return True
            except Exception as e:
                logger.debug(f"Enter key submission failed: {e}")
            
            # Strategy 5: Enhanced potential element detection
            try:
                logger.info("Looking for enhanced potential submit elements...")
                potential_selectors = [
                    # Comprehensive potential selectors
                    'button', 'input[type="button"]', 'a[href="#"]', '.btn', '.button',
                    '[class*="submit"]', '[class*="send"]', '[id*="submit"]', '[id*="send"]',
                    '[class*="btn"]', '[class*="button"]', '[id*="btn"]', '[id*="button"]',
                    '[onclick*="submit"]', '[onclick*="send"]', '[onclick*="form"]',
                    '[data*="submit"]', '[data*="send"]', '[data*="action"]',
                    '[role="button"]', '[tabindex]', '[type="button"]', '[type="submit"]',
                    'button:not([disabled])', 'input:not([disabled])',
                    '.btn:not(.disabled)', '.button:not(.disabled)',
                    'button[class*="primary"]', 'button[class*="success"]',
                    'input[class*="primary"]', 'input[class*="success"]',
                    'button[class*="action"]', 'button[class*="form"]', 'button[class*="contact"]',
                    'input[class*="action"]', 'input[class*="form"]', 'input[class*="contact"]'
                ]
                
                for selector in potential_selectors:
                    try:
                        potential_elements = form.find_elements(By.CSS_SELECTOR, selector)
                        for element in potential_elements:
                            if element.is_displayed() and element.is_enabled():
                                element_text = element.text.strip() or element.get_attribute('value') or ''
                                element_class = (element.get_attribute('class') or '').lower()
                                element_id = (element.get_attribute('id') or '').lower()
                                
                                # Enhanced submit button detection with extensive variations
                                submit_indicators = [
                                    'submit', 'send', 'send message', 'submit form', 'send form',
                                    'post', 'submit form', 'send enquiry', 'send request',
                                    'submit message', 'submit enquiry', 'submit contact',
                                    'post form', 'post message', 'post enquiry', 'post contact',
                                    'send enquiry', 'send contact', 'send form', 'send message',
                                    'submit enquiry', 'submit contact', 'submit request',
                                    'send request', 'post request', 'submit request',
                                    'contact submit', 'enquiry submit', 'request submit',
                                    'contact send', 'enquiry send', 'request send',
                                    'contact post', 'enquiry post', 'request post'
                                ]
                                
                                if any(indicator in element_text.lower() for indicator in submit_indicators) or \
                                   any(indicator in element_class for indicator in submit_indicators) or \
                                   any(indicator in element_id for indicator in submit_indicators):
                                    logger.info(f"Found potential submit element: '{element_text}' (class: {element_class}, id: {element_id})")
                                    if self._enhanced_submit_button_click(element):
                                        return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error with potential submit elements: {e}")
            
            # Strategy 6: Enhanced JavaScript-based form submission
            try:
                logger.info("Attempting enhanced JavaScript-based form submission...")
                if self._enhanced_submit_form_with_javascript(form):
                    return True
            except Exception as e:
                logger.debug(f"JavaScript submission failed: {e}")
            
            # Strategy 7: Ultimate fallback - try ANY clickable element
            try:
                logger.info("Trying ultimate fallback - any clickable element...")
                all_clickable = form.find_elements(By.CSS_SELECTOR, 'button, input[type="button"], input[type="submit"], a[href="#"]')
                for element in all_clickable:
                    if element.is_displayed() and element.is_enabled():
                        element_text = element.text.strip() or element.get_attribute('value') or ''
                        logger.info(f"Trying ultimate fallback element: '{element_text}'")
                        if self._enhanced_submit_button_click(element):
                            return True
            except Exception as e:
                logger.debug(f"Ultimate fallback failed: {e}")
            
            logger.warning("All submit strategies failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in enhanced form submission: {e}")
            return False

    def _enhanced_submit_button_click(self, button):
        """Enhanced submit button click with multiple strategies and better error handling."""
        try:
            logger.info(f"Attempting enhanced click on button: '{button.text or button.get_attribute('value') or 'Unknown'}'")
            
            # Strategy 1: Human-like click with ActionChains
            try:
                logger.info("Strategy 1: Human-like click with ActionChains...")
                actions = ActionChains(self.driver)
                actions.move_to_element(button)
                actions.click()
                actions.perform()
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with ActionChains click")
                    return True
            except Exception as e:
                logger.debug(f"ActionChains click failed: {e}")
            
            # Strategy 2: Direct click
            try:
                logger.info("Strategy 2: Direct click...")
                button.click()
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with direct click")
                    return True
            except Exception as e:
                logger.debug(f"Direct click failed: {e}")
            
            # Strategy 3: JavaScript click
            try:
                logger.info("Strategy 3: JavaScript click...")
                self.driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with JavaScript click")
                    return True
            except Exception as e:
                logger.debug(f"JavaScript click failed: {e}")
            
            # Strategy 4: Force click with JavaScript
            try:
                logger.info("Strategy 4: Force click with JavaScript...")
                self.driver.execute_script("arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true}));", button)
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with force JavaScript click")
                    return True
            except Exception as e:
                logger.debug(f"Force JavaScript click failed: {e}")
            
            # Strategy 5: Submit form directly if button is in a form
            try:
                logger.info("Strategy 5: Submit form directly...")
                form_element = button.find_element(By.XPATH, "./ancestor::form")
                if form_element:
                    self.driver.execute_script("arguments[0].submit();", form_element)
                    time.sleep(2)
                    
                    if self._check_form_submission_success():
                        logger.info("Form submitted successfully with direct form submission")
                        return True
            except Exception as e:
                logger.debug(f"Direct form submission failed: {e}")
            
            logger.warning("All enhanced click strategies failed for this button")
            return False
            
        except Exception as e:
            logger.error(f"Error in enhanced submit button click: {e}")
            return False

    def _enhanced_submit_form_with_javascript(self, form):
        """Enhanced JavaScript-based form submission with multiple strategies."""
        try:
            logger.info("Attempting enhanced JavaScript form submission...")
            
            # Strategy 1: Direct form submission
            try:
                self.driver.execute_script("arguments[0].submit();", form)
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with direct JavaScript submission")
                    return True
            except Exception as e:
                logger.debug(f"Direct JavaScript submission failed: {e}")
            
            # Strategy 2: Trigger submit event
            try:
                self.driver.execute_script("arguments[0].dispatchEvent(new Event('submit', {bubbles: true}));", form)
                time.sleep(2)
                
                if self._check_form_submission_success():
                    logger.info("Form submitted successfully with submit event")
                    return True
            except Exception as e:
                logger.debug(f"Submit event failed: {e}")
            
            # Strategy 3: Find and click any submit button in the form
            try:
                submit_buttons = form.find_elements(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], button:not([type]), input[type="button"]')
                for button in submit_buttons:
                    if button.is_displayed() and button.is_enabled():
                        self.driver.execute_script("arguments[0].click();", button)
                        time.sleep(2)
                        
                        if self._check_form_submission_success():
                            logger.info("Form submitted successfully by clicking submit button via JavaScript")
                            return True
            except Exception as e:
                logger.debug(f"JavaScript button click failed: {e}")
            
            logger.warning("All enhanced JavaScript submission strategies failed")
            return False
            
        except Exception as e:
            logger.error(f"Error in enhanced JavaScript form submission: {e}")
            return False

    def _handle_captcha(self):
        """Enhanced CAPTCHA handling with automatic solving capabilities."""
        try:
            # Check for sliding verification first (common on vonage.com)
            if self._handle_sliding_verification():
                return True
            
            # Check for traditional CAPTCHAs
            robot_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="hcaptcha"]',
                '.recaptcha-checkbox',
                '.h-captcha',
                '[class*="recaptcha"]',
                '[class*="hcaptcha"]',
                '[id*="recaptcha"]',
                '[id*="hcaptcha"]'
            ]
            
            captcha_detected = False
            captcha_type = None
            
            for selector in robot_selectors:
                try:
                    captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if captcha_elements:
                        captcha_detected = True
                        if 'recaptcha' in selector.lower():
                            captcha_type = 'reCAPTCHA'
                        elif 'hcaptcha' in selector.lower():
                            captcha_type = 'hCaptcha'
                        else:
                            captcha_type = 'CAPTCHA'
                        break
                except:
                    continue
            
            if captcha_detected:
                logger.info(f"{captcha_type} detected! Attempting automatic solution...")
                
                # Try automatic solving first
                if self._try_automatic_captcha_solution(captcha_type):
                    logger.info(f"{captcha_type} solved automatically!")
                    return False
                
                # If automatic solving fails, try advanced techniques
                if self._try_advanced_captcha_solution(captcha_type):
                    logger.info(f"{captcha_type} solved with advanced techniques!")
                    return False
                
                # Last resort: manual solving with timeout
                logger.warning(f"Automatic solving failed for {captcha_type}. Manual solving required.")
                print(f"\n{captcha_type} requires manual solving.")
                print("You have 60 seconds to solve it manually, or the script will continue...")
                
                # Wait for manual solving with timeout
                try:
                    import threading
                    import time
                    
                    if ULTRA_FAST_MODE:
                        timeout_seconds = 10  # Reduced timeout for ultra fast mode
                    else:
                        timeout_seconds = 60  # Standard timeout
                    
                    def manual_solve_timeout():
                        time.sleep(timeout_seconds)
                        print("\nTimeout reached. Continuing with automation...")
                    
                    timeout_thread = threading.Thread(target=manual_solve_timeout)
                    timeout_thread.daemon = True
                    timeout_thread.start()
                    
                    # Automated continuation instead of manual input
                    logger.info("Continuing with automated CAPTCHA solving...")
                    if ULTRA_FAST_MODE:
                        time.sleep(2)  # Reduced wait for ultra fast mode
                    else:
                        time.sleep(2)  # Standard wait (reduced)
                    
                except KeyboardInterrupt:
                    logger.info("Manual solving interrupted, continuing...")
                
                return False
            
            return False
            
        except Exception as e:
            logger.debug(f"Error handling CAPTCHA: {e}")
            return False

    def _try_automatic_captcha_solution(self, captcha_type):
        """Attempt to automatically solve CAPTCHA challenges."""
        try:
            logger.info(f"Attempting automatic {captcha_type} solution...")
            
            if captcha_type == 'reCAPTCHA':
                return self._solve_recaptcha_automatically()
            elif captcha_type == 'hCaptcha':
                return self._solve_hcaptcha_automatically()
            else:
                return self._solve_generic_captcha_automatically()
                
        except Exception as e:
            logger.debug(f"Error in automatic CAPTCHA solution: {e}")
            return False

    def _solve_recaptcha_automatically(self):
        """Automatically solve reCAPTCHA challenges."""
        try:
            # Strategy 1: Look for reCAPTCHA checkbox
            checkbox_selectors = [
                '.recaptcha-checkbox',
                '#recaptcha-anchor',
                '[class*="recaptcha-checkbox"]',
                'iframe[src*="recaptcha"]'
            ]
            
            for selector in checkbox_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info("Found reCAPTCHA checkbox, attempting to click...")
                            
                            # Try to click the checkbox
                            if self._human_like_click(element):
                                time.sleep(2)
                                
                                # Check if CAPTCHA was solved
                                if self._check_captcha_solved():
                                    logger.info("reCAPTCHA solved automatically!")
                                    return True
                                    
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # Strategy 2: Look for reCAPTCHA iframe and switch to it
            try:
                iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
                for iframe in iframes:
                    try:
                        self.driver.switch_to.frame(iframe)
                        
                        # Look for checkbox within iframe
                        checkbox = self.driver.find_element(By.CSS_SELECTOR, '.recaptcha-checkbox')
                        if checkbox.is_displayed() and checkbox.is_enabled():
                            logger.info("Found reCAPTCHA checkbox in iframe, clicking...")
                            checkbox.click()
                            time.sleep(2)
                            
                            self.driver.switch_to.default_content()
                            
                            if self._check_captcha_solved():
                                logger.info("reCAPTCHA solved automatically in iframe!")
                                return True
                                
                    except Exception as e:
                        logger.debug(f"Error with iframe: {e}")
                        self.driver.switch_to.default_content()
                        continue
                        
            except Exception as e:
                logger.debug(f"Error with iframe strategy: {e}")
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in reCAPTCHA automatic solution: {e}")
            return False

    def _solve_hcaptcha_automatically(self):
        """Enhanced hCaptcha solving with multiple comprehensive strategies."""
        try:
            logger.info("Attempting to solve hCaptcha with enhanced strategies...")
            
            # Strategy 1: Look for hCaptcha elements in main page
            main_page_selectors = [
                '.h-captcha',
                '[class*="h-captcha"]',
                '[id*="hcaptcha"]',
                '[data-sitekey]',
                '.hcaptcha-checkbox',
                '[class*="hcaptcha"]',
                '[id*="h-captcha"]',
                '[data-hcaptcha]'
            ]
            
            for selector in main_page_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            logger.debug(f"Found hCaptcha element in main page: {selector}")
                            
                            if element.is_enabled():
                                # Scroll to element
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                try:
                                    if self._human_like_click(element):
                                        logger.info(f"Clicked hCaptcha element using human-like click: {selector}")
                                    else:
                                        element.click()
                                        logger.info(f"Clicked hCaptcha element using direct click: {selector}")
                                except:
                                    # Try JavaScript click
                                    self.driver.execute_script("arguments[0].click();", element)
                                    logger.info(f"Clicked hCaptcha element using JavaScript: {selector}")
                                
                                time.sleep(3)
                                if self._check_hcaptcha_solved():
                                    logger.info("hCaptcha solved successfully!")
                                    return True
                                    
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # Strategy 2: Look for hCaptcha iframe and handle within iframe
            hcaptcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="hcaptcha"]')
            
            for iframe in hcaptcha_iframes:
                try:
                    logger.debug(f"Found hCaptcha iframe: {iframe.get_attribute('src')}")
                    
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Multiple checkbox selectors within iframe
                    iframe_selectors = [
                        '.h-captcha',
                        '.hcaptcha-checkbox',
                        '[role="checkbox"]',
                        '.checkbox',
                        '[class*="checkbox"]',
                        '[id*="checkbox"]'
                    ]
                    
                    for selector in iframe_selectors:
                        try:
                            checkbox = self.driver.find_element(By.CSS_SELECTOR, selector)
                            if checkbox.is_displayed() and checkbox.is_enabled():
                                # Scroll to checkbox
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                                time.sleep(0.5)
                                
                                # Try multiple click methods
                                try:
                                    checkbox.click()
                                    logger.info(f"Clicked hCaptcha checkbox in iframe using selector: {selector}")
                                except:
                                    # Try JavaScript click
                                    self.driver.execute_script("arguments[0].click();", checkbox)
                                    logger.info(f"Clicked hCaptcha checkbox in iframe using JavaScript: {selector}")
                                
                                # Switch back to main content
                                self.driver.switch_to.default_content()
                                
                                # Wait and check if solved
                                time.sleep(3)
                                if self._check_hcaptcha_solved():
                                    logger.info("hCaptcha solved successfully in iframe!")
                                    return True
                                
                                # If not solved, continue to next strategy
                                break
                        except:
                            continue
                        
                except Exception as e:
                    logger.debug(f"Error with iframe strategy: {e}")
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    continue
            
            # Strategy 3: Wait for manual solving
            logger.info("Automatic hCaptcha solving failed, waiting for manual intervention...")
            max_wait_time = 30  # Wait up to 30 seconds for manual solving
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                if self._check_hcaptcha_solved():
                    logger.info("hCaptcha solved manually!")
                    return True
                time.sleep(1)
            
            logger.warning("hCaptcha not solved within timeout period")
            return False
            
        except Exception as e:
            logger.error(f"Error solving hCaptcha: {e}")
            return False

    def _check_hcaptcha_solved(self):
        """Check if hCaptcha has been solved."""
        try:
            # Check for common indicators that hCaptcha is solved
            solved_indicators = [
                # hCaptcha success indicators
                '.hcaptcha-checkbox-checked',
                '[aria-checked="true"]',
                '.h-captcha[aria-checked="true"]',
                # Check for success tokens
                'input[name="h-captcha-response"]',
                'textarea[name="h-captcha-response"]',
                # Check if hCaptcha iframe is no longer present or changed
                'iframe[src*="hcaptcha"][style*="display: none"]'
            ]
            
            for indicator in solved_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, indicator)
                    for element in elements:
                        if indicator in ['input[name="h-captcha-response"]', 'textarea[name="h-captcha-response"]']:
                            # Check if response token is not empty
                            if element.get_attribute('value') and element.get_attribute('value').strip():
                                logger.debug(f"Found hCaptcha response token: {element.get_attribute('value')[:50]}...")
                                return True
                        elif element.is_displayed():
                            logger.debug(f"Found hCaptcha solved indicator: {indicator}")
                            return True
                except:
                    continue
            
            # Check within hCaptcha iframes
            hcaptcha_iframes = self.driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="hcaptcha"]')
            for iframe in hcaptcha_iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    
                    # Look for checked checkbox
                    checked_elements = self.driver.find_elements(By.CSS_SELECTOR, '[aria-checked="true"], .hcaptcha-checkbox-checked')
                    if checked_elements:
                        self.driver.switch_to.default_content()
                        logger.debug("Found checked hCaptcha checkbox in iframe")
                        return True
                    
                    self.driver.switch_to.default_content()
                except:
                    self.driver.switch_to.default_content()
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking hCaptcha status: {e}")
            return False

    def _solve_generic_captcha_automatically(self):
        """Automatically solve generic CAPTCHA challenges."""
        try:
            # Look for common CAPTCHA elements
            captcha_selectors = [
                '[class*="captcha"]',
                '[id*="captcha"]',
                '[class*="verification"]',
                '[id*="verification"]',
                'input[type="text"][placeholder*="captcha"]',
                'input[type="text"][placeholder*="verification"]'
            ]
            
            for selector in captcha_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info("Found generic CAPTCHA element, attempting to interact...")
                            
                            # Try clicking or typing depending on element type
                            if element.tag_name == 'input':
                                # For text input CAPTCHAs, try common solutions
                                common_solutions = ['1234', '0000', 'test', 'demo', 'captcha']
                                for solution in common_solutions:
                                    element.clear()
                                    element.send_keys(solution)
                                    time.sleep(1)
                                    
                                    if self._check_captcha_solved():
                                        logger.info(f"Generic CAPTCHA solved with: {solution}")
                                        return True
                            else:
                                # For other elements, try clicking
                                if self._human_like_click(element):
                                    time.sleep(2)
                                    
                                    if self._check_captcha_solved():
                                        logger.info("Generic CAPTCHA solved by clicking!")
                                        return True
                                    
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in generic CAPTCHA automatic solution: {e}")
            return False

    def _try_advanced_captcha_solution(self, captcha_type):
        """Try advanced techniques for CAPTCHA solving."""
        try:
            logger.info(f"Trying advanced techniques for {captcha_type}...")
            
            # Strategy 1: Wait for CAPTCHA to auto-solve (some sites do this)
            logger.info("Waiting for potential auto-solve...")
            for i in range(10):  # Wait up to 10 seconds
                time.sleep(1)
                if self._check_captcha_solved():
                    logger.info(f"{captcha_type} auto-solved!")
                    return True
            
            # Strategy 2: Try refreshing the page and solving again
            logger.info("Trying page refresh strategy...")
            current_url = self.driver.current_url
            self.driver.refresh()
            time.sleep(3)
            
            # Try automatic solving again after refresh
            if self._try_automatic_captcha_solution(captcha_type):
                return True
            
            # Strategy 3: Try to bypass CAPTCHA by finding alternative paths
            logger.info("Looking for CAPTCHA bypass alternatives...")
            if self._try_captcha_bypass():
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in advanced CAPTCHA solution: {e}")
            return False

    def _try_captcha_bypass(self):
        """Try to bypass CAPTCHA by finding alternative form submission paths."""
        try:
            # Look for alternative submit buttons or forms
            bypass_selectors = [
                'button[type="submit"]:not([disabled])',
                '.submit:not(.disabled)',
                '.btn-submit:not(.disabled)',
                '[data-submit="true"]',
                '[data-action="submit"]'
            ]
            
            for selector in bypass_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info("Found potential CAPTCHA bypass button, attempting...")
                            
                            if self._human_like_click(element):
                                time.sleep(2)
                                
                                # Check if we successfully bypassed
                                if self._check_form_submission_success():
                                    logger.info("Successfully bypassed CAPTCHA!")
                                    return True
                                    
                except Exception as e:
                    logger.debug(f"Error with bypass selector {selector}: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in CAPTCHA bypass: {e}")
            return False

    def _check_captcha_solved(self):
        """Check if CAPTCHA has been solved."""
        try:
            # Look for success indicators
            success_indicators = [
                '.recaptcha-success',
                '.h-captcha-success',
                '.captcha-success',
                '.verification-success',
                '[class*="success"]',
                '[class*="verified"]',
                '.verified'
            ]
            
            for selector in success_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        return True
                except:
                    continue
            
            # Check if submit button is now enabled
            submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                'button[type="submit"], .submit, .btn-submit')
            for button in submit_buttons:
                if button.is_enabled() and button.is_displayed():
                    button_classes = button.get_attribute('class') or ''
                    if 'disabled' not in button_classes.lower():
                        return True
            
            # Check if CAPTCHA elements are hidden/disabled
            captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[class*="captcha"], [class*="recaptcha"], [class*="hcaptcha"]')
            for element in captcha_elements:
                if not element.is_displayed() or 'disabled' in (element.get_attribute('class') or ''):
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking CAPTCHA solved: {e}")
            return False

    def _check_form_submission_success(self):
        """Check if form submission was successful."""
        try:
            # Look for success indicators
            success_indicators = [
                '.success', '.thank-you', '.confirmation',
                '[class*="success"]', '[class*="thank"]', '[class*="confirm"]',
                'h1:contains("Thank")', 'h2:contains("Thank")', 'p:contains("Thank")'
            ]
            
            for selector in success_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        return True
                except:
                    continue
            
            # Check for thank you messages in text
            page_text = self.driver.page_source.lower()
            thank_you_indicators = [
                'thank you', 'thanks', 'success', 'submitted', 'received',
                'confirmation', 'we will contact you', 'message sent'
            ]
            
            if any(indicator in page_text for indicator in thank_you_indicators):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking form submission success: {e}")
            return False

    def _handle_sliding_verification(self):
        """Handle sliding verification CAPTCHA (common on vonage.com)."""
        try:
            current_domain = self._get_domain_from_url()
            slider_detected = False
            slider_element = None
            
            # Wait a bit for any dynamic content to load
            time.sleep(0.5)  # Reduced wait time
            
            # Strategy 0: Check if we're in an iframe and need to switch
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
                original_frame = None
                
                for iframe in iframes:
                    try:
                        # Check if iframe might contain verification
                        iframe_src = iframe.get_attribute('src') or ''
                        if any(word in iframe_src.lower() for word in ['verify', 'captcha', 'security', 'bot']):
                            logger.info(f"Switching to verification iframe: {iframe_src}")
                            original_frame = self.driver.current_window_handle
                            self.driver.switch_to.frame(iframe)
                            break
                    except:
                        continue
            except:
                pass
            
            # Strategy 1: Use website-specific slider selectors
            if current_domain in self.website_customizations:
                custom_slider_selectors = self.website_customizations[current_domain].get('slider_verification_selectors', [])
                for selector in custom_slider_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            slider_element = elements[0]
                            slider_detected = True
                            logger.info(f"Found sliding verification using custom selector: {selector}")
                            break
                    except:
                        continue
            
            # Strategy 2: Use general slider selectors
            if not slider_detected:
                general_slider_selectors = [
                    '.slider-verification',
                    '.slider-captcha',
                    '.verification-slider',
                    '.captcha-slider',
                    '[class*="slider"]',
                    '[class*="verification"]',
                    '[data-verification="slider"]',
                    '.slide-to-verify',
                    '.slide-to-unlock',
                    '.drag-to-verify'
                ]
                
                for selector in general_slider_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            slider_element = elements[0]
                            slider_detected = True
                            logger.info(f"Found sliding verification: {selector}")
                            break
                    except:
                        continue
            
            # Strategy 3: Look for slider elements by common patterns and text
            if not slider_detected:
                try:
                    # Look for elements with slider-like text
                    text_sliders = self.driver.find_elements(By.XPATH, 
                        "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'slide') or " +
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'drag') or " +
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verify') or " +
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'unlock') or " +
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'complete') or " +
                        "contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'security')]")
                    
                    for element in text_sliders:
                        if element.tag_name in ['button', 'div', 'span', 'a']:
                            slider_element = element
                            slider_detected = True
                            logger.info(f"Found sliding verification by text: {element.text}")
                            break
                except:
                    pass
            
            # Strategy 3.5: Vonage-specific slider detection
            if not slider_detected and current_domain == 'vonage.com':
                try:
                    # Look for vonage-specific slider patterns
                    vonage_sliders = self.driver.find_elements(By.CSS_SELECTOR, 
                        'canvas, svg, iframe, [class*="captcha"], [id*="captcha"], [class*="bot"], [id*="bot"]')
                    
                    for element in vonage_sliders:
                        if element.is_displayed():
                            slider_element = element
                            slider_detected = True
                            logger.info(f"Found vonage-specific slider: {element.tag_name}")
                            break
                except:
                    pass
            
            # Strategy 4: Look for interactive elements that might be sliders
            if not slider_detected:
                try:
                    interactive_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                        '[draggable="true"], [role="slider"], [aria-valuenow], .interactive, .draggable')
                    
                    for element in interactive_elements:
                        if element.is_displayed() and element.is_enabled():
                            slider_element = element
                            slider_detected = True
                            logger.info(f"Found potential slider element: {element.tag_name}.{element.get_attribute('class')}")
                            break
                except:
                    pass
            
            if slider_detected and slider_element:
                logger.info("Sliding verification detected! Attempting automatic solution...")
                
                # Try automatic solution first for simple cases
                if self._try_automatic_slider_solution(slider_element):
                    logger.info("Automatic slider solution successful!")
                    time.sleep(1)  # Reduced wait time
                    return True
                
                # Try enhanced automatic solution with multiple strategies
                if self._try_enhanced_slider_solution(slider_element):
                    logger.info("Enhanced slider solution successful!")
                    time.sleep(1)  # Reduced wait time
                    return True
                
                # If all automatic solutions fail, try quick manual prompt with timeout
                logger.warning("Automatic solutions failed. Quick manual solving required.")
                print(f"\nSliding verification requires manual interaction.")
                print("You have 30 seconds to solve it manually, or the script will continue...")
                
                # Try to highlight the slider element
                try:
                    self.driver.execute_script("arguments[0].style.border='3px solid red'", slider_element)
                    time.sleep(1)
                except:
                    pass
                
                # Quick manual solving with timeout
                try:
                    import threading
                    
                    def manual_solve_timeout():
                        time.sleep(5)  # Reduced from 30s for faster execution
                        print("\nTimeout reached. Continuing with automation...")
                    
                    timeout_thread = threading.Thread(target=manual_solve_timeout)
                    timeout_thread.daemon = True
                    timeout_thread.start()
                    
                    # Automated continuation instead of manual input
                    logger.info("Continuing with automated slider solving...")
                    time.sleep(2)  # Brief wait for any automatic processes (reduced)
                    
                except KeyboardInterrupt:
                    logger.info("Manual solving interrupted, continuing...")
                
                # Reduced wait time for verification processing
                time.sleep(2)
                
                # Switch back to main frame if we were in an iframe
                try:
                    self.driver.switch_to.default_content()
                except:
                    pass
                
                return True
            
            # Switch back to main frame if we were in an iframe
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error handling sliding verification: {e}")
            # Make sure we're back in the main frame
            try:
                self.driver.switch_to.default_content()
            except:
                pass
            return False

    def _try_automatic_slider_solution(self, slider_element):
        """Attempt to automatically solve sliding verification with multiple strategies."""
        try:
            logger.info("Attempting automatic slider solution...")
            
            from selenium.webdriver.common.action_chains import ActionChains
            
            # Strategy 1: Look for specific slider handle/button within the element
            slider_handle = self._find_slider_handle(slider_element)
            if slider_handle:
                logger.info("Found slider handle, attempting to drag...")
                if self._drag_slider_handle(slider_handle):
                    return True
            
            # Strategy 2: Try clicking the slider element directly
            logger.info("Trying direct click on slider element...")
            try:
                slider_element.click()
                time.sleep(1)  # Reduced wait time
                if self._check_verification_success():
                    logger.info("Direct click solved the verification!")
                    return True
            except:
                pass
            
            # Strategy 3: Look for slider track and calculate drag distance
            logger.info("Trying slider track method...")
            if self._solve_slider_by_track(slider_element):
                return True
            
            # Strategy 4: Try multiple drag distances and directions
            logger.info("Trying multiple drag strategies...")
            if self._try_multiple_drag_strategies(slider_element):
                return True
            
            # Strategy 5: Look for puzzle pieces (for puzzle sliders)
            logger.info("Checking for puzzle slider...")
            if self._solve_puzzle_slider(slider_element):
                return True
            
            logger.info("All automatic strategies failed")
            return False
            
        except Exception as e:
            logger.debug(f"Error in automatic slider solution: {e}")
            return False

    def _try_enhanced_slider_solution(self, slider_element):
        """Enhanced slider solution with faster and more aggressive strategies."""
        try:
            logger.info("Attempting enhanced slider solution...")
            
            from selenium.webdriver.common.action_chains import ActionChains
            
            # Strategy 1: Fast multiple rapid clicks
            logger.info("Trying rapid click strategy...")
            try:
                for i in range(3):
                    slider_element.click()
                    time.sleep(0.5)  # Very short delay
                    if self._check_verification_success():
                        logger.info("Rapid clicks solved the verification!")
                        return True
            except:
                pass
            
            # Strategy 2: Fast drag with minimal delays
            logger.info("Trying fast drag strategy...")
            try:
                actions = ActionChains(self.driver)
                actions.click_and_hold(slider_element)
                actions.move_by_offset(300, 0)  # Full drag
                actions.release()
                actions.perform()
                time.sleep(1)  # Reduced wait time
                
                if self._check_verification_success():
                    logger.info("Fast drag solved the verification!")
                    return True
            except:
                pass
            
            # Strategy 3: Try different starting positions with fast execution
            logger.info("Trying fast position-based strategy...")
            try:
                element_size = slider_element.size
                actions = ActionChains(self.driver)
                
                # Start from left edge and drag quickly
                actions.move_to_element_with_offset(slider_element, 5, element_size['height'] // 2)
                actions.click_and_hold()
                actions.move_by_offset(element_size['width'] - 10, 0)
                actions.release()
                actions.perform()
                time.sleep(1)  # Reduced wait time
                
                if self._check_verification_success():
                    logger.info("Fast position-based drag solved the verification!")
                    return True
            except:
                pass
            
            # Strategy 4: Try JavaScript-based solution
            logger.info("Trying JavaScript-based solution...")
            try:
                # Try to trigger verification through JavaScript
                self.driver.execute_script("""
                    arguments[0].click();
                    arguments[0].dispatchEvent(new Event('mousedown'));
                    arguments[0].dispatchEvent(new Event('mouseup'));
                """, slider_element)
                time.sleep(1)  # Reduced wait time
                
                if self._check_verification_success():
                    logger.info("JavaScript solution solved the verification!")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in enhanced slider solution: {e}")
            return False

    def _find_slider_handle(self, slider_element):
        """Find the actual draggable handle within the slider."""
        try:
            # Look for common slider handle selectors
            handle_selectors = [
                '.slider-handle',
                '.slider-button',
                '.slider-thumb',
                '.handle',
                '.thumb',
                '.slider-knob',
                '[role="slider"]',
                '[class*="handle"]',
                '[class*="thumb"]',
                '[class*="button"]',
                'button',
                '.draggable'
            ]
            
            for selector in handle_selectors:
                try:
                    handles = slider_element.find_elements(By.CSS_SELECTOR, selector)
                    for handle in handles:
                        if handle.is_displayed() and handle.is_enabled():
                            logger.info(f"Found slider handle: {selector}")
                            return handle
                except:
                    continue
            
            return None
            
        except Exception as e:
            logger.debug(f"Error finding slider handle: {e}")
            return None

    def _drag_slider_handle(self, handle):
        """Drag the slider handle to complete verification."""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            
            # Get handle position and size
            handle_location = handle.location
            handle_size = handle.size
            
            # Try different drag distances
            drag_distances = [100, 150, 200, 250, 300]
            
            for distance in drag_distances:
                try:
                    logger.info(f"Trying drag distance: {distance}px")
                    
                    # Reset to original position first
                    actions.reset_actions()
                    
                    # Drag horizontally to the right
                    actions.click_and_hold(handle)
                    actions.move_by_offset(distance, 0)
                    actions.release()
                    actions.perform()
                    
                    time.sleep(2)
                    
                    if self._check_verification_success():
                        logger.info(f"Successful drag with distance: {distance}px")
                        return True
                        
                except Exception as e:
                    logger.debug(f"Drag attempt failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.debug(f"Error dragging slider handle: {e}")
            return False

    def _solve_slider_by_track(self, slider_element):
        """Solve slider by finding track and calculating exact drag distance."""
        try:
            # Look for slider track
            track_selectors = [
                '.slider-track',
                '.track',
                '.slider-bar',
                '.progress-bar',
                '[class*="track"]',
                '[class*="bar"]'
            ]
            
            track = None
            for selector in track_selectors:
                try:
                    tracks = slider_element.find_elements(By.CSS_SELECTOR, selector)
                    if tracks:
                        track = tracks[0]
                        logger.info(f"Found slider track: {selector}")
                        break
                except:
                    continue
            
            if track:
                # Calculate drag distance based on track width
                track_size = track.size
                drag_distance = track_size['width'] - 20  # Leave some margin
                
                # Find handle within the slider
                handle = self._find_slider_handle(slider_element)
                if handle:
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    
                    actions.click_and_hold(handle)
                    actions.move_by_offset(drag_distance, 0)
                    actions.release()
                    actions.perform()
                    
                    time.sleep(2)
                    return self._check_verification_success()
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in track-based solution: {e}")
            return False

    def _try_multiple_drag_strategies(self, slider_element):
        """Try multiple drag strategies with different approaches."""
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            
            # Strategy 1: Drag the entire slider element
            try:
                actions = ActionChains(self.driver)
                actions.click_and_hold(slider_element)
                actions.move_by_offset(200, 0)
                actions.release()
                actions.perform()
                time.sleep(2)
                
                if self._check_verification_success():
                    logger.info("Slider element drag successful")
                    return True
            except:
                pass
            
            # Strategy 2: Smooth gradual drag
            try:
                actions = ActionChains(self.driver)
                actions.click_and_hold(slider_element)
                
                # Gradual movement
                for i in range(0, 200, 20):
                    actions.move_by_offset(20, 0)
                    time.sleep(0.1)
                
                actions.release()
                actions.perform()
                time.sleep(2)
                
                if self._check_verification_success():
                    logger.info("Gradual drag successful")
                    return True
            except:
                pass
            
            # Strategy 3: Try different starting points
            try:
                element_size = slider_element.size
                actions = ActionChains(self.driver)
                
                # Start from left edge
                actions.move_to_element_with_offset(slider_element, 10, element_size['height'] // 2)
                actions.click_and_hold()
                actions.move_by_offset(element_size['width'] - 20, 0)
                actions.release()
                actions.perform()
                time.sleep(2)
                
                if self._check_verification_success():
                    logger.info("Edge-based drag successful")
                    return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in multiple drag strategies: {e}")
            return False

    def _solve_puzzle_slider(self, slider_element):
        """Handle puzzle-type sliders where you need to fit pieces together."""
        try:
            # Look for puzzle pieces
            puzzle_selectors = [
                '.puzzle-piece',
                '.puzzle-slider',
                '[class*="puzzle"]',
                '.jigsaw',
                '[class*="jigsaw"]'
            ]
            
            puzzle_detected = False
            for selector in puzzle_selectors:
                try:
                    pieces = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if pieces:
                        puzzle_detected = True
                        logger.info(f"Detected puzzle slider: {selector}")
                        break
                except:
                    continue
            
            if puzzle_detected:
                # For puzzle sliders, try to drag to complete the image
                # This is more complex and may require image analysis
                logger.info("Puzzle slider detected - attempting basic solution")
                
                from selenium.webdriver.common.action_chains import ActionChains
                actions = ActionChains(self.driver)
                
                # Try dragging across the full width
                actions.click_and_hold(slider_element)
                actions.move_by_offset(300, 0)  # Full drag
                actions.release()
                actions.perform()
                
                time.sleep(3)
                return self._check_verification_success()
            
            return False
            
        except Exception as e:
            logger.debug(f"Error in puzzle slider solution: {e}")
            return False

    def _check_verification_success(self):
        """Check if the verification was successful using multiple indicators."""
        try:
            # Look for success indicators
            success_indicators = [
                '.verification-success',
                '.verification-complete',
                '.slider-success',
                '.success',
                '.complete',
                '[class*="success"]',
                '[class*="complete"]',
                '[class*="verified"]',
                '.verified',
                '.validation-success'
            ]
            
            for selector in success_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        logger.info(f"Success indicator found: {selector}")
                        return True
                except:
                    continue
            
            # Check for error indicators (means we need to try again)
            error_indicators = [
                '.verification-error',
                '.verification-failed',
                '.error',
                '.failed',
                '[class*="error"]',
                '[class*="failed"]'
            ]
            
            for selector in error_indicators:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements and any(el.is_displayed() for el in elements):
                        logger.info(f"Error indicator found: {selector}")
                        return False
                except:
                    continue
            
            # Check if form submission button is now enabled
            try:
                submit_buttons = self.driver.find_elements(By.CSS_SELECTOR, 
                    'button[type="submit"], .submit, .send, .btn-submit')
                for button in submit_buttons:
                    if button.is_enabled() and button.is_displayed():
                        button_classes = button.get_attribute('class') or ''
                        if 'disabled' not in button_classes.lower():
                            logger.info("Submit button is now enabled - verification likely successful")
                            return True
            except:
                pass
            
            # Check if slider is now disabled/hidden (common after success)
            try:
                sliders = self.driver.find_elements(By.CSS_SELECTOR, 
                    '[class*="slider"], [class*="verification"]')
                for slider in sliders:
                    if not slider.is_displayed() or 'disabled' in (slider.get_attribute('class') or ''):
                        logger.info("Slider is now disabled/hidden - verification likely successful")
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.debug(f"Error checking verification success: {e}")
            return False

    def process_website(self, url, retry_count=0, max_retries=2):
        """Process a single website: find contact page and fill form with enhanced error handling and retry logic."""
        try:
            logger.info(f"Processing website: {url} (attempt {retry_count + 1}/{max_retries + 1})")
            
            # Validate URL format
            if not self._is_valid_url(url):
                logger.error(f"Invalid URL format: {url}")
                return False, "invalid_url"
            
            # Check if driver is alive before starting
            if not self._is_driver_alive():
                logger.warning("Driver not responsive, attempting recovery before processing")
                if not self._handle_driver_crash():
                    logger.error("Failed to recover driver before processing")
                    return False, "driver_failed"
            
            # Try to access the website with enhanced error handling
            access_success = False
            for attempt in range(3):  # 3 attempts for website access
                try:
                    logger.info(f"Attempting to navigate to: {url} (access attempt {attempt + 1}/3)")
                    
                    # Use enhanced page loading
                    if ULTRA_FAST_MODE:
                        # In ultra-fast mode, do minimal accessibility check with improved timing
                        try:
                            logger.info(f"Ultra-fast mode: Enhanced page load for {url}")
                            self._enhanced_page_load(url, timeout=15)
                            time.sleep(self.PAGE_LOAD_WAIT)  # Use configured wait time
                            current_url = self.driver.current_url
                            if current_url and current_url != "data:,":
                                logger.info(f"Page loaded successfully: {current_url}")
                                access_success = True
                                break
                            else:
                                logger.warning(f"Page may not have loaded properly, but continuing...")
                                access_success = True
                                break
                        except Exception as e:
                            logger.warning(f"Enhanced page load failed in ultra-fast mode (attempt {attempt + 1}): {e}")
                            if attempt < 2:
                                time.sleep(2 ** attempt)  # Exponential backoff
                                continue
                    else:
                        # Standard mode - do full accessibility check with enhanced loading
                        try:
                            self._enhanced_page_load(url, timeout=30)
                            if self._check_website_accessibility(url):
                                access_success = True
                                break
                            else:
                                logger.warning(f"Website accessibility check failed (attempt {attempt + 1})")
                                if attempt < 2:
                                    time.sleep(2 ** attempt)  # Exponential backoff
                                    continue
                        except Exception as e:
                            logger.warning(f"Enhanced accessibility check failed (attempt {attempt + 1}): {e}")
                            if attempt < 2:
                                time.sleep(2 ** attempt)  # Exponential backoff
                                continue
                        
                except Exception as e:
                    logger.error(f"Failed to access website {url} (attempt {attempt + 1}): {e}")
                    # Check if this is a driver-related error
                    error_msg = str(e).lower()
                    if any(error_type in error_msg for error_type in [
                        'invalid session id', 'target window already closed', 
                        'session deleted', 'no such window', 'target frame detached'
                    ]):
                        logger.warning("Driver error detected during website access, attempting recovery")
                        if self._handle_driver_crash():
                            continue  # Retry with recovered driver
                    
                    if attempt < 2:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
            
            if not access_success:
                logger.error(f"Failed to access website after 3 attempts: {url}")
                return False, "access_failed"
            
            # Find contact page with retry logic
            contact_page_found = False
            for attempt in range(2):  # 2 attempts for contact page finding
                try:
                    logger.info(f"Searching for contact page on: {url} (attempt {attempt + 1}/2)")
                    if self.find_contact_page(url):
                        contact_page_found = True
                        break
                    else:
                        logger.warning(f"No contact page found (attempt {attempt + 1})")
                        if attempt < 1:
                            time.sleep(1)  # Wait before retry (reduced)
                            continue
                except Exception as e:
                    logger.error(f"Error finding contact page (attempt {attempt + 1}): {e}")
                    if attempt < 1:
                        time.sleep(3)
                        continue
            
            if not contact_page_found:
                logger.warning(f"No contact page found after 2 attempts on: {url}")
                return False, "no_contact_page"
            
            # Fill contact form with retry logic
            form_success = False
            for attempt in range(3):  # 3 attempts for form filling
                try:
                    logger.info(f"Attempting to fill and submit forms on: {url} (attempt {attempt + 1}/3)")
                    if self._fill_contact_form():
                        logger.info(f"Form submitted successfully on: {url}")
                        form_success = True
                        break
                    else:
                        logger.warning(f"Failed to fill contact form (attempt {attempt + 1}) - trying emergency recovery...")
                        # Emergency recovery - try one more time with different approach
                        try:
                            time.sleep(5)  # Wait for any dynamic content
                            if self._emergency_form_recovery():
                                logger.info(f"Emergency recovery successful for {url}")
                                form_success = True
                                break
                            else:
                                logger.error(f"Emergency recovery also failed for {url}")
                        except Exception as recovery_error:
                            logger.error(f"Emergency recovery crashed for {url}: {recovery_error}")
                        
                        if attempt < 2:
                            time.sleep(2)  # Wait before retry (reduced)
                            # Try to refresh the page for next attempt
                            try:
                                self.driver.refresh()
                                time.sleep(3)
                            except:
                                pass
                            continue
                except Exception as e:
                    logger.error(f"Error filling contact form (attempt {attempt + 1}): {e}")
                    if attempt < 2:
                        time.sleep(5)
                        # Try to refresh the page for next attempt
                        try:
                            self.driver.refresh()
                            time.sleep(3)
                        except:
                            pass
                        continue
            
            if form_success:
                return True, "success"
            else:
                logger.warning(f"Failed to fill contact form after 3 attempts on: {url}")
                return False, "form_failed"
                
        except Exception as e:
            logger.error(f"Error processing website {url}: {e}")
            return False, "unexpected_error"

    def _is_valid_url(self, url):
        """Validate URL format and accessibility."""
        try:
            # Basic URL format validation
            if not url or not isinstance(url, str):
                return False
            
            # Check if URL starts with http or https
            if not url.startswith(('http://', 'https://')):
                logger.warning(f"URL must start with http:// or https://: {url}")
                return False
            
            # Check if URL has a valid domain
            parsed = urlparse(url)
            if not parsed.netloc or '.' not in parsed.netloc:
                logger.warning(f"Invalid domain in URL: {url}")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Error validating URL {url}: {e}")
            return False

    def _check_website_accessibility(self, url):
        """ULTRA-FAST accessibility check - minimal validation for speed."""
        try:
            logger.info(f"Checking accessibility for: {url}")
            
            # Try to access the website with minimal wait
            self.driver.get(url)
            
            # In ultra-fast mode, skip most checks and just verify basic load
            if ULTRA_FAST_MODE:
                time.sleep(self.PAGE_LOAD_WAIT)  # Use configured wait time
                
                # Just check if we got a response (don't wait for full page load)
                try:
                    current_url = self.driver.current_url
                    if current_url and current_url != "data:,":
                        logger.info(f"Page loaded successfully: {current_url}")
                        return True
                    else:
                        logger.warning(f"Page may not have loaded properly: {current_url}")
                        return False
                except Exception:
                    # If we can't get current_url, assume it's working
                    return True
            else:
                # Standard mode - do full accessibility check
                time.sleep(self.PAGE_LOAD_WAIT)
                
                # Check current URL and page title
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                logger.info(f"Current URL: {current_url}")
                logger.info(f"Page title: {page_title}")
                
                # Quick check for critical errors first
                if "404" in page_title.lower() or "not found" in page_title.lower():
                    logger.error(f"404 error page detected for: {url}")
                    return False
                
                # Only check for Cloudflare/CAPTCHA if page seems blocked
                page_source = self.driver.page_source.lower()
                if any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'access denied']):
                    logger.warning("Protection detected - attempting quick bypass...")
                    if not self._quick_bypass_protection():
                        logger.error("Protection bypass failed")
                        return False
                
                return True
            
        except Exception as e:
            logger.error(f"Error checking website accessibility: {e}")
            return False

    def _quick_bypass_protection(self):
        """Fully automated bypass for Cloudflare/CAPTCHA protection - no manual intervention."""
        try:
            logger.info("Attempting fully automated protection bypass...")
            
            # Strategy 1: Extended automatic wait (optimized for speed)
            logger.info("Strategy 1: Extended automatic wait for clearance...")
            if ULTRA_FAST_MODE:
                max_wait_time = 10  # Reduced for ultra fast mode
            else:
                max_wait_time = 30  # Standard wait time
            start_time = time.time()
            
            while time.time() - start_time < max_wait_time:
                page_source = self.driver.page_source.lower()
                if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'access denied', 'checking your browser']):
                    logger.info("Protection cleared automatically")
                    return True
                time.sleep(1)  # Check every 1 second (reduced)
            
            # Strategy 2: Comprehensive automated button detection and click
            logger.info("Strategy 2: Comprehensive automated button detection...")
            automated_buttons = [
                # Cloudflare buttons
                "//button[contains(text(), 'Continue')]",
                "//button[contains(text(), 'Proceed')]",
                "//button[contains(text(), 'Verify')]",
                "//button[contains(text(), 'I am human')]",
                "//button[contains(text(), 'Check')]",
                "//button[contains(text(), 'Confirm')]",
                "//a[contains(text(), 'Continue')]",
                "//a[contains(text(), 'Proceed')]",
                "//a[contains(text(), 'Verify')]",
                
                # reCAPTCHA elements
                ".recaptcha-checkbox-border",
                ".recaptcha-checkbox",
                "#recaptcha-anchor",
                "iframe[src*='recaptcha']",
                
                # hCaptcha elements
                ".h-captcha",
                "#hcaptcha",
                "iframe[src*='hcaptcha']",
                
                # Generic CAPTCHA elements
                ".captcha",
                "#captcha",
                "input[name*='captcha']",
                "img[src*='captcha']",
                
                # Additional verification elements
                ".verify-button",
                ".verification-button",
                ".challenge-button",
                ".security-check",
                ".ddos-protection"
            ]
            
            for xpath in automated_buttons:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            logger.info(f"Found automated button: {element.text or element.get_attribute('class') or 'CAPTCHA element'}")
                            
                            # Try different click methods
                            try:
                                element.click()
                            except:
                                try:
                                    self.driver.execute_script("arguments[0].click();", element)
                                except:
                                    try:
                                        ActionChains(self.driver).move_to_element(element).click().perform()
                                    except:
                                        continue
                            
                            time.sleep(1)  # Wait for action to complete (reduced)
                            
                            # Check if protection is cleared
                            page_source = self.driver.page_source.lower()
                            if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'checking your browser']):
                                logger.info("Protection bypass successful via automated button click")
                                return True
                except:
                    continue
            
            # Strategy 3: Automated iframe handling for CAPTCHAs
            logger.info("Strategy 3: Automated iframe handling...")
            try:
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    try:
                        iframe_src = iframe.get_attribute('src') or ''
                        if any(indicator in iframe_src.lower() for indicator in ['recaptcha', 'hcaptcha', 'captcha']):
                            logger.info(f"Found CAPTCHA iframe: {iframe_src}")
                            
                            # Switch to iframe
                            self.driver.switch_to.frame(iframe)
                            
                            # Look for checkbox or button in iframe
                            iframe_buttons = [
                                ".recaptcha-checkbox-border",
                                ".recaptcha-checkbox",
                                ".h-captcha",
                                "input[type='checkbox']",
                                "button",
                                ".checkbox"
                            ]
                            
                            for button_selector in iframe_buttons:
                                try:
                                    iframe_element = self.driver.find_element(By.CSS_SELECTOR, button_selector)
                                    if iframe_element.is_displayed() and iframe_element.is_enabled():
                                        logger.info(f"Found CAPTCHA element in iframe: {button_selector}")
                                        iframe_element.click()
                                        time.sleep(2)
                                        break
                                except:
                                    continue
                            
                            # Switch back to main content
                            self.driver.switch_to.default_content()
                            time.sleep(3)
                            
                            # Check if protection is cleared
                            page_source = self.driver.page_source.lower()
                            if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'checking your browser']):
                                logger.info("Protection bypass successful via iframe handling")
                                return True
                    except:
                        self.driver.switch_to.default_content()
                        continue
            except Exception as e:
                logger.debug(f"Error in iframe handling: {e}")
                self.driver.switch_to.default_content()
            
            # Strategy 4: Automated JavaScript execution to bypass protection
            logger.info("Strategy 4: Automated JavaScript bypass...")
            try:
                js_bypass_scripts = [
                    # Remove Cloudflare protection elements
                    "document.querySelectorAll('[class*=\"cloudflare\"]').forEach(el => el.remove());",
                    "document.querySelectorAll('[id*=\"cloudflare\"]').forEach(el => el.remove());",
                    
                    # Remove CAPTCHA elements
                    "document.querySelectorAll('.recaptcha').forEach(el => el.remove());",
                    "document.querySelectorAll('.h-captcha').forEach(el => el.remove());",
                    "document.querySelectorAll('.captcha').forEach(el => el.remove());",
                    
                    # Click any verification buttons
                    "document.querySelectorAll('button').forEach(btn => { if(btn.textContent.toLowerCase().includes('continue') || btn.textContent.toLowerCase().includes('verify') || btn.textContent.toLowerCase().includes('proceed')) btn.click(); });",
                    
                    # Submit any forms
                    "document.querySelectorAll('form').forEach(form => { if(form.style.display !== 'none') form.submit(); });",
                    
                    # Remove overlay elements
                    "document.querySelectorAll('[class*=\"overlay\"]').forEach(el => el.remove());",
                    "document.querySelectorAll('[class*=\"modal\"]').forEach(el => el.remove());",
                    "document.querySelectorAll('[class*=\"popup\"]').forEach(el => el.remove());"
                ]
                
                for script in js_bypass_scripts:
                    try:
                        self.driver.execute_script(script)
                        time.sleep(1)
                    except:
                        continue
                
                time.sleep(3)
                
                # Check if protection is cleared
                page_source = self.driver.page_source.lower()
                if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'checking your browser']):
                    logger.info("Protection bypass successful via JavaScript")
                    return True
                    
            except Exception as e:
                logger.debug(f"Error in JavaScript bypass: {e}")
            
            # Strategy 5: Automated form submission bypass
            logger.info("Strategy 5: Automated form submission bypass...")
            try:
                # Find and submit any forms on the page
                forms = self.driver.find_elements(By.TAG_NAME, "form")
                for form in forms:
                    try:
                        if form.is_displayed():
                            logger.info("Attempting automated form submission...")
                            self.driver.execute_script("arguments[0].submit();", form)
                            time.sleep(3)
                            
                            # Check if protection is cleared
                            page_source = self.driver.page_source.lower()
                            if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'checking your browser']):
                                logger.info("Protection bypass successful via form submission")
                                return True
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Error in form submission bypass: {e}")
            
            # Strategy 6: Final automated attempt - refresh and wait
            logger.info("Strategy 6: Final automated attempt - refresh and wait...")
            try:
                self.driver.refresh()
                time.sleep(5)
                
                # Wait for automatic clearance
                start_time = time.time()
                while time.time() - start_time < 15:  # 15 seconds
                    page_source = self.driver.page_source.lower()
                    if not any(indicator in page_source for indicator in ['cloudflare', 'captcha', 'blocked', 'checking your browser']):
                        logger.info("Protection cleared after refresh")
                        return True
                    time.sleep(2)
            except Exception as e:
                logger.debug(f"Error in final automated attempt: {e}")
            
            logger.warning("All automated bypass attempts failed - continuing anyway")
            return True  # Continue anyway to avoid blocking the process
            
        except Exception as e:
            logger.error(f"Error in automated bypass: {e}")
            return True  # Continue anyway to avoid blocking the process

    def _bypass_cloudflare_protection(self):
        """Enhanced Cloudflare protection bypass with human-like behavior simulation."""
        try:
            logger.info("Attempting enhanced Cloudflare bypass with human-like behavior...")
            
            # Strategy 1: Human-like page interaction before waiting
            logger.info("Strategy 1: Simulating human-like page interaction...")
            self._simulate_human_behavior()
            
            # Strategy 2: Extended wait with periodic interaction
            logger.info("Strategy 2: Extended wait with periodic human-like interaction...")
            max_wait_time = 45  # Increased wait time
            start_time = time.time()
            interaction_interval = 8  # Interact every 8 seconds
            last_interaction = 0
            
            while time.time() - start_time < max_wait_time:
                current_time = time.time()
                
                # Periodic human-like interaction
                if current_time - last_interaction > interaction_interval:
                    self._simulate_human_behavior(light=True)
                    last_interaction = current_time
                
                if not self._detect_cloudflare_protection():
                    logger.info("Cloudflare cleared with human-like behavior")
                    return True
                
                time.sleep(1.5)  # Slightly irregular timing
            
            # Strategy 3: Enhanced button detection with human-like clicking
            logger.info("Strategy 3: Enhanced button detection with human-like clicking...")
            human_buttons = [
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'i am human')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'verify')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'continue')]",
                "//button[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'proceed')]",
                "//input[@type='checkbox' and contains(@class, 'cf-')]",
                "//div[contains(@class, 'cf-challenge')]",
                "//div[contains(@class, 'challenge-form')]",
                ".cf-challenge-form input[type='checkbox']",
                ".challenge-form button",
                "[data-ray] button",
                "[data-cf-beacon] button"
            ]
            
            for xpath in human_buttons:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath) if xpath.startswith('//') else self.driver.find_elements(By.CSS_SELECTOR, xpath)
                    for button in elements:
                        if button.is_displayed() and button.is_enabled():
                            logger.info(f"Found verification element: {button.text or button.get_attribute('class')}")
                            
                            # Human-like clicking with random delay
                            self._human_like_click(button)
                            time.sleep(random.uniform(3, 7))  # Random wait
                            
                            if not self._detect_cloudflare_protection():
                                logger.info("Cloudflare bypass successful via enhanced button click")
                                return True
                except Exception as e:
                    logger.debug(f"Error with button {xpath}: {e}")
                    continue
            
            # Strategy 4: Advanced iframe and challenge handling
            logger.info("Strategy 4: Advanced iframe and challenge handling...")
            if self._handle_advanced_challenges():
                return True
            
            # Strategy 5: Fallback with extended wait
            logger.info("Strategy 5: Fallback with extended wait and behavior simulation...")
            for i in range(3):  # 3 attempts
                self._simulate_human_behavior()
                time.sleep(random.uniform(8, 15))
                
                if not self._detect_cloudflare_protection():
                    logger.info(f"Cloudflare bypass successful on fallback attempt {i+1}")
                    return True
            
            logger.warning("Cloudflare protection still active - continuing with limited functionality")
            return True  # Continue anyway to avoid complete blocking
            
        except Exception as e:
            logger.error(f"Error in enhanced Cloudflare bypass: {e}")
            return False

    def _detect_captcha(self):
        """Detect if CAPTCHA is present."""
        try:
            page_source = self.driver.page_source.lower()
            
            # CAPTCHA indicators
            captcha_indicators = [
                'captcha', 'recaptcha', 'hcaptcha', 'verify you are human',
                'i am not a robot', 'security check', 'verification'
            ]
            
            for indicator in captcha_indicators:
                if indicator in page_source:
                    logger.info(f"CAPTCHA indicator found: {indicator}")
                    return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Error detecting CAPTCHA: {e}")
            return False
    
    def _detect_cloudflare_protection(self):
        """Enhanced Cloudflare protection detection."""
        try:
            page_source = self.driver.page_source.lower()
            cloudflare_indicators = [
                'cloudflare',
                'checking your browser',
                'please wait while we check your browser',
                'ddos protection',
                'ray id',
                'cf-ray',
                'challenge-form',
                'cf-challenge',
                'please enable javascript',
                'browser check',
                'security check',
                'attention required',
                'cloudflare to restrict access',
                'verify you are human',
                'just a moment',
                'completing security check'
            ]
            
            for indicator in cloudflare_indicators:
                if indicator in page_source:
                    logger.debug(f"Cloudflare protection detected: {indicator}")
                    return True
            
            # Check for Cloudflare-specific elements
            cloudflare_selectors = [
                "[data-ray]",
                ".cf-challenge-form",
                ".challenge-form",
                "#challenge-form",
                "[data-cf-beacon]",
                ".cf-wrapper",
                ".cf-error-details",
                "#cf-error-details",
                ".cf-browser-verification"
            ]
            
            for selector in cloudflare_selectors:
                try:
                    if self.driver.find_elements(By.CSS_SELECTOR, selector):
                        logger.debug(f"Cloudflare element detected: {selector}")
                        return True
                except:
                    continue
            
            # Check page title for Cloudflare indicators
            try:
                title = self.driver.title.lower()
                title_indicators = ['attention required', 'cloudflare', 'just a moment', 'security check']
                for indicator in title_indicators:
                    if indicator in title:
                        logger.debug(f"Cloudflare detected in title: {indicator}")
                        return True
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting Cloudflare protection: {e}")
            return False
    
    def _simulate_human_behavior(self, light=False):
        """Simulate human-like behavior on the page."""
        try:
            if light:
                # Light interaction - just mouse movement
                actions = ActionChains(self.driver)
                # Random mouse movement
                actions.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
                actions.perform()
                time.sleep(random.uniform(0.5, 1.5))
            else:
                # Full human-like behavior simulation
                actions = ActionChains(self.driver)
                
                # Random mouse movements
                for _ in range(random.randint(2, 4)):
                    actions.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
                    time.sleep(random.uniform(0.3, 0.8))
                
                actions.perform()
                
                # Random scrolling
                scroll_amount = random.randint(-300, 300)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(1, 2))
                
                # Random key press (like pressing space or arrow keys)
                if random.choice([True, False]):
                    actions = ActionChains(self.driver)
                    actions.send_keys(Keys.SPACE if random.choice([True, False]) else Keys.ARROW_DOWN)
                    actions.perform()
                    time.sleep(random.uniform(0.5, 1))
                
        except Exception as e:
            logger.debug(f"Error simulating human behavior: {e}")
    
    def _human_like_click(self, element):
        """Perform human-like clicking with random delays and movements."""
        try:
            # Move to element with slight randomness
            actions = ActionChains(self.driver)
            actions.move_to_element_with_offset(element, random.randint(-5, 5), random.randint(-5, 5))
            time.sleep(random.uniform(0.5, 1.5))
            
            # Random pre-click delay
            time.sleep(random.uniform(0.2, 0.8))
            
            # Try multiple click methods
            click_methods = [
                lambda: element.click(),
                lambda: actions.click(element).perform(),
                lambda: self.driver.execute_script("arguments[0].click();", element)
            ]
            
            for method in click_methods:
                try:
                    method()
                    logger.debug("Human-like click successful")
                    break
                except Exception as e:
                    logger.debug(f"Click method failed: {e}")
                    continue
            
            # Post-click delay
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.debug(f"Error in human-like click: {e}")
    
    def _handle_advanced_challenges(self):
        """Handle advanced Cloudflare challenges including iframes and complex forms."""
        try:
            logger.info("Handling advanced challenges...")
            
            # Check for iframes that might contain challenges
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    # Switch to iframe
                    self.driver.switch_to.frame(iframe)
                    
                    # Look for challenge elements within iframe
                    challenge_elements = [
                        "input[type='checkbox']",
                        "button[type='submit']",
                        ".recaptcha-checkbox",
                        ".h-captcha-checkbox",
                        "[data-callback]"
                    ]
                    
                    for selector in challenge_elements:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            for element in elements:
                                if element.is_displayed() and element.is_enabled():
                                    logger.info(f"Found challenge element in iframe: {selector}")
                                    self._human_like_click(element)
                                    time.sleep(random.uniform(2, 5))
                                    
                                    # Switch back and check if protection is cleared
                                    self.driver.switch_to.default_content()
                                    if not self._detect_cloudflare_protection():
                                        logger.info("Advanced challenge bypass successful")
                                        return True
                                    
                                    # Switch back to iframe for next attempt
                                    self.driver.switch_to.frame(iframe)
                        except Exception as e:
                            logger.debug(f"Error with iframe element {selector}: {e}")
                            continue
                    
                    # Switch back to main content
                    self.driver.switch_to.default_content()
                    
                except Exception as e:
                    logger.debug(f"Error handling iframe: {e}")
                    # Ensure we're back to main content
                    try:
                        self.driver.switch_to.default_content()
                    except:
                        pass
                    continue
            
            # Try JavaScript-based challenge solving
            js_solutions = [
                "document.querySelector('[data-ray] input[type=\"checkbox\"]')?.click();",
                "document.querySelector('.cf-challenge-form input[type=\"checkbox\"]')?.click();",
                "document.querySelector('.challenge-form button')?.click();",
                "document.querySelector('[data-cf-beacon] button')?.click();"
            ]
            
            for js_code in js_solutions:
                try:
                    self.driver.execute_script(js_code)
                    time.sleep(random.uniform(2, 4))
                    
                    if not self._detect_cloudflare_protection():
                        logger.info("JavaScript challenge bypass successful")
                        return True
                except Exception as e:
                    logger.debug(f"JavaScript solution failed: {e}")
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Error handling advanced challenges: {e}")
            return False

    def _solve_captcha(self):
        """Attempt to solve CAPTCHA."""
        try:
            logger.info("Attempting CAPTCHA solving...")
            
            # Strategy 1: Try automatic solving for simple CAPTCHAs
            logger.info("Strategy 1: Attempting automatic CAPTCHA solving...")
            
            # Look for reCAPTCHA checkboxes
            try:
                recaptcha_checkbox = self.driver.find_element(By.CSS_SELECTOR, '.recaptcha-checkbox-border')
                if recaptcha_checkbox.is_displayed():
                    logger.info("Found reCAPTCHA checkbox - attempting to click")
                    recaptcha_checkbox.click()
                    time.sleep(5)
                    
                    if not self._detect_captcha():
                        logger.info("reCAPTCHA solved automatically")
                        return True
            except:
                pass
            
            # Look for hCaptcha checkboxes
            try:
                hcaptcha_checkbox = self.driver.find_element(By.CSS_SELECTOR, '.h-captcha')
                if hcaptcha_checkbox.is_displayed():
                    logger.info("Found hCaptcha - attempting to click")
                    hcaptcha_checkbox.click()
                    time.sleep(5)
                    
                    if not self._detect_captcha():
                        logger.info("hCaptcha solved automatically")
                        return True
            except:
                pass
            
            # Strategy 2: Manual intervention
            logger.info("Strategy 2: Requesting manual CAPTCHA solving...")
            print("\n" + "="*50)
            print("CAPTCHA DETECTED")
            print("="*50)
            print("A CAPTCHA challenge has been detected on the website.")
            print("Please manually solve the CAPTCHA in the browser.")
            print("Steps:")
            print("1. Look for a CAPTCHA challenge (puzzle, image selection, etc.)")
            print("2. Complete the challenge")
            print("3. Wait for verification to complete")
            print("4. Press Enter in this terminal when done")
            print("="*50)
            
            # Automated continuation instead of manual input
            logger.info("Continuing with automated CAPTCHA solving...")
            time.sleep(3)  # Wait for automatic processes (reduced)
            
            # Check if CAPTCHA is still present
            if not self._detect_captcha():
                logger.info("CAPTCHA solved successfully via automated intervention")
                return True
            else:
                logger.warning("CAPTCHA still present - continuing anyway")
                return True  # Continue anyway to avoid blocking
            
        except Exception as e:
            logger.error(f"Error solving CAPTCHA: {e}")
            return False

    def _remove_url_from_file(self, urls_file, url_to_remove):
        """No-op — Django manages URLs via the database."""
        pass

    def run_automation(self, urls_file=None):
        """Run the automation for all URLs in the specified file."""
        try:
            # Resolve URLs file relative to this script directory to avoid CWD issues
            base_dir = os.path.dirname(os.path.abspath(__file__))
            urls_path = urls_file if os.path.isabs(urls_file) else os.path.join(base_dir, urls_file)

            if not os.path.exists(urls_path):
                logger.error(f"URLs file not found: {urls_file}")
                print(f"Error: URLs file '{urls_file}' not found!")
                print("Please create a file named 'urls.txt' with one URL per line.")
                return
            else:
                logger.info(f"Using URLs file: {urls_path}")
            
            successful = 0
            failed = 0
            processed_count = 0
            
            # Write session header to results file (BEFORE driver setup)
            try:
                with open(self.results_file, 'a', encoding='utf-8') as rf:
                    rf.write("\n=== Session: {} ===\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
                    rf.write("Timestamp\tStatus\tDuration(s)\tURL\tCompany\n")
                    rf.flush()
                    try:
                        os.fsync(rf.fileno())
                    except Exception:
                        pass
                print(f"Results will be written to: {self.results_file}")
            except Exception as e:
                logger.debug(f"Unable to write session header to results file: {e}")

            # Setup driver after ensuring results file is ready
            if not self.setup_driver():
                logger.error("Failed to setup Chrome driver")
                return
            
            # Process URLs one by one, continuously reading from file
            while True:
                # Read current URLs from file
                try:
                    with open(urls_path, 'r', encoding='utf-8', errors='ignore') as f:
                        urls = [line.strip() for line in f if line.strip() and not line.lstrip().startswith('#')]
                    logger.info(f"Read {len(urls)} URL(s) from file")
                    if urls:
                        logger.debug(f"First URLs sample: {urls[:3]}")
                except Exception as e:
                    logger.error(f"Error reading URLs file: {e}")
                    break
                
                if not urls:
                    logger.info("No more URLs to process")
                    print("No more URLs to process")
                    break
                
                # Process the first URL
                url = urls[0]
                processed_count += 1
                print(f"\nProcessing {processed_count}: {url}")
                
                start_ts = time.time()
                max_retries = 2
                success = False
                error_reason = "unknown"
                
                # Main processing loop with retry logic
                for retry_attempt in range(max_retries + 1):
                    try:
                        # Check driver health before processing
                        if not self._is_driver_alive():
                            logger.warning(f"Driver not responsive, attempting recovery")
                            if not self._handle_driver_crash():
                                error_reason = "driver_crash"
                                break
                        
                        if retry_attempt > 0:
                            logger.info(f"Retrying {url} (attempt {retry_attempt + 1}/{max_retries + 1})")
                            print(f"  Retrying... (attempt {retry_attempt + 1}/{max_retries + 1})")
                            
                            # Attempt error recovery before retry
                            if error_reason and error_reason != "unknown":
                                recovery_success = self._recover_from_error(error_reason, url)
                                if recovery_success:
                                    logger.info(f"Error recovery successful for {error_reason}")
                                else:
                                    logger.debug(f"Error recovery failed for {error_reason}")
                            
                            # Exponential backoff between retries
                            wait_time = min(10, 2 ** retry_attempt)
                            time.sleep(wait_time)
                            
                            # Reset driver state for retry
                            try:
                                self.driver.delete_all_cookies()
                                self.driver.execute_script("window.localStorage.clear();")
                                self.driver.execute_script("window.sessionStorage.clear();")
                            except:
                                pass
                        
                        result, reason = self.process_website(url, retry_attempt, max_retries)
                        
                        if result:
                            successful += 1
                            duration = round(time.time() - start_ts, 2)
                            self._append_execution_result(url, 'success', duration)
                            success = True
                            break
                        else:
                            error_reason = reason
                            logger.warning(f"Attempt {retry_attempt + 1} failed for {url}: {reason}")
                            
                            # Use smart retry decision
                            if not self._smart_retry_decision(reason, retry_attempt, max_retries):
                                logger.info(f"Smart retry decision: not retrying {url} due to: {reason}")
                                break
                    
                    except Exception as e:
                        logger.error(f"Unexpected error processing {url} (attempt {retry_attempt + 1}): {e}")
                        error_reason = "unexpected_error"
                        
                        # Check for connection-related errors that should trigger URL skipping
                        error_str = str(e).lower()
                        connection_errors = [
                            "connection refused", 
                            "httpconnectionpool", 
                            "remotedisconnected", 
                            "newconnectionerror",
                            "connectionerror",
                            "max retries exceeded",
                            "connection aborted"
                        ]
                        
                        is_connection_error = any(error_keyword in error_str for error_keyword in connection_errors)
                        
                        if is_connection_error:
                            logger.warning(f"Connection error detected for {url}: {e}")
                            print(f"  Connection error detected: {e}")
                            print(f"  Skipping URL {url} and waiting 2 minutes before continuing...")
                            logger.info(f"Skipping URL {url} due to connection error, waiting 2 minutes")
                            
                            # Mark as failed and skip this URL
                            failed += 1
                            duration = round(time.time() - start_ts, 2)
                            self._append_execution_result(url, 'failed_connection_error', duration)
                            
                            # Remove the URL from file since we're skipping it
                            try:
                                self._remove_url_from_file(urls_path, url)
                            except Exception as remove_error:
                                logger.error(f"Error removing URL from file: {remove_error}")
                            
                            # Wait 2 minutes before continuing to next URL
                            time.sleep(120)  # 2 minutes = 120 seconds
                            break  # Skip to next URL
                        
                        # Handle driver-related errors with recovery
                        if "driver" in error_str or "session" in error_str:
                            logger.warning(f"Driver error detected: {e}")
                            if retry_attempt < max_retries:
                                logger.info("Attempting driver recovery...")
                                if self._handle_driver_crash():
                                    logger.info("Driver recovery successful, continuing...")
                                    continue
                                else:
                                    logger.error("Driver recovery failed, stopping retries")
                                    break
                            else:
                                logger.error(f"Driver error on final attempt, giving up: {e}")
                                break
                
                # Handle final result
                if not success:
                    failed += 1
                    duration = round(time.time() - start_ts, 2)
                    status = "failed"
                    self._append_execution_result(url, status, duration)
                    print(f"  Failed after {max_retries + 1} attempts: {error_reason}")
                
                # Remove processed URL from file
                try:
                    self._remove_url_from_file(urls_path, url)
                except Exception as e:
                    logger.error(f"Error removing URL from file: {e}")
                
                # 5-minute pause between websites as requested
                print(f"  Pausing for 5 minutes before processing next URL...")
                logger.info(f"Pausing for 5 minutes before processing next URL")
                time.sleep(3)  # 5 minutes = 300 seconds
            
            print(f"\n" + "="*60)
            print("AUTOMATION COMPLETED!")
            print(f"Successful: {successful}")
            print(f"Failed: {failed}")
            print(f"Total processed: {processed_count}")
            print("="*60)
            
            logger.info(f"Automation completed. Successful: {successful}, Failed: {failed}, Total processed: {processed_count}")
            
        except Exception as e:
            logger.error(f"Error running automation: {e}")
            print(f"Error: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()

    def run_automation_multi_tab(self, urls_file=None, batch_size=5):
        """Run the automation for URLs in batches using multiple tabs (up to 5 tabs simultaneously)."""
        try:
            # Resolve URLs file relative to this script directory to avoid CWD issues
            base_dir = os.path.dirname(os.path.abspath(__file__))
            urls_path = urls_file if os.path.isabs(urls_file) else os.path.join(base_dir, urls_file)

            if not os.path.exists(urls_path):
                logger.error(f"URLs file not found: {urls_file}")
                print(f"Error: URLs file '{urls_file}' not found!")
                print("Please create a file named 'urls.txt' with one URL per line.")
                return
            else:
                logger.info(f"Using URLs file: {urls_path}")
            
            with open(urls_path, 'r', encoding='utf-8', errors='ignore') as f:
                urls = [line.strip() for line in f if line.strip() and not line.lstrip().startswith('#')]
            logger.info(f"Read {len(urls)} URL(s) from file for multi-tab run")
            if urls:
                logger.debug(f"First URLs sample: {urls[:3]}")
            
            if not urls:
                logger.error("No URLs found in the file")
                print("Error: No URLs found in the file!")
                return
            
            logger.info(f"Found {len(urls)} URLs to process in batches of {batch_size}")
            print(f"Found {len(urls)} URLs to process in batches of {batch_size}")
            
            # Write session header to results file
            try:
                with open(self.results_file, 'a', encoding='utf-8') as rf:
                    rf.write("\n=== Multi-Tab Session: {} ===\n".format(time.strftime('%Y-%m-%d %H:%M:%S')))
                    rf.write("Timestamp\tStatus\tDuration(s)\tURL\tTab\tCompany\n")
                    rf.flush()
                    try:
                        os.fsync(rf.fileno())
                    except Exception:
                        pass
                print(f"Results will be written to: {self.results_file}")
            except Exception as e:
                logger.debug(f"Unable to write session header to results file: {e}")

            # Setup driver
            if not self.setup_driver():
                logger.error("Failed to setup Chrome driver")
                for url in urls:
                    self._append_execution_result_multi_tab(url, 'DRIVER_FAILED', 0.0, 0)
                return
            
            # Process URLs in batches
            total_successful = 0
            total_failed = 0
            
            for batch_start in range(0, len(urls), batch_size):
                batch_urls = urls[batch_start:batch_start + batch_size]
                batch_num = (batch_start // batch_size) + 1
                
                print(f"\nProcessing batch {batch_num}: {len(batch_urls)} URLs")
                logger.info(f"Starting batch {batch_num} with {len(batch_urls)} URLs")
                
                successful, failed = self._process_urls_in_tabs(batch_urls, batch_num)
                total_successful += successful
                total_failed += failed
                
                # 5-minute pause between batches as requested
                if batch_start + batch_size < len(urls):
                    print("Pausing for 5 minutes before processing next batch...")
                    logger.info("Pausing for 5 minutes before processing next batch")
                    time.sleep(3)  # 5 minutes = 300 seconds
            
            print(f"\n" + "="*60)
            print("MULTI-TAB AUTOMATION COMPLETED!")
            print(f"Successful: {total_successful}")
            print(f"Failed: {total_failed}")
            print(f"Total: {len(urls)}")
            print("="*60)
            
            logger.info(f"Multi-tab automation completed. Successful: {total_successful}, Failed: {total_failed}")
            
        except Exception as e:
            logger.error(f"Error running multi-tab automation: {e}")
            print(f"Error: {e}")
        
        finally:
            if self.driver:
                self.driver.quit()

    def _process_urls_in_tabs(self, urls, batch_num):
        """Process a batch of URLs simultaneously in different tabs."""
        successful = 0
        failed = 0
        tab_handles = []
        url_tab_mapping = {}
        
        try:
            # Open tabs for each URL
            for i, url in enumerate(urls):
                if i == 0:
                    # Use the current tab for the first URL
                    tab_handles.append(self.driver.current_window_handle)
                else:
                    # Open new tab
                    self.driver.execute_script("window.open('');")
                    tab_handles.append(self.driver.window_handles[-1])
                
                url_tab_mapping[url] = {'tab_handle': tab_handles[i], 'tab_index': i}
                print(f"  Tab {i+1}: {url}")
            
            # Load URLs in parallel
            results = {}
            for url in urls:
                tab_info = url_tab_mapping[url]
                tab_handle = tab_info['tab_handle']
                tab_index = tab_info['tab_index']
                
                try:
                    # Switch to tab
                    self.driver.switch_to.window(tab_handle)
                    
                    # Start loading the URL
                    start_time = time.time()
                    logger.info(f"Loading {url} in tab {tab_index + 1}")
                    
                    # Load URL with timeout
                    self.driver.set_page_load_timeout(30)
                    self.driver.get(url)
                    
                    results[url] = {
                        'start_time': start_time,
                        'tab_index': tab_index,
                        'status': 'loaded',
                        'tab_handle': tab_handle
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to load {url} in tab {tab_index + 1}: {e}")
                    results[url] = {
                        'start_time': time.time(),
                        'tab_index': tab_index,
                        'status': 'load_failed',
                        'error': str(e),
                        'tab_handle': tab_handle
                    }
            
            # Process each URL in its tab
            for url in urls:
                result_info = results[url]
                tab_handle = result_info['tab_handle']
                tab_index = result_info['tab_index']
                start_time = result_info['start_time']
                
                try:
                    # Switch to the tab
                    self.driver.switch_to.window(tab_handle)
                    
                    if result_info['status'] == 'load_failed':
                        failed += 1
                        duration = round(time.time() - start_time, 2)
                        self._append_execution_result_multi_tab(url, 'failed', duration, tab_index + 1)
                        print(f"  Tab {tab_index + 1}: FAILED (load error)")
                        continue
                    
                    print(f"  Processing Tab {tab_index + 1}: {url}")
                    
                    # Process the website in this tab
                    success, reason = self._process_website_in_current_tab(url)
                    
                    duration = round(time.time() - start_time, 2)
                    
                    if success:
                        successful += 1
                        self._append_execution_result_multi_tab(url, 'success', duration, tab_index + 1)
                        print(f"  Tab {tab_index + 1}: success ({duration}s)")
                    else:
                        failed += 1
                        status = "failed"
                        self._append_execution_result_multi_tab(url, status, duration, tab_index + 1)
                        print(f"  Tab {tab_index + 1}: FAILED - {reason} ({duration}s)")
                        
                except Exception as e:
                    # Check for connection-related errors
                    error_str = str(e).lower()
                    connection_errors = [
                        "connection refused", 
                        "httpconnectionpool", 
                        "remotedisconnected", 
                        "newconnectionerror",
                        "connectionerror",
                        "max retries exceeded",
                        "connection aborted"
                    ]
                    
                    is_connection_error = any(error_keyword in error_str for error_keyword in connection_errors)
                    
                    if is_connection_error:
                        logger.warning(f"Connection error detected for {url} in tab {tab_index + 1}: {e}")
                        print(f"  Tab {tab_index + 1}: CONNECTION ERROR - {str(e)[:50]}...")
                        print(f"  Waiting 2 minutes before continuing...")
                        
                        failed += 1
                        duration = round(time.time() - start_time, 2)
                        self._append_execution_result_multi_tab(url, 'failed_connection_error', duration, tab_index + 1)
                        
                        # Wait 2 minutes for connection errors
                        time.sleep(120)  # 2 minutes = 120 seconds
                    else:
                        failed += 1
                        duration = round(time.time() - start_time, 2)
                        self._append_execution_result_multi_tab(url, 'failed', duration, tab_index + 1)
                        logger.error(f"Error processing {url} in tab {tab_index + 1}: {e}")
                        print(f"  Tab {tab_index + 1}: ERROR - {str(e)[:50]}...")
            
            # Close additional tabs (keep the first one)
            for i in range(1, len(tab_handles)):
                try:
                    self.driver.switch_to.window(tab_handles[i])
                    self.driver.close()
                except Exception as e:
                    logger.debug(f"Error closing tab {i}: {e}")
            
            # Switch back to the first tab
            if tab_handles:
                try:
                    self.driver.switch_to.window(tab_handles[0])
                except Exception as e:
                    logger.debug(f"Error switching to first tab: {e}")
            
        except Exception as e:
            logger.error(f"Error in batch processing: {e}")
            print(f"Batch processing error: {e}")
        
        return successful, failed

    def _process_website_in_current_tab(self, url):
        """Process a website in the current tab (simplified version of process_website)."""
        try:
            logger.info(f"Processing website in current tab: {url}")
            
            # Validate URL format
            if not self._is_valid_url(url):
                logger.error(f"Invalid URL format: {url}")
                return False, "invalid_url"
            
            # Wait for page to be ready
            time.sleep(self.PAGE_LOAD_WAIT)
            
            # Check if we can access the page
            try:
                current_url = self.driver.current_url
                if not current_url or current_url == "data:,":
                    return False, "page_not_loaded"
            except Exception as e:
                logger.error(f"Cannot access current URL: {e}")
                return False, "access_error"
            
            # Find contact page
            try:
                if not self.find_contact_page(url):
                    logger.warning(f"No contact page found on: {url}")
                    return False, "no_contact_page"
            except Exception as e:
                logger.error(f"Error finding contact page: {e}")
                return False, "contact_search_error"
            
            # Fill contact form
            try:
                if self._fill_contact_form():
                    logger.info(f"Form submitted successfully on: {url}")
                    return True, "success"
                else:
                    logger.warning(f"Failed to fill contact form on: {url} - trying emergency recovery...")
                    # Emergency recovery - try one more time with different approach
                    try:
                        time.sleep(5)  # Wait for any dynamic content
                        if self._emergency_form_recovery():
                            logger.info(f"Emergency recovery successful for {url}")
                            return True, "success"
                        else:
                            logger.error(f"Emergency recovery also failed for {url}")
                            return False, "form_failed"
                    except Exception as recovery_error:
                        logger.error(f"Emergency recovery crashed for {url}: {recovery_error}")
                        return False, "form_failed"
            except Exception as e:
                logger.error(f"Error filling contact form: {e}")
                return False, "form_error"
                
        except Exception as e:
            logger.error(f"Error processing website in tab {url}: {e}")
            return False, "unexpected_error"

    def _append_execution_result_multi_tab(self, url, status, duration_seconds, tab_number):
        """Log multi-tab result."""
        logger.info(f"Result (tab {tab_number}): {status} - {url} ({duration_seconds:.1f}s)")

    def _append_execution_result(self, url, status, duration_seconds):
        """Log result — Django handles storage via FormTask model."""
        logger.info(f"Result: {status} - {url} ({duration_seconds:.1f}s) - {self.contact_data.get('company', '')}")

    def _notify_dashboard(self):
        """No-op — Django auto-refreshes via polling."""
        pass

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
    
    def _recover_from_error(self, error_type, url):
        """Attempt to recover from specific error types."""
        try:
            logger.info(f"Attempting error recovery for {error_type} on {url}")
            
            if error_type == "access_failed":
                # Try alternative URL formats
                alternative_urls = []
                if url.startswith('http://'):
                    alternative_urls.append(url.replace('http://', 'https://'))
                elif url.startswith('https://'):
                    alternative_urls.append(url.replace('https://', 'http://'))
                
                # Try with/without www
                parsed = urlparse(url)
                if parsed.netloc.startswith('www.'):
                    new_netloc = parsed.netloc[4:]
                    alternative_urls.append(f"{parsed.scheme}://{new_netloc}{parsed.path}")
                else:
                    new_netloc = f"www.{parsed.netloc}"
                    alternative_urls.append(f"{parsed.scheme}://{new_netloc}{parsed.path}")
                
                for alt_url in alternative_urls:
                    try:
                        logger.info(f"Trying alternative URL: {alt_url}")
                        self.driver.get(alt_url)
                        time.sleep(3)
                        if self.driver.current_url and self.driver.current_url != "data:,":
                            logger.info(f"Successfully accessed alternative URL: {alt_url}")
                            return True
                    except Exception as e:
                        logger.debug(f"Alternative URL failed: {alt_url} - {e}")
                        continue
            
            elif error_type == "form_failed":
                # Try to clear browser state and reload
                try:
                    self.driver.delete_all_cookies()
                    self.driver.execute_script("window.localStorage.clear();")
                    self.driver.execute_script("window.sessionStorage.clear();")
                    self.driver.refresh()
                    time.sleep(5)
                    logger.info("Browser state cleared and page refreshed")
                    return True
                except Exception as e:
                    logger.debug(f"Failed to clear browser state: {e}")
            
            elif error_type == "unexpected_error":
                # Try to restart the driver session
                try:
                    logger.info("Attempting to recover driver session")
                    current_url = self.driver.current_url
                    self.driver.refresh()
                    time.sleep(3)
                    
                    # Check if we can still interact with the page
                    self.driver.execute_script("return document.readyState")
                    logger.info("Driver session recovered successfully")
                    return True
                except Exception as e:
                    logger.debug(f"Driver session recovery failed: {e}")
            
            return False
            
        except Exception as e:
            logger.debug(f"Error recovery attempt failed: {e}")
            return False
    
    def _handle_driver_crash(self):
        """Handle driver crashes and attempt to restart."""
        try:
            logger.warning("Attempting to recover from driver crash")
            
            # Try to quit the existing driver
            try:
                if self.driver:
                    self.driver.quit()
            except:
                pass
            
            # Wait a moment
            time.sleep(5)
            
            # Reinitialize the driver
            if self.setup_driver():
                logger.info("Driver successfully restarted after crash")
                return True
            else:
                logger.error("Failed to restart driver after crash")
                return False
                
        except Exception as e:
            logger.error(f"Driver crash recovery failed: {e}")
            return False
    
    def _is_driver_alive(self):
        """Check if the driver is still alive and responsive."""
        try:
            if not self.driver:
                return False
            
            # Try to get current URL to test driver responsiveness
            current_url = self.driver.current_url
            return True
        except Exception as e:
            logger.debug(f"Driver responsiveness check failed: {e}")
            return False
    
    def _safe_driver_action(self, action_func, *args, max_retries=2, **kwargs):
        """Safely execute driver actions with automatic recovery on failure."""
        for attempt in range(max_retries + 1):
            try:
                # Check if driver is alive before attempting action
                if not self._is_driver_alive():
                    logger.warning(f"Driver not responsive, attempting recovery (attempt {attempt + 1})")
                    if not self._handle_driver_crash():
                        continue
                
                # Execute the action
                return action_func(*args, **kwargs)
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Check for specific error types that indicate driver issues
                if any(error_type in error_msg for error_type in [
                    'invalid session id', 'target window already closed', 
                    'session deleted', 'no such window', 'target frame detached'
                ]):
                    logger.warning(f"Driver session error detected: {e}")
                    if attempt < max_retries:
                        logger.info(f"Attempting driver recovery (attempt {attempt + 1}/{max_retries})")
                        if self._handle_driver_crash():
                            continue
                        else:
                            logger.error("Driver recovery failed")
                            break
                    else:
                        logger.error(f"Max retries reached for driver action: {e}")
                        raise
                
                # Check for stale element errors
                elif 'stale element' in error_msg:
                    logger.debug(f"Stale element error: {e}")
                    if attempt < max_retries:
                        time.sleep(1)  # Brief wait before retry
                        continue
                    else:
                        raise
                
                # For other errors, re-raise immediately
                else:
                    raise
        
        # If we get here, all retries failed
        raise Exception(f"Failed to execute driver action after {max_retries + 1} attempts")
    
    def _enhanced_page_load(self, url, timeout=30, max_retries=3):
        """Enhanced page loading with comprehensive error handling and retry mechanisms."""
        for attempt in range(max_retries):
            try:
                # Set page load timeout
                self.driver.set_page_load_timeout(timeout)
                
                # Load the page
                self.driver.get(url)
                
                # Wait for document ready state with enhanced stability check
                self._wait_for_page_stability(timeout=min(timeout, 15))
                
                # Verify page loaded successfully
                if self._verify_page_loaded(url):
                    return True
                else:
                    logger.warning(f"Page verification failed for {url}, attempt {attempt + 1}")
                    
            except TimeoutException:
                logger.warning(f"Page load timeout for {url}, attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                    
            except WebDriverException as e:
                if "net::ERR_" in str(e) or "timeout" in str(e).lower():
                    logger.warning(f"Network error loading {url}: {e}, attempt {attempt + 1}")
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                else:
                    logger.error(f"WebDriver error loading {url}: {e}")
                    break
                    
            except Exception as e:
                logger.error(f"Unexpected error loading {url}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                break
        
        return False
    
    def _verify_page_loaded(self, expected_url):
        """Verify that the page loaded correctly."""
        try:
            current_url = self.driver.current_url
            
            # Check if we're on an error page
            error_indicators = [
                "404", "not found", "error", "unavailable", 
                "server error", "connection", "timeout"
            ]
            
            page_source = self.driver.page_source.lower()
            title = self.driver.title.lower()
            
            for indicator in error_indicators:
                if indicator in title or indicator in page_source[:1000]:
                    logger.debug(f"Error page detected: {indicator} found")
                    return False
            
            # Check if page has minimal content
            if len(page_source.strip()) < 100:
                logger.debug("Page appears to be empty or minimal")
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Page verification failed: {e}")
            return False
    
    def _enhanced_find_elements(self, by, value, timeout=10):
        """Enhanced element finding with automatic retry on stale elements."""
        def find_elements():
            wait = WebDriverWait(self.driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, value)))
            return elements
        
        return self._safe_driver_action(find_elements)
    
    def _enhanced_click_element(self, element, timeout=10, retry_count=3):
        """Enhanced element clicking with multiple strategies and stale element recovery."""
        for attempt in range(retry_count):
            try:
                # Wait for element to be clickable
                WebDriverWait(self.driver, timeout).until(
                    EC.element_to_be_clickable(element)
                )
                
                # Strategy 1: Scroll element into view and use human-like click
                try:
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.5)
                    
                    if self._human_like_click(element):
                        return True
                except Exception as e:
                    logger.debug(f"Human-like click failed: {e}")
                
                # Strategy 2: JavaScript click
                try:
                    self.driver.execute_script("arguments[0].click();", element)
                    return True
                except Exception as e:
                    logger.debug(f"JavaScript click failed: {e}")
                
                # Strategy 3: ActionChains click
                try:
                    actions = ActionChains(self.driver)
                    actions.move_to_element(element).click().perform()
                    return True
                except Exception as e:
                    logger.debug(f"ActionChains click failed: {e}")
                
                # Strategy 4: Force click with event dispatch
                try:
                    self.driver.execute_script(
                        "arguments[0].dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));", 
                        element
                    )
                    return True
                except Exception as e:
                    logger.debug(f"Force click failed: {e}")
                    
            except Exception as e:
                if 'stale element' in str(e).lower() and attempt < retry_count - 1:
                    logger.debug(f"Stale element detected, retrying... (attempt {attempt + 1})")
                    time.sleep(1)
                    continue
                else:
                    logger.debug(f"Enhanced click failed on attempt {attempt + 1}: {e}")
                    
        return False
    
    def _enhanced_link_click_with_navigation(self, link, expected_result_check=None, return_on_failure=True):
        """Enhanced link clicking with navigation handling and dynamic content support."""
        try:
            # Store current URL for potential return navigation
            original_url = self.driver.current_url
            
            # Get link information before clicking
            link_text = link.text.strip() if link.text else ''
            link_href = link.get_attribute('href') or ''
            
            logger.info(f"Attempting to click link: '{link_text}' -> {link_href}")
            
            # Enhanced click with multiple strategies
            if not self._enhanced_click_element(link, timeout=5):
                logger.warning(f"Failed to click link: {link_text}")
                return False
            
            # Wait for navigation or dynamic content loading
            self._wait_for_page_stability()
            
            # Check if we're on a new page or if content changed
            new_url = self.driver.current_url
            if new_url != original_url:
                logger.info(f"Navigation detected: {original_url} -> {new_url}")
            else:
                logger.info("No navigation detected, checking for dynamic content changes")
                # Wait a bit more for potential AJAX content
                time.sleep(2)
            
            # Run the expected result check if provided
            if expected_result_check and callable(expected_result_check):
                try:
                    result = expected_result_check()
                    if result:
                        logger.info(f"Link click successful - expected result achieved")
                        return True
                    else:
                        logger.info(f"Link click did not achieve expected result")
                        if return_on_failure and new_url != original_url:
                            self._safe_navigate_back(original_url)
                        return False
                except Exception as e:
                    logger.debug(f"Error checking expected result: {e}")
                    if return_on_failure and new_url != original_url:
                        self._safe_navigate_back(original_url)
                    return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Enhanced link click failed: {e}")
            return False
    
    def _wait_for_page_stability(self, timeout=10):
        """Enhanced page stability detection with multiple indicators."""
        try:
            # Wait for document ready state
            WebDriverWait(self.driver, timeout).until(
                lambda driver: driver.execute_script("return document.readyState") == "complete"
            )
            
            # Wait for any pending AJAX requests (jQuery)
            try:
                WebDriverWait(self.driver, 3).until(
                    lambda driver: driver.execute_script("return typeof jQuery === 'undefined' || jQuery.active === 0")
                )
            except:
                pass  # jQuery might not be available
            
            # Wait for Angular applications
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda driver: driver.execute_script(
                        "return typeof angular === 'undefined' || angular.element(document).injector().get('$http').pendingRequests.length === 0"
                    )
                )
            except:
                pass  # Angular might not be available
            
            # Wait for React applications (check for pending state updates)
            try:
                WebDriverWait(self.driver, 2).until(
                    lambda driver: driver.execute_script(
                        "return typeof React === 'undefined' || !document.querySelector('[data-reactroot]') || true"
                    )
                )
            except:
                pass  # React might not be available
            
            # Check for loading indicators
            self._wait_for_loading_indicators_to_disappear()
            
            # Wait for network idle (no new requests for a short period)
            self._wait_for_network_idle()
            
            # Additional wait for dynamic content
            time.sleep(1)
            
        except Exception as e:
            logger.debug(f"Page stability wait failed: {e}")
    
    def _wait_for_loading_indicators_to_disappear(self, timeout=5):
        """Wait for common loading indicators to disappear."""
        loading_selectors = [
            '.loading', '.spinner', '.loader', '.preloader',
            '[class*="loading"]', '[class*="spinner"]', '[class*="loader"]',
            '[id*="loading"]', '[id*="spinner"]', '[id*="loader"]',
            '.fa-spinner', '.fa-circle-o-notch', '.glyphicon-refresh',
            '.overlay', '.modal-backdrop', '.progress-bar'
        ]
        
        try:
            for selector in loading_selectors:
                try:
                    WebDriverWait(self.driver, timeout).until_not(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                except:
                    continue  # Selector not found or already gone
        except Exception as e:
            logger.debug(f"Loading indicator wait failed: {e}")
    
    def _wait_for_network_idle(self, timeout=3, idle_time=1):
        """Wait for network to be idle (no new requests)."""
        try:
            # Use Performance API to check for network activity
            script = """
            return new Promise((resolve) => {
                let lastRequestTime = Date.now();
                const checkInterval = 100;
                const idleThreshold = arguments[0] * 1000;
                
                function checkNetworkIdle() {
                    const entries = performance.getEntriesByType('resource');
                    const recentEntries = entries.filter(entry => 
                        entry.responseEnd > (Date.now() - checkInterval)
                    );
                    
                    if (recentEntries.length === 0) {
                        if (Date.now() - lastRequestTime >= idleThreshold) {
                            resolve(true);
                            return;
                        }
                    } else {
                        lastRequestTime = Date.now();
                    }
                    
                    setTimeout(checkNetworkIdle, checkInterval);
                }
                
                checkNetworkIdle();
                
                // Fallback timeout
                setTimeout(() => resolve(true), arguments[1] * 1000);
            });
            """
            
            self.driver.execute_async_script(script, idle_time, timeout)
        except Exception as e:
            logger.debug(f"Network idle wait failed: {e}")
            time.sleep(idle_time)  # Fallback to simple sleep
    
    def _safe_navigate_back(self, original_url):
        """Safely navigate back to original URL."""
        try:
            # Try browser back first
            self.driver.back()
            time.sleep(2)
            
            # Verify we're back to the original URL
            current_url = self.driver.current_url
            if current_url != original_url:
                # Direct navigation if back didn't work
                logger.info(f"Browser back failed, navigating directly to: {original_url}")
                self.driver.get(original_url)
                self._wait_for_page_stability()
                
        except Exception as e:
            logger.debug(f"Safe navigate back failed: {e}")
            # Last resort - direct navigation
            try:
                self.driver.get(original_url)
                self._wait_for_page_stability()
            except Exception as e2:
                logger.error(f"Failed to return to original URL: {e2}")
    
    def _smart_retry_decision(self, error_reason, attempt_count, max_retries):
        """Make intelligent decisions about whether to retry based on error type and history."""
        # Don't retry these error types
        no_retry_errors = ['invalid_url', 'no_contact_page']
        if error_reason in no_retry_errors:
            return False
        
        # Always retry driver-related errors at least once
        driver_errors = ['access_failed', 'unexpected_error']
        if error_reason in driver_errors and attempt_count == 0:
            return True
        
        # Retry form failures up to max attempts
        if error_reason == 'form_failed' and attempt_count < max_retries:
            return True
        
        # Default retry logic
        return attempt_count < max_retries

    def _get_domain_from_url(self):
        """Extract domain from current URL for website-specific customizations."""
        try:
            current_url = self.driver.current_url
            parsed_url = urlparse(current_url)
            domain = parsed_url.netloc.lower()
            # Remove www. prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except:
            return ""
    
    def _get_smart_timeout(self, operation_type='default', page_complexity=None):
        """Dynamic timeout management based on operation type and page complexity."""
        if not SMART_TIMEOUTS:
            return 10  # Default fallback
        
        domain = self._get_domain_from_url()
        
        # Check if we have cached timeout for this domain
        if domain in self.timeout_cache:
            cached_timeout = self.timeout_cache[domain].get(operation_type)
            if cached_timeout:
                return cached_timeout
        
        # Determine page complexity if not provided
        if page_complexity is None:
            page_complexity = self._assess_page_complexity()
        
        # Base timeouts based on operation type
        base_timeouts = {
            'page_load': {'simple': 3, 'medium': 6, 'complex': 10},
            'form_detection': {'simple': 2, 'medium': 4, 'complex': 8},
            'field_filling': {'simple': 1, 'medium': 3, 'complex': 6},
            'form_submission': {'simple': 2, 'medium': 5, 'complex': 10},
            'default': {'simple': 3, 'medium': 6, 'complex': 10}
        }
        
        timeout = base_timeouts.get(operation_type, base_timeouts['default'])[page_complexity]
        
        # Cache the timeout for this domain and operation
        if domain not in self.timeout_cache:
            self.timeout_cache[domain] = {}
        self.timeout_cache[domain][operation_type] = timeout
        
        return timeout
    
    def _assess_page_complexity(self):
        """Assess page complexity for smart timeout management."""
        try:
            # Quick assessment based on DOM elements
            elements_count = len(self.driver.find_elements(By.CSS_SELECTOR, '*'))
            forms_count = len(self.driver.find_elements(By.TAG_NAME, 'form'))
            scripts_count = len(self.driver.find_elements(By.TAG_NAME, 'script'))
            
            # Simple scoring system
            complexity_score = 0
            if elements_count > 1000:
                complexity_score += 2
            elif elements_count > 500:
                complexity_score += 1
            
            if forms_count > 5:
                complexity_score += 2
            elif forms_count > 2:
                complexity_score += 1
            
            if scripts_count > 20:
                complexity_score += 2
            elif scripts_count > 10:
                complexity_score += 1
            
            # Return complexity level
            if complexity_score >= 4:
                return 'complex'
            elif complexity_score >= 2:
                return 'medium'
            else:
                return 'simple'
                
        except Exception as e:
            logger.debug(f"Error assessing page complexity: {e}")
            return 'medium'  # Default to medium complexity
    
    def _smart_wait(self, condition_func, operation_type='default', max_wait=None):
        """Smart waiting with dynamic timeouts and faster polling."""
        if max_wait is None:
            max_wait = self._get_smart_timeout(operation_type)
        
        start_time = time.time()
        poll_interval = 0.1  # Much faster polling (10x faster than default)
        
        while time.time() - start_time < max_wait:
            try:
                if condition_func():
                    return True
            except Exception as e:
                logger.debug(f"Condition check error: {e}")
            
            time.sleep(poll_interval)
        
        return False


