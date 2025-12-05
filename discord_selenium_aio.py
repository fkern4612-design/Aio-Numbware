from flask import Blueprint, render_template, request, jsonify, send_file
import threading
import uuid
import time
import random
import string
import os
import capsolver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import io

discord_bp = Blueprint('discord', __name__, url_prefix='/discord')

capsolver.api_key = os.environ.get('CAPSOLVER_API_KEY', '')

job_lock = threading.Lock()
job_status = {}
active_drivers = {}
screenshot_buffer = {}

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 
          'July', 'August', 'September', 'October', 'November', 'December']

DISCORD_HCAPTCHA_SITEKEY = "4c672d35-0701-42b2-88c3-78380b0db560"

def gen_uuid():
    return str(uuid.uuid4())

def gen_username():
    strategies = random.randint(1, 4)
    if strategies == 1:
        prefixes = ['dark', 'swift', 'sharp', 'fierce', 'silent', 'bright', 'cool', 'epic', 'cyber', 'mystic']
        animals = ['tiger', 'wolf', 'eagle', 'dragon', 'phoenix', 'ninja', 'warrior', 'raven', 'falcon']
        return f"{random.choice(prefixes)}{random.choice(animals)}{random.randint(100, 999)}"
    elif strategies == 2:
        return ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 12)))
    elif strategies == 3:
        prefixes = ['player', 'user', 'gamer', 'pro', 'elite', 'master']
        return f"{random.choice(prefixes)}{random.randint(1000, 9999)}"
    else:
        return f"{random.choice(string.ascii_lowercase)}{random.randint(100, 999)}{random.choice(string.ascii_lowercase)}{random.randint(10, 99)}"

def gen_display_name():
    strategies = random.randint(1, 4)
    if strategies == 1:
        adjectives = ['Cool', 'Epic', 'Swift', 'Dark', 'Bright', 'Silent', 'Fierce', 'Mystic']
        nouns = ['Tiger', 'Dragon', 'Phoenix', 'Wolf', 'Eagle', 'Ninja', 'Shadow', 'Knight']
        return f"{random.choice(adjectives)} {random.choice(nouns)}"
    elif strategies == 2:
        first_names = ['Alex', 'Sam', 'Jordan', 'Riley', 'Casey', 'Morgan', 'Taylor', 'Blake']
        return f"{random.choice(first_names)}{random.randint(10, 99)}"
    elif strategies == 3:
        return ''.join(random.choices(string.ascii_letters, k=random.randint(6, 10))).capitalize()
    else:
        words = ['Storm', 'Fire', 'Ice', 'Thunder', 'Shadow', 'Light', 'Crystal', 'Neon']
        return f"{random.choice(words)}{random.choice(words)}{random.randint(1, 99)}"

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(random.randint(12, 16)))

def gen_email():
    providers = ['gmail.com', 'outlook.com', 'yahoo.com', 'proton.me']
    name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 12)))
    return f"{name}@{random.choice(providers)}"

def set_input_value(driver, css_selector, value):
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
    )
    element.clear()
    element.send_keys(value)
    return element

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--headless=new")
    
    driver = uc.Chrome(options=options)
    return driver

def solve_hcaptcha(website_url, website_key):
    """Solve hCaptcha using CapSolver"""
    try:
        solution = capsolver.solve({
            "type": "HCaptchaTaskProxyLess",
            "websiteURL": website_url,
            "websiteKey": website_key
        })
        return solution.get('gRecaptchaResponse') or solution.get('token') or solution
    except Exception as e:
        return None

@discord_bp.route('/')
def dashboard():
    return render_template('discord_dashboard.html')

@discord_bp.route('/api/create-account', methods=['POST'])
def create_account():
    data = request.json or {}
    custom_email = data.get('email', '')
    custom_username = data.get('username', '')
    custom_password = data.get('password', '')
    
    job_id = gen_uuid()
    driver_id = gen_uuid()
    
    with job_lock:
        job_status[job_id] = {
            'status': 'starting',
            'message': '🚀 Launching undetected browser...',
            'email': None,
            'username': None,
            'password': None,
            'driver_id': driver_id
        }
    
    def run_create():
        driver = None
        try:
            with job_lock:
                job_status[job_id]['message'] = '🚀 Creating undetected Chrome...'
            
            driver = create_driver()
            
            with job_lock:
                active_drivers[driver_id] = driver
            
            email = custom_email or gen_email()
            username = custom_username or gen_username()
            password = custom_password or gen_password()
            display_name = gen_display_name()
            
            with job_lock:
                job_status[job_id]['email'] = email
                job_status[job_id]['username'] = username
                job_status[job_id]['password'] = password
            
            with job_lock:
                job_status[job_id]['message'] = '🌐 Opening Discord register...'
            driver.get('https://discord.com/register')
            time.sleep(3)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = f'✉️ Email: {email}'
            try:
                set_input_value(driver, 'input[name="email"]', email)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = f'📛 Display: {display_name}'
            try:
                set_input_value(driver, 'input[name="global_name"]', display_name)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = f'👤 Username: {username}'
            try:
                set_input_value(driver, 'input[name="username"]', username)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '🔐 Password...'
            try:
                set_input_value(driver, 'input[name="password"]', password)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '📅 Date of birth...'
            
            month = random.choice(MONTHS)
            day = str(random.randint(1, 28))
            year = str(random.randint(1990, 2002))
            
            try:
                month_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[id="react-select-2-input"]'))
                )
                month_input.send_keys(month)
                month_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except:
                pass
            
            try:
                day_input = driver.find_element(By.CSS_SELECTOR, '[id="react-select-3-input"]')
                day_input.send_keys(day)
                day_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except:
                pass
            
            try:
                year_input = driver.find_element(By.CSS_SELECTOR, '[id="react-select-4-input"]')
                year_input.send_keys(year)
                year_input.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '✅ Accepting terms...'
            try:
                tos_checkbox = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "[type='checkbox']"))
                )
                driver.execute_script("arguments[0].click();", tos_checkbox)
                time.sleep(0.5)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '⏳ Submitting form...'
            try:
                submit_btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, '[type="submit"]'))
                )
                submit_btn.click()
            except:
                pass
            time.sleep(3)
            take_screenshot(driver_id)
            
            captcha_detected = False
            hcaptcha_sitekey = DISCORD_HCAPTCHA_SITEKEY
            try:
                iframe = driver.find_element(By.CSS_SELECTOR, 'iframe[src*="hcaptcha"]')
                captcha_detected = True
                src = iframe.get_attribute('src') or ''
                if 'sitekey=' in src:
                    hcaptcha_sitekey = src.split('sitekey=')[1].split('&')[0]
            except:
                pass
            
            if captcha_detected:
                with job_lock:
                    job_status[job_id]['message'] = '🤖 Solving hCaptcha with CapSolver...'
                take_screenshot(driver_id)
                
                token = solve_hcaptcha(driver.current_url, hcaptcha_sitekey)
                
                if token:
                    with job_lock:
                        job_status[job_id]['message'] = '💉 Injecting captcha token...'
                    
                    try:
                        driver.execute_script(f"""
                            document.querySelector('[name="h-captcha-response"]').value = '{token}';
                            document.querySelector('[name="g-recaptcha-response"]').value = '{token}';
                        """)
                        time.sleep(1)
                        
                        try:
                            submit_btn = driver.find_element(By.CSS_SELECTOR, '[type="submit"]')
                            submit_btn.click()
                        except:
                            pass
                        time.sleep(3)
                        take_screenshot(driver_id)
                        
                        with job_lock:
                            job_status[job_id]['status'] = 'success'
                            job_status[job_id]['message'] = f'✅ Captcha solved! {email}:{username}:{password}'
                    except Exception as e:
                        with job_lock:
                            job_status[job_id]['status'] = 'error'
                            job_status[job_id]['message'] = f'❌ Token injection failed: {str(e)[:50]}'
                else:
                    with job_lock:
                        job_status[job_id]['status'] = 'captcha_failed'
                        job_status[job_id]['message'] = f'⚠️ CapSolver failed. {email}:{username}:{password}'
            else:
                with job_lock:
                    job_status[job_id]['status'] = 'completed'
                    job_status[job_id]['message'] = f'✅ Form submitted! {email}:{username}:{password}'
            
            try:
                with open('discord_accounts.txt', 'a') as f:
                    f.write(f"{email}:{username}:{password}\n")
            except:
                pass
            
        except Exception as e:
            with job_lock:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = f'❌ Error: {str(e)[:100]}'
        finally:
            time.sleep(3)
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            with job_lock:
                if driver_id in active_drivers:
                    del active_drivers[driver_id]
    
    threading.Thread(target=run_create, daemon=True).start()
    return jsonify({'job_id': job_id, 'driver_id': driver_id})

@discord_bp.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown', 'message': 'Job not found'})
    return jsonify(status)

@discord_bp.route('/api/screenshot/<driver_id>', methods=['GET'])
def get_screenshot(driver_id):
    with job_lock:
        if driver_id in screenshot_buffer:
            screenshot_data = screenshot_buffer[driver_id]
            return send_file(io.BytesIO(screenshot_data), mimetype='image/png', as_attachment=False)
    return jsonify({'error': 'No screenshot'}), 404

def take_screenshot(driver_id):
    try:
        driver = active_drivers.get(driver_id)
        if driver:
            screenshot = driver.get_screenshot_as_png()
            with job_lock:
                screenshot_buffer[driver_id] = screenshot
    except:
        pass

@discord_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = []
    try:
        with open('discord_accounts.txt', 'r') as f:
            for line in f:
                if ':' in line:
                    parts = line.strip().split(':')
                    if len(parts) >= 3:
                        accounts.append({'email': parts[0], 'username': parts[1], 'password': parts[2]})
    except:
        pass
    return jsonify(accounts)
