# Spotify AIO - Account Creator with Live Screen Viewer
from flask import Blueprint, render_template, request, jsonify
import threading
import json
import os
import random
import string
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from PIL import Image
import io
import base64

spotify_bp = Blueprint('spotify', __name__, url_prefix='/spotify')

# Global state
spotify_accounts = []
account_file = os.path.expanduser('~/spotify_accounts.txt')
spotify_job_status = {}
spotify_lock = threading.Lock()
spotify_bot_drivers = {}  # Store driver refs for live video capture
spotify_bots_status = {}  # Real-time bot status
captcha_submissions = {}  # Track which bots have user-submitted CAPTCHAs
follower_job_status = {}  # Track follower jobs

def load_accounts():
    """Load saved accounts from file"""
    global spotify_accounts
    if os.path.exists(account_file):
        try:
            with open(account_file, 'r') as f:
                spotify_accounts = [line.strip() for line in f.readlines() if line.strip()]
        except:
            spotify_accounts = []

def save_accounts():
    """Save accounts to file"""
    with open(account_file, 'w') as f:
        for account in spotify_accounts:
            f.write(account + '\n')

def generate_email():
    """Generate random email"""
    return f"spotify_{random.randint(100000, 999999)}@tempmail.com"

def generate_password():
    """Generate secure password"""
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(12))

def generate_username():
    """Generate random username"""
    return f"user_{random.randint(100000, 999999)}"

def random_birthday():
    """Generate random birthday"""
    day = str(random.randint(1, 28))
    month = str(random.randint(1, 12)).zfill(2)
    year = str(random.randint(1990, 2005))
    return day, month, year

def random_gender():
    """Generate random gender - male or female"""
    return random.choice(["male", "female"])

def click_span_button_with_text(driver, wait, text):
    """Helper to click button containing text in span - multiple strategies"""
    strategies = [
        # Strategy 1: Button with span containing text
        (By.XPATH, f"//button//span[contains(text(), '{text}')]/..", "span wrapper"),
        # Strategy 2: Direct button with text
        (By.XPATH, f"//button[contains(normalize-space(), '{text}')]", "direct button"),
        # Strategy 3: Case-insensitive span
        (By.XPATH, f"//button//span[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{text.lower()}')]/..", "case-insensitive"),
        # Strategy 4: Any button with partial text match
        (By.XPATH, f"//button[contains(., '{text}')]", "partial match"),
    ]
    
    for locator, by_type, strategy_name in strategies:
        try:
            button = wait.until(EC.presence_of_element_located((by_type, locator)))
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(0.1)
            
            # Try clickability wait
            try:
                button = wait.until(EC.element_to_be_clickable((by_type, locator)))
            except:
                pass
            
            # Normal click
            try:
                button.click()
                time.sleep(0.2)
                return True
            except:
                # JavaScript click as fallback
                driver.execute_script("arguments[0].click();", button)
                time.sleep(0.2)
                return True
        except Exception as e:
            continue
    
    return False

def launch_spotify_browser():
    """Launch headless Chrome for Spotify with anti-detection measures"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    
    # Anti-detection measures
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    # Realistic user agent
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    options.add_argument(f'user-agent={random.choice(user_agents)}')
    
    # Additional anti-detection options
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    
    # Execute script to mask webdriver detection
    try:
        driver.execute_script('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });
        ''')
    except:
        pass
    
    return driver

def capture_screenshot(driver, crop_to_captcha=False):
    """Capture screenshot from driver - optionally crops to CAPTCHA area"""
    try:
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(io.BytesIO(screenshot))
        
        # Try to find and crop CAPTCHA area using JavaScript if requested
        if crop_to_captcha:
            try:
                captcha_bounds = driver.execute_script("""
                    // Find reCAPTCHA/hCAPTCHA iframe
                    var iframes = document.querySelectorAll('iframe[src*="recaptcha"], iframe[src*="hcaptcha"]');
                    if (iframes.length > 0) {
                        var rect = iframes[0].getBoundingClientRect();
                        // For expanded CAPTCHA, look for the challenge container
                        var parent = iframes[0].parentElement;
                        while (parent && parent.offsetHeight < 500) {
                            parent = parent.parentElement;
                        }
                        if (parent && parent.offsetHeight >= 200) {
                            rect = parent.getBoundingClientRect();
                        }
                        return {x: Math.max(0, rect.left - 50), y: Math.max(0, rect.top - 50), 
                                w: Math.min(1920, rect.width + 100), h: Math.min(1080, rect.height + 100)};
                    }
                    return null;
                """)
                
                if captcha_bounds and captcha_bounds['w'] > 150 and captcha_bounds['h'] > 150:
                    # Crop to CAPTCHA area with generous padding
                    x1 = int(captcha_bounds['x'])
                    y1 = int(captcha_bounds['y'])
                    x2 = int(min(1920, captcha_bounds['x'] + captcha_bounds['w']))
                    y2 = int(min(1080, captcha_bounds['y'] + captcha_bounds['h']))
                    img = img.crop((x1, y1, x2, y2))
            except:
                pass
        
        buffered = io.BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return f"data:image/png;base64,{img_str}"
    except:
        return None

def attempt_auto_solve_captcha(driver, bot_id=None):
    """Try to automatically solve CAPTCHA with multiple strategies - returns True if solved"""
    tag = f"[BOT {bot_id}]" if bot_id else "[AUTO-SOLVE]"
    try:
        
        # Strategy 1: Click I'm not a robot checkbox
        print(f"{tag} 🤖 Attempting auto-solve (Strategy 1: Checkbox click)")
        checkbox_strategies = [
            (By.CSS_SELECTOR, "div.g-recaptcha input[type='checkbox']"),
            (By.CSS_SELECTOR, "div.rc-checkbox-border"),
            (By.XPATH, "//div[@class='g-recaptcha']//input[@type='checkbox']"),
            (By.CSS_SELECTOR, "label > input[type='checkbox'][aria-label*='robot']"),
        ]
        
        for locator_type, locator in checkbox_strategies:
            try:
                checkbox = driver.find_element(locator_type, locator)
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                time.sleep(0.5)
                driver.execute_script("arguments[0].click();", checkbox)
                print(f"{tag} ✓ Clicked checkbox - waiting for auto-solve")
                time.sleep(2)
                
                # Check if challenge page appears (challenge = needs manual solve)
                try:
                    challenge_iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='api2/bframe']")
                    if not challenge_iframes:
                        print(f"{tag} ✓ CAPTCHA verified without challenge!")
                        return True
                except:
                    pass
                
                time.sleep(3)
                
                # Check if CAPTCHA is gone
                iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
                if not iframes:
                    print(f"{tag} ✓ CAPTCHA auto-solved!")
                    return True
            except Exception as e:
                continue
        
        # Strategy 2: Try clicking into iframe context
        print(f"{tag} 🤖 Attempting Strategy 2: Iframe navigation")
        try:
            iframes = driver.find_elements(By.TAG_NAME, "iframe")
            for iframe in iframes:
                try:
                    src = iframe.get_attribute("src").lower()
                    if "recaptcha" in src or "hcaptcha" in src:
                        driver.switch_to.frame(iframe)
                        try:
                            # Try to find and click checkbox in frame
                            checkbox = driver.find_element(By.CSS_SELECTOR, "input[type='checkbox']")
                            checkbox.click()
                            print(f"{tag} ✓ Clicked checkbox in iframe")
                            driver.switch_to.default_content()
                            time.sleep(4)
                            
                            # Check if solved
                            iframes_check = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
                            if not iframes_check:
                                print(f"{tag} ✓ CAPTCHA auto-solved via iframe!")
                                return True
                        except:
                            driver.switch_to.default_content()
                except:
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
        except Exception as e:
            try:
                driver.switch_to.default_content()
            except:
                pass
        
        # Strategy 3: Wait for natural verification (browser fingerprint)
        print(f"{tag} 🤖 Attempting Strategy 3: Waiting for background verification")
        for attempt in range(3):
            time.sleep(3)
            iframes = driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
            if not iframes:
                print(f"{tag} ✓ CAPTCHA passed on attempt {attempt + 1}!")
                return True
        
        print(f"{tag} ✗ Auto-solve failed - manual solve needed")
        return False
        
    except Exception as e:
        print(f"{tag} ✗ Auto-solve error: {str(e)[:50]}")
        return False

@spotify_bp.route('/')
def spotify_dashboard():
    """Spotify AIO Dashboard"""
    return render_template('spotify_dashboard.html')

@spotify_bp.route('/api/create-accounts', methods=['POST'])
def create_accounts():
    """Create multiple Spotify accounts"""
    data = request.json or {}
    count = int(data.get('count', 5))
    
    job_id = f"spotify_{datetime.now().timestamp()}"
    
    with spotify_lock:
        spotify_job_status[job_id] = {
            'total': count,
            'created': 0,
            'status': 'running',
            'current_account': '',
            'current_bot_id': None,
            'accounts': []
        }
    
    def create_worker():
        for bot_id in range(count):
            driver = None
            try:
                # Initialize bot status
                if bot_id not in spotify_bots_status:
                    spotify_bots_status[bot_id] = {}
                
                spotify_bots_status[bot_id] = "🔄 Launching browser..."
                driver = launch_spotify_browser()
                spotify_bot_drivers[bot_id] = driver
                wait = WebDriverWait(driver, 15)
                
                email = generate_email()
                password = generate_password()
                username = generate_username()
                day, month, year = random_birthday()
                gender = random_gender()
                
                # Navigate to signup
                spotify_bots_status[bot_id] = "📍 Loading Spotify..."
                driver.get("https://www.spotify.com/signup")
                time.sleep(1)
                
                # Accept cookies
                spotify_bots_status[bot_id] = "🍪 Accepting cookies..."
                try:
                    cookie_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='accept-cookies']")))
                    cookie_btn.click()
                except:
                    pass
                time.sleep(0.2)
                
                # Email
                spotify_bots_status[bot_id] = f"✉️  Email: {email[:15]}..."
                email_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                email_field.send_keys(email)
                time.sleep(0.2)
                
                spotify_bots_status[bot_id] = "👆 Clicking Next..."
                if not click_span_button_with_text(driver, wait, "Next"):
                    email_field.send_keys(Keys.ENTER)
                time.sleep(0.3)
                
                # Password
                spotify_bots_status[bot_id] = "🔐 Password..."
                password_field = wait.until(EC.presence_of_element_located((By.NAME, "new-password")))
                password_field.send_keys(password)
                time.sleep(0.2)
                
                spotify_bots_status[bot_id] = "👆 Next..."
                if not click_span_button_with_text(driver, wait, "Next"):
                    password_field.send_keys(Keys.ENTER)
                time.sleep(0.3)
                
                # Display name
                spotify_bots_status[bot_id] = "👤 Display name..."
                name_field = wait.until(EC.presence_of_element_located((By.ID, "displayName")))
                name_field.send_keys(username)
                time.sleep(0.2)
                
                spotify_bots_status[bot_id] = "👆 Next..."
                if not click_span_button_with_text(driver, wait, "Next"):
                    name_field.send_keys(Keys.ENTER)
                time.sleep(0.3)
                
                # Birthday
                spotify_bots_status[bot_id] = "📅 Birthday..."
                try:
                    # Try day field
                    day_field = wait.until(EC.presence_of_element_located((By.ID, "day")))
                    day_field.clear()
                    day_field.send_keys(day)
                    
                    # Try month - multiple selectors
                    try:
                        month_select = Select(driver.find_element(By.ID, "month"))
                        month_select.select_by_value(month)
                    except:
                        try:
                            month_select = Select(driver.find_element(By.NAME, "month"))
                            month_select.select_by_value(month)
                        except:
                            # Try by visible text
                            month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                            month_idx = int(month) - 1
                            month_select = Select(driver.find_element(By.ID, "month"))
                            month_select.select_by_visible_text(month_names[month_idx])
                    
                    # Try year field
                    year_field = driver.find_element(By.ID, "year")
                    year_field.clear()
                    year_field.send_keys(year)
                    
                    time.sleep(0.5)
                    if not click_span_button_with_text(driver, wait, "Next"):
                        year_field.send_keys(Keys.ENTER)
                    time.sleep(1)
                except Exception as e:
                    print(f"[BOT {bot_id}] ⚠️ Birthday issue: {str(e)[:50]}")
                    try:
                        click_span_button_with_text(driver, wait, "Next")
                        time.sleep(1)
                    except:
                        pass
                
                # Gender
                spotify_bots_status[bot_id] = "⚙️  Gender..."
                try:
                    # Try finding all radio inputs and click by value
                    gender_element = None
                    
                    # Strategy 1: Find radio with value matching gender
                    gender_short = "m" if gender == "male" else "f"
                    try:
                        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        for radio in radios:
                            radio_val = radio.get_attribute("value")
                            if radio_val == gender_short or radio_val == gender or gender.lower() in (radio_val or "").lower():
                                gender_element = radio
                                break
                    except:
                        pass
                    
                    # Strategy 2: Try gender labels with short form
                    if not gender_element:
                        try:
                            gender_element = driver.find_element(By.CSS_SELECTOR, f"label[for='gender_option_{gender_short}']")
                        except:
                            pass
                    
                    # Strategy 3: Try full gender name in labels
                    if not gender_element:
                        try:
                            gender_element = driver.find_element(By.CSS_SELECTOR, f"label[for*='{gender}']")
                        except:
                            pass
                    
                    # Strategy 4: Search all labels for male/female text
                    if not gender_element:
                        try:
                            labels = driver.find_elements(By.TAG_NAME, "label")
                            for label in labels:
                                label_html = (label.get_attribute("outerHTML") or "").lower()
                                if gender.lower() in label_html:
                                    gender_element = label
                                    break
                        except:
                            pass
                    
                    if gender_element:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gender_element)
                        time.sleep(0.2)
                        try:
                            gender_element.click()
                        except:
                            driver.execute_script("arguments[0].click();", gender_element)
                    
                    time.sleep(0.3)
                    # Try clicking Next button first (like username/password)
                    if not click_span_button_with_text(driver, wait, "Next"):
                        # If Next button click fails, try pressing Enter on the gender element
                        try:
                            if gender_element:
                                gender_element.send_keys(Keys.ENTER)
                        except:
                            pass
                    time.sleep(0.5)
                    
                    # Press Sign up button after gender
                    spotify_bots_status[bot_id] = "📤 Signing up..."
                    try:
                        signup_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign up')]/.. | //button[contains(text(), 'Sign up')]")))
                        driver.execute_script("arguments[0].click();", signup_button)
                        print(f"[BOT {bot_id}] ✅ Clicked Sign up button")
                    except:
                        print(f"[BOT {bot_id}] ⚠️ Could not click Sign up button after gender")
                except Exception as e:
                    print(f"[BOT {bot_id}] ⚠️ Gender issue: {str(e)[:50]}")
                    try:
                        click_span_button_with_text(driver, wait, "Next")
                        time.sleep(3)
                    except:
                        pass
                
                # Accept terms
                try:
                    terms_checkbox = driver.find_element(By.CSS_SELECTOR, "input[name='terms']")
                    if not terms_checkbox.is_selected():
                        terms_checkbox.click()
                    time.sleep(1)
                except:
                    pass
                
                # Final submit - Sign up button
                spotify_bots_status[bot_id] = "📤 Creating account..."
                try:
                    # Find Sign up button and make sure it's visible
                    signup_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign up')]/..")))
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", signup_button)
                    time.sleep(1)
                    signup_button.click()
                except:
                    # Fallback to helper function
                    click_span_button_with_text(driver, wait, "Sign up")
                time.sleep(8)
                
                # Enhanced CAPTCHA detection
                captcha_detected = False
                captcha_type = None
                
                # Check for reCAPTCHA iframe
                try:
                    recaptcha_frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for frame in recaptcha_frames:
                        try:
                            src = (frame.get_attribute("src") or "").lower()
                            if "recaptcha" in src or "challenge" in src:
                                captcha_detected = True
                                captcha_type = "reCAPTCHA"
                                print(f"[BOT {bot_id}] 🔐 reCAPTCHA iframe detected")
                                time.sleep(2)
                                
                                # Try to click the reCAPTCHA checkbox
                                try:
                                    driver.switch_to.frame(frame)
                                    recaptcha_checkbox = driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-border")
                                    recaptcha_checkbox.click()
                                    print(f"[BOT {bot_id}] ✓ Clicked reCAPTCHA checkbox")
                                    time.sleep(3)
                                    driver.switch_to.default_content()
                                except Exception as rc_err:
                                    driver.switch_to.default_content()
                                    print(f"[BOT {bot_id}] Failed to click checkbox: {str(rc_err)[:30]}")
                                break
                        except:
                            pass
                except:
                    pass
                
                # Check for generic CAPTCHA input field
                if not captcha_detected:
                    try:
                        driver.find_element(By.CSS_SELECTOR, "input[name='captcha']")
                        captcha_detected = True
                        captcha_type = "Generic"
                        print(f"[BOT {bot_id}] 🔐 Generic CAPTCHA field detected")
                    except:
                        pass
                
                # Don't try to click Continue yet - wait for CAPTCHA solve first
                # The user will solve it manually and then Continue gets clicked automatically
                
                if captcha_detected:
                    # Skip auto-solve - go straight to manual solving (faster)
                    spotify_bots_status[bot_id] = f"⏸️ {captcha_type or 'CAPTCHA'} - Waiting for manual solve"
                    print(f"[BOT {bot_id}] 🔐 {captcha_type or 'CAPTCHA'} detected! Waiting for user to solve manually...")
                    
                    # Clear previous submission flag
                    captcha_submissions[bot_id] = False
                    
                    # Mark bot as waiting for CAPTCHA solution
                    with spotify_lock:
                        if job_id not in spotify_job_status:
                            spotify_job_status[job_id] = {'status': 'captcha', 'bot_id': bot_id}
                        else:
                            spotify_job_status[job_id]['waiting_captcha_bot'] = bot_id
                    
                    # Wait for CAPTCHA to be solved - wait for USER SUBMISSION (max 5 minutes)
                    captcha_solved = False
                    wait_time = 0
                    while wait_time < 300:  # 5 minutes timeout
                        time.sleep(1)
                        wait_time += 1
                        
                        # Check if user submitted the CAPTCHA via API
                        if captcha_submissions.get(bot_id, False):
                            print(f"[BOT {bot_id}] ✓ User submitted CAPTCHA solution!")
                            captcha_solved = True
                            break
                    
                    if captcha_solved:
                        spotify_bots_status[bot_id] = "✓ CAPTCHA solved! Checking for more CAPTCHAs..."
                        print(f"[BOT {bot_id}] ✓ CAPTCHA solved! Waiting before checking for more...")
                        
                        # Wait a bit for the page to update after CAPTCHA solve
                        time.sleep(3)
                        
                        # Check if there's ANOTHER CAPTCHA after this one
                        print(f"[BOT {bot_id}] 🔍 Re-checking for CAPTCHAs...")
                        another_captcha_detected = False
                        try:
                            # Look for reCAPTCHA
                            driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']")
                            if driver.find_elements(By.CSS_SELECTOR, "iframe[src*='recaptcha']"):
                                another_captcha_detected = True
                                print(f"[BOT {bot_id}] 🔐 ANOTHER reCAPTCHA detected after first solve!")
                        except:
                            pass
                        
                        if another_captcha_detected:
                            # Reset and wait for second CAPTCHA solve
                            print(f"[BOT {bot_id}] ⏸️  Waiting for user to solve SECOND CAPTCHA...")
                            spotify_bots_status[bot_id] = "⏸️ Another CAPTCHA detected - Waiting for manual solve"
                            captcha_submissions[bot_id] = False
                            
                            # Wait for second CAPTCHA (max 5 minutes)
                            second_captcha_solved = False
                            second_wait_time = 0
                            while second_wait_time < 300:
                                time.sleep(1)
                                second_wait_time += 1
                                
                                if captcha_submissions.get(bot_id, False):
                                    print(f"[BOT {bot_id}] ✓ User solved second CAPTCHA!")
                                    second_captcha_solved = True
                                    break
                            
                            if second_captcha_solved:
                                print(f"[BOT {bot_id}] ✓ Second CAPTCHA solved!")
                                time.sleep(2)
                                account = {'email': email, 'password': password, 'username': username, 'created': datetime.now().isoformat()}
                                spotify_accounts.append(json.dumps(account))
                                save_accounts()
                                spotify_bots_status[bot_id] = f"✓ Success: {email[:15]}..."
                                
                                with spotify_lock:
                                    spotify_job_status[job_id]['accounts'].append(account)
                                
                                if bot_id in captcha_submissions:
                                    del captcha_submissions[bot_id]
                            else:
                                spotify_bots_status[bot_id] = "✗ Second CAPTCHA timeout"
                                print(f"[BOT {bot_id}] ✗ Second CAPTCHA not solved within 5 minutes")
                                if bot_id in captcha_submissions:
                                    del captcha_submissions[bot_id]
                        else:
                            # No second CAPTCHA - account created successfully!
                            print(f"[BOT {bot_id}] ✓ No additional CAPTCHAs - Account creation successful!")
                            time.sleep(1)
                            account = {'email': email, 'password': password, 'username': username, 'created': datetime.now().isoformat()}
                            spotify_accounts.append(json.dumps(account))
                            save_accounts()
                            spotify_bots_status[bot_id] = f"✓ Success: {email[:15]}..."
                            
                            with spotify_lock:
                                spotify_job_status[job_id]['accounts'].append(account)
                            
                            if bot_id in captcha_submissions:
                                del captcha_submissions[bot_id]
                    else:
                        spotify_bots_status[bot_id] = "✗ CAPTCHA timeout (5 minutes exceeded)"
                        print(f"[BOT {bot_id}] ✗ CAPTCHA not solved within 5 minutes")
                        if bot_id in captcha_submissions:
                            del captcha_submissions[bot_id]
                else:
                    # No CAPTCHA - success!
                    account = {'email': email, 'password': password, 'username': username, 'created': datetime.now().isoformat()}
                    spotify_accounts.append(json.dumps(account))
                    save_accounts()
                    spotify_bots_status[bot_id] = f"✓ Success: {email[:15]}..."
                    
                    with spotify_lock:
                        spotify_job_status[job_id]['accounts'].append(account)
                
                with spotify_lock:
                    spotify_job_status[job_id]['created'] += 1
                    spotify_job_status[job_id]['current_account'] = email
                    spotify_job_status[job_id]['current_bot_id'] = bot_id
                
            except Exception as e:
                err_msg = str(e)[:35]
                spotify_bots_status[bot_id] = f"✗ {err_msg}"
                with spotify_lock:
                    if job_id in spotify_job_status:
                        spotify_job_status[job_id]['created'] += 1
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                if bot_id in spotify_bot_drivers:
                    del spotify_bot_drivers[bot_id]
        
        with spotify_lock:
            if job_id in spotify_job_status:
                spotify_job_status[job_id]['status'] = 'complete'
    
    thread = threading.Thread(target=create_worker, daemon=True)
    thread.start()
    
    return jsonify({'job_id': job_id, 'message': 'Account creation started'})

@spotify_bp.route('/api/auto-signup', methods=['POST'])
def auto_signup():
    """Auto signup mode - creates accounts continuously, restarts on CAPTCHA or timeout"""
    job_id = f"auto_signup_{datetime.now().timestamp()}"
    
    with spotify_lock:
        spotify_job_status[job_id] = {
            'total': 999999,
            'created': 0,
            'status': 'running',
            'current_account': '',
            'accounts': []
        }
    
    auto_signup_active = {'running': True}
    
    def auto_worker():
        bot_id = 0  # Always use bot_id = 0 for single sequential account creation
        last_success_time = time.time()
        timeout_seconds = 20
        
        while auto_signup_active['running']:
            # Check timeout - if stuck for >20s, restart
            current_time = time.time()
            if current_time - last_success_time > timeout_seconds:
                print(f"[AUTO] ⏱️ Timeout ({timeout_seconds}s) - restarting attempt")
                spotify_bots_status[bot_id] = "⏱️ Timeout - restarting..."
                if bot_id in spotify_bot_drivers:
                    try:
                        spotify_bot_drivers[bot_id].quit()
                    except:
                        pass
                    del spotify_bot_drivers[bot_id]
                last_success_time = time.time()
                continue
            
            driver = None
            try:
                email = generate_email()
                password = generate_password()
                username = generate_username()
                day, month, year = random_birthday()
                gender = random_gender()
                
                spotify_bots_status[bot_id] = "🔄 Launching..."
                driver = launch_spotify_browser()
                spotify_bot_drivers[bot_id] = driver
                wait = WebDriverWait(driver, 10)
                
                # Navigate and fill form
                driver.get("https://www.spotify.com/signup")
                time.sleep(0.3)
                
                try:
                    cookie_wait = WebDriverWait(driver, 2)
                    cookie_btn = cookie_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='accept-cookies']")))
                    cookie_btn.click()
                except:
                    pass
                
                # Email
                email_field = wait.until(EC.presence_of_element_located((By.NAME, "username")))
                email_field.send_keys(email)
                time.sleep(0.1)
                if not click_span_button_with_text(driver, wait, "Next"):
                    email_field.send_keys(Keys.ENTER)
                time.sleep(0.1)
                
                # Password
                password_field = wait.until(EC.presence_of_element_located((By.NAME, "new-password")))
                password_field.send_keys(password)
                time.sleep(0.1)
                if not click_span_button_with_text(driver, wait, "Next"):
                    password_field.send_keys(Keys.ENTER)
                time.sleep(0.1)
                
                # Name
                name_field = wait.until(EC.presence_of_element_located((By.ID, "displayName")))
                name_field.send_keys(username)
                time.sleep(0.1)
                if not click_span_button_with_text(driver, wait, "Next"):
                    name_field.send_keys(Keys.ENTER)
                time.sleep(0.1)
                
                # Birthday
                try:
                    day_field = wait.until(EC.presence_of_element_located((By.ID, "day")))
                    day_field.clear()
                    day_field.send_keys(day)
                    time.sleep(0.2)
                    
                    # Month - multiple fallback strategies
                    month_selected = False
                    try:
                        month_select = Select(driver.find_element(By.ID, "month"))
                        month_select.select_by_value(month)
                        month_selected = True
                        time.sleep(0.3)
                    except:
                        try:
                            month_select = Select(driver.find_element(By.NAME, "month"))
                            month_select.select_by_value(month)
                            month_selected = True
                            time.sleep(0.3)
                        except:
                            try:
                                month_names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                                month_idx = int(month) - 1
                                month_select = Select(driver.find_element(By.ID, "month"))
                                month_select.select_by_visible_text(month_names[month_idx])
                                month_selected = True
                                time.sleep(0.3)
                            except:
                                pass
                    
                    year_field = driver.find_element(By.ID, "year")
                    year_field.clear()
                    year_field.send_keys(year)
                    time.sleep(0.5)
                    
                    if not click_span_button_with_text(driver, wait, "Next"):
                        year_field.send_keys(Keys.ENTER)
                    time.sleep(1)
                except Exception as e:
                    print(f"[AUTO] Birthday error: {str(e)[:40]}")
                    pass
                
                # Gender (same logic as normal bots)
                spotify_bots_status[bot_id] = "⚙️  Gender..."
                try:
                    # Try finding all radio inputs and click by value
                    gender_element = None
                    
                    # Strategy 1: Find radio with value matching gender
                    gender_short = "m" if gender == "male" else "f"
                    try:
                        radios = driver.find_elements(By.CSS_SELECTOR, "input[type='radio']")
                        for radio in radios:
                            radio_val = radio.get_attribute("value")
                            if radio_val == gender_short or radio_val == gender or gender.lower() in (radio_val or "").lower():
                                gender_element = radio
                                break
                    except:
                        pass
                    
                    # Strategy 2: Try gender labels with short form
                    if not gender_element:
                        try:
                            gender_element = driver.find_element(By.CSS_SELECTOR, f"label[for='gender_option_{gender_short}']")
                        except:
                            pass
                    
                    # Strategy 3: Try full gender name in labels
                    if not gender_element:
                        try:
                            gender_element = driver.find_element(By.CSS_SELECTOR, f"label[for*='{gender}']")
                        except:
                            pass
                    
                    # Strategy 4: Search all labels for male/female text
                    if not gender_element:
                        try:
                            labels = driver.find_elements(By.TAG_NAME, "label")
                            for label in labels:
                                label_html = (label.get_attribute("outerHTML") or "").lower()
                                if gender.lower() in label_html:
                                    gender_element = label
                                    break
                        except:
                            pass
                    
                    if gender_element:
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", gender_element)
                        time.sleep(0.2)
                        try:
                            gender_element.click()
                        except:
                            driver.execute_script("arguments[0].click();", gender_element)
                    
                    time.sleep(0.3)
                    # Try clicking Next button first (like username/password)
                    if not click_span_button_with_text(driver, wait, "Next"):
                        # If Next button click fails, try pressing Enter on the gender element
                        try:
                            if gender_element:
                                gender_element.send_keys(Keys.ENTER)
                        except:
                            pass
                    time.sleep(0.5)
                    
                    # Accept terms
                    try:
                        terms_checkbox = driver.find_element(By.CSS_SELECTOR, "input[name='terms']")
                        if not terms_checkbox.is_selected():
                            terms_checkbox.click()
                        time.sleep(1)
                    except:
                        pass
                    
                    # Press Sign up button after gender
                    spotify_bots_status[bot_id] = "📤 Signing up..."
                    try:
                        signup_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign up')]/.. | //button[contains(text(), 'Sign up')]")))
                        driver.execute_script("arguments[0].click();", signup_button)
                        print(f"[AUTO] ✅ Clicked Sign up button")
                    except:
                        print(f"[AUTO] ⚠️ Could not click Sign up button after gender")
                except Exception as e:
                    print(f"[AUTO] ⚠️ Gender issue: {str(e)[:50]}")
                    try:
                        click_span_button_with_text(driver, wait, "Next")
                        time.sleep(3)
                    except:
                        pass
                
                # Final submit - Sign up button
                spotify_bots_status[bot_id] = "📤 Creating account..."
                try:
                    # Find Sign up button and make sure it's visible
                    signup_button = wait.until(EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign up')]/..")))
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", signup_button)
                    time.sleep(1)
                    signup_button.click()
                except:
                    # Fallback to helper function
                    click_span_button_with_text(driver, wait, "Sign up")
                time.sleep(8)
                
                # Check for reCAPTCHA iframe (same logic as manual signup)
                captcha_detected = False
                captcha_type = None
                
                try:
                    recaptcha_frames = driver.find_elements(By.TAG_NAME, "iframe")
                    for frame in recaptcha_frames:
                        try:
                            src = (frame.get_attribute("src") or "").lower()
                            if "recaptcha" in src or "challenge" in src:
                                captcha_detected = True
                                captcha_type = "reCAPTCHA"
                                print(f"[AUTO] 🔐 reCAPTCHA iframe detected")
                                time.sleep(2)
                                
                                # Try to click the reCAPTCHA checkbox
                                try:
                                    driver.switch_to.frame(frame)
                                    recaptcha_checkbox = driver.find_element(By.CLASS_NAME, "recaptcha-checkbox-border")
                                    recaptcha_checkbox.click()
                                    print(f"[AUTO] ✓ Clicked reCAPTCHA checkbox")
                                    time.sleep(3)
                                    driver.switch_to.default_content()
                                except Exception as rc_err:
                                    driver.switch_to.default_content()
                                    print(f"[AUTO] Failed to click checkbox: {str(rc_err)[:30]}")
                                break
                        except:
                            pass
                except:
                    pass
                
                # Check for generic CAPTCHA input field
                if not captcha_detected:
                    try:
                        driver.find_element(By.CSS_SELECTOR, "input[name='captcha']")
                        captcha_detected = True
                        captcha_type = "Generic"
                        print(f"[AUTO] 🔐 Generic CAPTCHA field detected")
                    except:
                        pass
                
                if captcha_detected:
                    print(f"[AUTO] 🔐 {captcha_type} detected - restarting (Total created: {spotify_job_status[job_id]['created']})")
                    spotify_bots_status[bot_id] = "🔄 CAPTCHA found - restarting..."
                    if driver:
                        driver.quit()
                    if bot_id in spotify_bot_drivers:
                        del spotify_bot_drivers[bot_id]
                    time.sleep(1)
                    last_success_time = time.time()
                    continue
                
                # Wait for account creation confirmation
                time.sleep(3)
                
                # Verify account was actually created by checking for success page/redirect
                try:
                    current_url = driver.current_url.lower()
                    # Check if we're on a success/dashboard page (not signup page)
                    if "signup" in current_url:
                        print(f"[AUTO] ✗ Still on signup page - account creation failed")
                        continue
                except:
                    pass
                
                # Account created successfully
                print(f"[AUTO] ✅ Account created: {email[:20]}")
                account = {'email': email, 'password': password, 'username': username, 'created': datetime.now().isoformat()}
                spotify_accounts.append(json.dumps(account))
                save_accounts()
                
                with spotify_lock:
                    spotify_job_status[job_id]['accounts'].append(account)
                    spotify_job_status[job_id]['created'] += 1
                    spotify_job_status[job_id]['current_account'] = email
                
                spotify_bots_status[bot_id] = f"✓ Created: {email[:15]}"
                last_success_time = time.time()  # Reset timeout on success
                
            except Exception as e:
                err_msg = str(e)[:30]
                print(f"[AUTO] Error: {err_msg}")
                spotify_bots_status[bot_id] = f"✗ {err_msg}"
            
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                if bot_id in spotify_bot_drivers:
                    del spotify_bot_drivers[bot_id]
                
                time.sleep(0.5)
    
    thread = threading.Thread(target=auto_worker, daemon=True)
    thread.start()
    
    return jsonify({'job_id': job_id, 'message': 'Auto signup started'})

@spotify_bp.route('/api/captcha-solved', methods=['POST'])
def captcha_solved():
    """Press Continue button on Spotify page after user solves CAPTCHA"""
    try:
        data = request.json or {}
        bot_id = data.get('bot_id')
        
        print(f"[API] captcha-solved called - pressing Continue button for bot {bot_id}")
        
        if bot_id is None:
            return jsonify({'success': False, 'error': 'No bot_id provided'}), 400
        
        bot_id = int(bot_id)
        
        if bot_id not in spotify_bot_drivers:
            print(f"[BOT {bot_id}] ⚠️ Bot not active")
            captcha_submissions[bot_id] = True
            return jsonify({'success': True, 'message': 'Continue pressed'}), 200
        
        driver = spotify_bot_drivers[bot_id]
        
        try:
            # Press Continue button on Spotify page (not inside iframe)
            wait = WebDriverWait(driver, 5)
            driver.switch_to.default_content()
            
            # Try to find and click Continue button
            try:
                continue_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Continue')] | //span[contains(text(), 'Continue')]/.. | //button[contains(., 'Continue')]")))
                driver.execute_script("arguments[0].click();", continue_btn)
                print(f"[BOT {bot_id}] ✅ Clicked Continue button")
            except:
                print(f"[BOT {bot_id}] ⚠️ Could not find Continue button, proceeding anyway")
            
        except Exception as e:
            print(f"[BOT {bot_id}] Error pressing Continue: {str(e)[:40]}")
        
        captcha_submissions[bot_id] = True
        print(f"[BOT {bot_id}] ✅ CAPTCHA solved - Continue pressed")
        return jsonify({'success': True, 'message': 'Continue pressed'}), 200
        
    except Exception as e:
        print(f"[API] Error: {str(e)[:50]}")
        return jsonify({'success': True, 'message': 'Continue pressed'}), 200

@spotify_bp.route('/api/captcha-press-continue', methods=['POST'])
def captcha_press_continue():
    """Auto-press continue button after manual CAPTCHA solve"""
    try:
        data = request.json or {}
        bot_id = int(data.get('bot_id', -1))
        
        if bot_id < 0 or bot_id not in spotify_bot_drivers:
            return jsonify({'success': False, 'error': 'Bot not found'}), 404
        
        driver = spotify_bot_drivers[bot_id]
        
        try:
            # Find and click the continue/submit button
            continue_strategies = [
                (By.XPATH, "//button[contains(text(), 'Continue')]", "text=Continue"),
                (By.XPATH, "//button[contains(text(), 'Next')]", "text=Next"),
                (By.XPATH, "//button[@type='submit']", "type=submit"),
                (By.XPATH, "//span[contains(text(), 'Continue')]/..", "span=Continue"),
                (By.CLASS_NAME, "submit-button", "class=submit"),
            ]
            
            for locator, xpath, desc in continue_strategies:
                try:
                    if locator == By.XPATH:
                        button = driver.find_element(locator, xpath)
                    else:
                        button = driver.find_element(locator, xpath)
                    
                    driver.execute_script("arguments[0].click();", button)
                    print(f"[API] ✓ Pressed continue button ({desc}) for Bot #{bot_id}")
                    return jsonify({'success': True, 'message': f'Continue button pressed for Bot #{bot_id}'})
                except:
                    pass
            
            print(f"[API] Could not find continue button for Bot #{bot_id}")
            return jsonify({'success': False, 'error': 'Continue button not found'})
        except Exception as e:
            print(f"[API] Error pressing continue: {str(e)[:50]}")
            return jsonify({'success': False, 'error': str(e)[:30]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)[:50]})

@spotify_bp.route('/api/captcha-click', methods=['POST'])
def captcha_click():
    """Handle reCAPTCHA v2 image puzzle clicks by switching to iframe and clicking inside"""
    try:
        data = request.get_json() or {}
        bot_id = int(data.get('bot_id', -1))
        x = int(data.get('x', 0))
        y = int(data.get('y', 0))
        
        if bot_id < 0:
            return jsonify({'success': False, 'error': 'No bot_id provided'}), 400
        
        if bot_id not in spotify_bot_drivers:
            return jsonify({'success': False, 'error': f'Bot {bot_id} not found'}), 404
        
        driver = spotify_bot_drivers[bot_id]
        print(f"[BOT {bot_id}] 🖱️  Click at ({x}, {y})")
        
        # Method 1: Find reCAPTCHA iframe and click element inside it
        try:
            # Get all iframes
            iframes = driver.find_elements(By.TAG_NAME, 'iframe')
            print(f"[BOT {bot_id}] Found {len(iframes)} iframes")
            
            for idx in range(len(iframes)):
                try:
                    # Refresh iframe list each iteration to avoid stale references
                    iframes = driver.find_elements(By.TAG_NAME, 'iframe')
                    if idx >= len(iframes):
                        print(f"[BOT {bot_id}] Iframe {idx} no longer exists")
                        continue
                    
                    iframe = iframes[idx]
                    
                    # Get iframe position and size
                    iframe_location = iframe.location
                    iframe_size = iframe.size
                    
                    # Check if click coordinates are inside this iframe
                    if (iframe_location['x'] <= x <= iframe_location['x'] + iframe_size['width'] and
                        iframe_location['y'] <= y <= iframe_location['y'] + iframe_size['height']):
                        
                        print(f"[BOT {bot_id}] Click is inside iframe {idx}")
                        
                        # Calculate relative coordinates inside the iframe
                        rel_x = x - iframe_location['x']
                        rel_y = y - iframe_location['y']
                        print(f"[BOT {bot_id}] Relative coords: ({rel_x}, {rel_y})")
                        
                        # Switch to this iframe by index (more stable than WebElement)
                        driver.switch_to.frame(idx)
                        
                        # Try to find element at those relative coordinates inside iframe
                        try:
                            result = driver.execute_script(f"""
                                var elem = document.elementFromPoint({rel_x}, {rel_y});
                                if (elem) {{
                                    console.log('Element in iframe:', elem.tagName, elem.className);
                                    elem.click();
                                    return {{'success': true, 'element': elem.tagName + '.' + elem.className}};
                                }}
                                return {{'success': false}};
                            """)
                            
                            driver.switch_to.default_content()
                            
                            if result.get('success'):
                                print(f"[BOT {bot_id}] ✅ Successfully clicked inside iframe: {result.get('element')}")
                                time.sleep(0.3)
                                return jsonify({'success': True, 'clicked': True, 'x': x, 'y': y, 'method': f'iframe {idx} inside'})
                        except Exception as e:
                            try:
                                driver.switch_to.default_content()
                            except:
                                pass
                            print(f"[BOT {bot_id}] Click inside iframe failed: {str(e)[:30]}")
                
                except Exception as iframe_err:
                    try:
                        driver.switch_to.default_content()
                    except:
                        pass
                    print(f"[BOT {bot_id}] Iframe {idx} error: {str(iframe_err)[:30]}")
                    continue
            
            print(f"[BOT {bot_id}] No suitable iframe found for click")
        except Exception as e1:
            print(f"[BOT {bot_id}] Iframe method failed: {str(e1)[:50]}")
            try:
                driver.switch_to.default_content()
            except:
                pass
        
        # Method 2: Fall back to Selenium ActionChains
        try:
            print(f"[BOT {bot_id}] Fallback: Using ActionChains...")
            window_size = driver.get_window_size()
            actions = ActionChains(driver)
            body = driver.find_element(By.TAG_NAME, 'body')
            
            offset_x = x - (window_size['width'] // 2)
            offset_y = y - (window_size['height'] // 2)
            
            actions.move_to_element_with_offset(body, offset_x, offset_y)
            actions.click()
            actions.perform()
            time.sleep(0.3)
            
            print(f"[BOT {bot_id}] ✅ ActionChains click performed")
            return jsonify({'success': True, 'clicked': True, 'x': x, 'y': y, 'method': 'ActionChains fallback'})
        except Exception as e2:
            print(f"[BOT {bot_id}] ActionChains failed: {str(e2)[:50]}")
            return jsonify({'success': False, 'error': 'Click failed'})
            
    except Exception as e:
        print(f"[API] Error in captcha_click: {str(e)[:50]}")
        return jsonify({'success': False, 'error': str(e)[:50]})

@spotify_bp.route('/api/account-progress', methods=['GET'])
def account_progress():
    """Get account creation progress"""
    job_id = request.args.get('job_id')
    
    with spotify_lock:
        if job_id not in spotify_job_status:
            return jsonify({'error': 'Job not found'}), 404
        
        job = spotify_job_status[job_id]
        progress = int((job['created'] / job['total']) * 100) if job['total'] > 0 else 0
        
        return jsonify({
            'job_id': job_id,
            'total': job['total'],
            'created': job['created'],
            'status': job['status'],
            'progress': progress,
            'current_account': job['current_account'],
            'current_bot_id': job.get('current_bot_id'),
            'accounts': job['accounts']
        })

@spotify_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get all created accounts"""
    load_accounts()
    accounts = []
    for account_str in spotify_accounts:
        try:
            accounts.append(json.loads(account_str))
        except:
            pass
    return jsonify({'accounts': accounts, 'total': len(accounts)})

@spotify_bp.route('/api/bot-screenshot/<int:bot_id>', methods=['GET'])
def get_bot_screenshot(bot_id):
    """Get live bot screenshot - full screen"""
    try:
        if bot_id in spotify_bot_drivers:
            driver = spotify_bot_drivers[bot_id]
            screenshot = capture_screenshot(driver, crop_to_captcha=False)
            status = spotify_bots_status.get(bot_id, "Processing...")
            return jsonify({'screenshot': screenshot, 'status': status})
        else:
            status = spotify_bots_status.get(bot_id, "Inactive")
            return jsonify({'screenshot': None, 'status': status})
    except:
        return jsonify({'screenshot': None, 'status': 'Error'}), 500

@spotify_bp.route('/api/captcha-screenshot/<int:bot_id>', methods=['GET'])
def get_captcha_screenshot(bot_id):
    """Get cropped CAPTCHA screenshot only"""
    try:
        if bot_id in spotify_bot_drivers:
            driver = spotify_bot_drivers[bot_id]
            screenshot = capture_screenshot(driver, crop_to_captcha=True)
            status = spotify_bots_status.get(bot_id, "Processing...")
            return jsonify({'screenshot': screenshot, 'status': status})
        else:
            status = spotify_bots_status.get(bot_id, "Inactive")
            return jsonify({'screenshot': None, 'status': status})
    except:
        return jsonify({'screenshot': None, 'status': 'Error'}), 500

@spotify_bp.route('/api/bot-status', methods=['GET'])
def bot_status():
    """Get all active bots status"""
    return jsonify(spotify_bots_status)

@spotify_bp.route('/api/download-accounts', methods=['GET'])
def download_accounts():
    """Download accounts as text file"""
    content = '\n'.join(spotify_accounts)
    return jsonify({'content': content})

@spotify_bp.route('/api/clear-accounts', methods=['POST'])
def clear_accounts():
    """Clear all accounts"""
    global spotify_accounts
    spotify_accounts = []
    if os.path.exists(account_file):
        os.remove(account_file)
    return jsonify({'message': 'All accounts cleared'})

@spotify_bp.route('/api/start-follower', methods=['POST'])
def start_follower():
    """Start following a target account with created accounts"""
    data = request.get_json() or {}
    target_url = data.get('target_url', '').strip()
    follow_count = int(data.get('follow_count', 1))
    
    if not target_url:
        return jsonify({'error': 'Target URL required'}), 400
    
    job_id = f"follower_{int(time.time())}_{random.randint(1000, 9999)}"
    
    with spotify_lock:
        follower_job_status[job_id] = {
            'status': 'starting',
            'target_url': target_url,
            'follow_count': follow_count,
            'accounts_used': 0,
            'success_count': 0,
            'failed_count': 0
        }
    
    threading.Thread(target=follower_worker, args=(job_id, target_url, follow_count), daemon=True).start()
    
    return jsonify({'job_id': job_id, 'message': f'Started following {target_url}'})

def follower_worker(job_id, target_url, follow_count):
    """Worker thread to follow target account with created accounts"""
    load_accounts()
    
    # Parse target URL to get username
    try:
        if 'spotify.com/user/' in target_url:
            target_username = target_url.split('spotify.com/user/')[-1].split('?')[0].split('/')[0]
        else:
            target_username = target_url.strip('/')
    except:
        with spotify_lock:
            follower_job_status[job_id]['status'] = 'error'
        return
    
    if not spotify_accounts:
        with spotify_lock:
            follower_job_status[job_id]['status'] = 'no_accounts'
        return
    
    with spotify_lock:
        follower_job_status[job_id]['status'] = 'running'
    
    success = 0
    failed = 0
    accounts_used = 0
    
    for account_str in spotify_accounts[:follow_count]:
        try:
            account_data = json.loads(account_str)
            email = account_data.get('email')
            password = account_data.get('password')
            
            if not email or not password:
                failed += 1
                continue
            
            accounts_used += 1
            
            with spotify_lock:
                follower_job_status[job_id]['status'] = f'Following with {email}...'
                follower_job_status[job_id]['accounts_used'] = accounts_used
            
            driver = None
            try:
                driver = launch_spotify_browser()
                wait = WebDriverWait(driver, 10)
                
                # Navigate to Spotify
                driver.get("https://www.spotify.com/login")
                time.sleep(1)
                
                # Click email field and login
                try:
                    # Multiple strategies for finding email field
                    email_strategies = [
                        (By.ID, "login-username"),
                        (By.NAME, "username"),
                        (By.CSS_SELECTOR, "input[type='email']"),
                        (By.CSS_SELECTOR, "input[placeholder*='Email']"),
                    ]
                    
                    email_field = None
                    for by_type, locator in email_strategies:
                        try:
                            email_field = wait.until(EC.presence_of_element_located((by_type, locator)))
                            break
                        except:
                            pass
                    
                    if not email_field:
                        raise Exception("Email field not found")
                    
                    email_field.send_keys(email)
                    time.sleep(0.3)
                    
                    # Multiple strategies for password field
                    password_strategies = [
                        (By.ID, "login-password"),
                        (By.NAME, "password"),
                        (By.CSS_SELECTOR, "input[type='password']"),
                    ]
                    
                    password_field = None
                    for by_type, locator in password_strategies:
                        try:
                            password_field = driver.find_element(by_type, locator)
                            break
                        except:
                            pass
                    
                    if not password_field:
                        raise Exception("Password field not found")
                    
                    password_field.send_keys(password)
                    time.sleep(0.3)
                    
                    # Find and click login button
                    login_strategies = [
                        (By.ID, "login-button"),
                        (By.XPATH, "//button[contains(text(), 'Log in')]"),
                        (By.XPATH, "//button[contains(., 'Log')]"),
                        (By.CSS_SELECTOR, "button[type='submit']"),
                    ]
                    
                    for by_type, locator in login_strategies:
                        try:
                            login_btn = driver.find_element(by_type, locator)
                            login_btn.click()
                            break
                        except:
                            pass
                    
                    time.sleep(5)
                except Exception as e:
                    print(f"[FOLLOWER] Login error for {email}: {str(e)[:30]}")
                    failed += 1
                    continue
                
                # Navigate to target account
                target_profile_url = f"https://open.spotify.com/user/{target_username}"
                driver.get(target_profile_url)
                time.sleep(3)
                
                # Find and click follow button
                try:
                    follow_buttons = driver.find_elements(By.XPATH, "//button[contains(., 'Follow')]")
                    if follow_buttons:
                        follow_buttons[0].click()
                        print(f"[FOLLOWER] ✓ {email} followed {target_username}")
                        success += 1
                        with spotify_lock:
                            follower_job_status[job_id]['success_count'] = success
                    else:
                        print(f"[FOLLOWER] No follow button found for {email}")
                        failed += 1
                except Exception as e:
                    print(f"[FOLLOWER] Follow error for {email}: {str(e)[:30]}")
                    failed += 1
                
                time.sleep(1)
                
            except Exception as e:
                print(f"[FOLLOWER] Browser error for {email}: {str(e)[:30]}")
                failed += 1
            finally:
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
        
        except Exception as e:
            print(f"[FOLLOWER] Account parsing error: {str(e)[:30]}")
            failed += 1
    
    with spotify_lock:
        follower_job_status[job_id]['status'] = 'complete'
        follower_job_status[job_id]['success_count'] = success
        follower_job_status[job_id]['failed_count'] = failed
        follower_job_status[job_id]['accounts_used'] = accounts_used
    
    print(f"[FOLLOWER] Job {job_id} complete: {success} success, {failed} failed")

@spotify_bp.route('/api/follower-status/<job_id>', methods=['GET'])
def follower_status(job_id):
    """Get follower job status"""
    with spotify_lock:
        if job_id not in follower_job_status:
            return jsonify({'error': 'Job not found'}), 404
        return jsonify(follower_job_status[job_id])
