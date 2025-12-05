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
from selenium.webdriver.common.action_chains import ActionChains
import io

roblox_bp = Blueprint('roblox', __name__, url_prefix='/roblox')

capsolver.api_key = os.environ.get('CAPSOLVER_API_KEY', '')

job_lock = threading.Lock()
job_status = {}
active_drivers = {}
screenshot_buffer = {}

ACCEPT_ALL = '//button[contains(@class, "btn-cta-lg") and contains(@class, "cookie-btn")]'
SIGNUP_BUTTON = '//*[@id="signup-button"]'
USERNAME_BOX = '//*[@id="signup-username"]'
PASSWORD_BOX = '//*[@id="signup-password"]'
MONTH_DROPDOWN = '//*[@id="MonthDropdown"]'
DAY_DROPDOWN = '//*[@id="DayDropdown"]'
YEAR_DROPDOWN = '//*[@id="YearDropdown"]'
MALE_GENDER = "//button[@id='MaleButton']"
FEMALE_GENDER = "//button[@id='FemaleButton']"
ARKOSE_IFRAME = "arkose-iframe"

ROBLOX_FUNCAPTCHA_PUBLICKEY = "A2A14B1D-1AF3-C791-9BBC-EE33CC7A0A6F"

def gen_uuid():
    return str(uuid.uuid4())

def gen_username():
    strategy = random.randint(1, 8)
    
    if strategy == 1:
        words = ['Pro', 'Epic', 'Cool', 'Fast', 'Dark', 'Fire', 'Ice', 'Sky', 'Sun', 'Star']
        return f"{random.choice(words)}{random.randint(1000, 9999)}"
    elif strategy == 2:
        first = ['Wolf', 'Tiger', 'Eagle', 'Hawk', 'Fox', 'Bear', 'Lion', 'Shark']
        return f"{random.choice(first)}{random.randint(100, 999)}"
    elif strategy == 3:
        adj = ['Swift', 'Bold', 'Brave', 'Fierce', 'Sharp', 'Quick', 'Sly']
        noun = ['Wolf', 'Fox', 'Hawk', 'Bear', 'Ace', 'Pro']
        return f"{random.choice(adj)}{random.choice(noun)}{random.randint(10, 99)}"
    elif strategy == 4:
        return f"Player{random.randint(10000, 99999)}"
    elif strategy == 5:
        prefix = random.choice(['x', 'X', 'z', 'Z', 'v', 'V'])
        return f"{prefix}{random.randint(100, 999)}Pro{random.randint(10, 99)}"
    elif strategy == 6:
        words = ['Gamer', 'Ninja', 'Hero', 'Boss', 'King', 'Pro', 'Ace']
        return f"{random.choice(words)}{random.randint(1000, 9999)}"
    elif strategy == 7:
        return ''.join(random.choices(string.ascii_letters + string.digits, k=random.randint(8, 15)))
    else:
        first = ['Dark', 'Ice', 'Fire', 'Sky', 'Neo', 'Max', 'Top']
        last = ['Wolf', 'Fox', 'Pro', 'Ace', 'King', 'Boss']
        return f"{random.choice(first)}{random.choice(last)}{random.randint(10, 999)}"

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%"
    return ''.join(random.choice(chars) for _ in range(12))

def create_driver():
    options = uc.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--incognito')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--headless=new')
    options.add_argument('log-level=3')
    
    driver = uc.Chrome(options=options)
    return driver

def click_button(driver, xpath, move=False, timeout=20):
    try:
        button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, xpath))
        )
    except:
        button = driver.find_element(By.XPATH, xpath)
    
    if move:
        actions = ActionChains(driver)
        actions.move_to_element(button)
        actions.click().perform()
        actions.reset_actions()
    else:
        button.click()
    
    return button

def select_dropdown(driver, xpath, min_val, max_val):
    index = random.randint(min_val, max_val)
    option_xpath = f"{xpath}/option[{index}]"
    
    dropdown = WebDriverWait(driver, 15).until(
        EC.element_to_be_clickable((By.XPATH, xpath))
    )
    dropdown.click()
    time.sleep(0.8)
    
    option = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, option_xpath))
    )
    option.click()
    time.sleep(0.8)

def enter_value(driver, xpath, text):
    textbox = click_button(driver, xpath)
    textbox.send_keys(Keys.CONTROL + "a")
    textbox.send_keys(Keys.BACKSPACE)
    time.sleep(0.3)
    textbox.send_keys(text)

def check_captcha(driver):
    try:
        driver.find_element(By.ID, ARKOSE_IFRAME)
        return True
    except:
        return False

def get_funcaptcha_publickey(driver):
    try:
        elem = driver.find_element(By.CSS_SELECTOR, '[data-pkey]')
        return elem.get_attribute('data-pkey')
    except:
        return ROBLOX_FUNCAPTCHA_PUBLICKEY

def solve_funcaptcha(website_url, public_key):
    """Solve FunCaptcha using CapSolver"""
    try:
        solution = capsolver.solve({
            "type": "FunCaptchaTaskProxyLess",
            "websiteURL": website_url,
            "websitePublicKey": public_key
        })
        return solution.get('token') or solution
    except Exception as e:
        return None

@roblox_bp.route('/')
def dashboard():
    return render_template('roblox_dashboard.html')

@roblox_bp.route('/api/create-account', methods=['POST'])
def create_account():
    data = request.json or {}
    custom_username = data.get('username', '')
    custom_password = data.get('password', '')
    
    job_id = gen_uuid()
    driver_id = gen_uuid()
    
    with job_lock:
        job_status[job_id] = {
            'status': 'starting',
            'message': '🔄 Launching undetected browser...',
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
            
            username = custom_username or gen_username()
            password = custom_password or gen_password()
            
            with job_lock:
                job_status[job_id]['username'] = username
                job_status[job_id]['password'] = password
            
            with job_lock:
                job_status[job_id]['message'] = '🎮 Opening Roblox...'
            driver.get('https://www.roblox.com')
            time.sleep(4)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '🍪 Accepting cookies...'
            try:
                click_button(driver, ACCEPT_ALL, move=True, timeout=5)
                time.sleep(1)
            except:
                pass
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '📅 Setting birthday (Month)...'
            try:
                select_dropdown(driver, MONTH_DROPDOWN, 1, 12)
            except:
                pass
            time.sleep(1)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '📅 Setting birthday (Day)...'
            try:
                select_dropdown(driver, DAY_DROPDOWN, 1, 20)
            except:
                pass
            time.sleep(1)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '📅 Setting birthday (Year)...'
            try:
                select_dropdown(driver, YEAR_DROPDOWN, 24, 37)
            except:
                pass
            time.sleep(1)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = f'👤 Username: {username}'
            try:
                enter_value(driver, USERNAME_BOX, username)
            except:
                pass
            time.sleep(1.5)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '🔐 Entering password...'
            try:
                enter_value(driver, PASSWORD_BOX, password)
            except:
                pass
            time.sleep(1)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '👥 Selecting gender...'
            gender = "Unknown"
            try:
                g = random.randint(1, 2)
                if g == 1:
                    click_button(driver, MALE_GENDER)
                    gender = "Male"
                else:
                    click_button(driver, FEMALE_GENDER)
                    gender = "Female"
            except:
                pass
            time.sleep(1)
            take_screenshot(driver_id)
            
            with job_lock:
                job_status[job_id]['message'] = '✅ Clicking signup...'
            try:
                click_button(driver, SIGNUP_BUTTON)
            except:
                pass
            time.sleep(3)
            take_screenshot(driver_id)
            
            captcha_detected = check_captcha(driver)
            
            if captcha_detected:
                with job_lock:
                    job_status[job_id]['message'] = '🤖 Solving FunCaptcha with CapSolver...'
                take_screenshot(driver_id)
                
                public_key = get_funcaptcha_publickey(driver)
                token = solve_funcaptcha(driver.current_url, public_key)
                
                if token:
                    with job_lock:
                        job_status[job_id]['message'] = '💉 Injecting captcha token...'
                    
                    try:
                        driver.execute_script(f"""
                            var fcToken = document.querySelector('[name="fc-token"]');
                            if (fcToken) fcToken.value = '{token}';
                            
                            var callback = window.ArkoseEnforcement && window.ArkoseEnforcement.setConfig;
                            if (callback) {{
                                try {{ callback({{ token: '{token}' }}); }} catch(e) {{}}
                            }}
                        """)
                        time.sleep(2)
                        
                        try:
                            click_button(driver, SIGNUP_BUTTON)
                        except:
                            pass
                        time.sleep(5)
                        take_screenshot(driver_id)
                        
                        current_url = driver.current_url
                        if 'home' in current_url.lower():
                            with job_lock:
                                job_status[job_id]['status'] = 'success'
                                job_status[job_id]['message'] = f'✅ Account created! {username}:{password} ({gender})'
                        else:
                            with job_lock:
                                job_status[job_id]['status'] = 'completed'
                                job_status[job_id]['message'] = f'⏳ Captcha solved, verifying... {username}:{password}'
                    except Exception as e:
                        with job_lock:
                            job_status[job_id]['status'] = 'error'
                            job_status[job_id]['message'] = f'❌ Token injection failed: {str(e)[:50]}'
                else:
                    with job_lock:
                        job_status[job_id]['status'] = 'captcha_failed'
                        job_status[job_id]['message'] = f'⚠️ CapSolver failed. {username}:{password}'
            else:
                current_url = driver.current_url
                if 'home' in current_url.lower():
                    with job_lock:
                        job_status[job_id]['status'] = 'success'
                        job_status[job_id]['message'] = f'✅ Account created! {username}:{password} ({gender})'
                else:
                    with job_lock:
                        job_status[job_id]['status'] = 'completed'
                        job_status[job_id]['message'] = f'⏳ Form submitted. {username}:{password} ({gender})'
            
            try:
                with open('roblox_accounts.txt', 'a') as f:
                    f.write(f"{username}:{password}\n")
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

@roblox_bp.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown', 'message': 'Job not found'})
    return jsonify(status)

@roblox_bp.route('/api/screenshot/<driver_id>', methods=['GET'])
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

@roblox_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = []
    try:
        with open('roblox_accounts.txt', 'r') as f:
            for line in f:
                if ':' in line:
                    parts = line.strip().split(':')
                    if len(parts) >= 2:
                        accounts.append({'username': parts[0], 'password': parts[1]})
    except:
        pass
    return jsonify(accounts)
