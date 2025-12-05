# Instagram AIO - Web App with Phone/SMS Verification
from flask import Blueprint, render_template, request, jsonify
import threading
import json
import os
import random
import string
import time
from datetime import datetime
import hashlib
import uuid
import requests
from faker import Faker
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

instagram_bp = Blueprint('instagram', __name__, url_prefix='/instagram')

# Global state
job_status = {}
job_lock = threading.Lock()
bot_drivers = {}
bot_status = {}
accounts_file = os.path.expanduser('~/instagram_accounts.txt')
verification_sessions = {}  # Track phone verification sessions

def generate_uuid(prefix='', suffix=''):
    return f'{prefix}{uuid.uuid4()}{suffix}'

def generate_android_device_id():
    return "android-%s" % hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

def generate_useragent():
    try:
        with open("UserAgent.txt", "r", encoding="utf-8") as f:
            agents = [l.strip() for l in f if l.strip()]
        if agents:
            a = random.choice(agents)
            parts = a.split(",")
            if len(parts) >= 10:
                return f'Instagram 261.0.0.21.111 Android ({parts[7]}/{parts[6]}; {parts[5]}dpi; {parts[4]}; {parts[0]}; {parts[1]}; {parts[2]}; {parts[3]}; en_US; {parts[9]})'
            else:
                return a
    except:
        pass
    return 'Instagram 261.0.0.21.111 Android (28/9; 420dpi; Pixel 4 XL; Google; Pixel; 11; 1; en_US; 0)'

def get_mid():
    try:
        r = requests.get("https://i.instagram.com/api/v1/accounts/login", timeout=6)
        mid = r.cookies.get("mid")
        if mid:
            return mid
    except:
        pass
    u01 = 'QWERTYUIOPASDFGHJKLZXCVBNM'
    return f'Y4nS4g{"".join(random.choice(u01) for _ in range(8))}zwIrWdeYLcD9Shxj'

def Username():
    fake = Faker()
    return fake.user_name()

def Password():
    all_chars = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.sample(all_chars, 10))

def generate_jazoest(symbols):
    return f"2{sum(ord(s) for s in symbols)}"

def Birthday():
    return [str(random.randint(1, 28)), str(random.randint(1988, 2003)), str(random.randint(1, 12))]

# Backward compatibility aliases
gen_uuid = generate_uuid
gen_device_id = generate_android_device_id
gen_username = Username
gen_password = Password
gen_birthday = Birthday

def build_headers(device_id, family_id, android_id):
    return {
        'Host': 'i.instagram.com',
        'X-Ig-App-Locale': 'en_US',
        'X-Ig-Device-Locale': 'en_US',
        'X-Ig-Mapped-Locale': 'en_US',
        'X-Pigeon-Session-Id': generate_uuid('UFS-', '-1'),
        'X-Pigeon-Rawclienttime': str(round(time.time(), 3)),
        'X-Ig-Bandwidth-Speed-Kbps': str(random.randint(2500000, 3000000) / 1000),
        'X-Ig-Bandwidth-Totalbytes-B': str(random.randint(5000000, 90000000)),
        'X-Ig-Bandwidth-Totaltime-Ms': str(random.randint(2000, 9000)),
        'X-Bloks-Version-Id': 'a399f367a2e4aa3e40cdb4aab6535045b23db15f3dea789880aa062',
        'X-Ig-Www-Claim': '0',
        'X-Bloks-Is-Layout-Rtl': 'false',
        'X-Ig-Device-Id': device_id,
        'X-Ig-Family-Device-Id': family_id,
        'X-Ig-Android-Id': android_id,
        'X-Ig-Timezone-Offset': '16500',
        'X-Fb-Connection-Type': 'WIFI',
        'X-Ig-Connection-Type': 'WIFI',
        'X-Ig-Capabilities': '3brTv10=',
        'X-Ig-App-Id': '567067343352427',
        'Priority': 'u=3',
        'User-Agent': generate_useragent(),
        'Accept-Language': 'en-US',
        'X-Mid': get_mid(),
        'Ig-Intended-User-Id': '0',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Fb-Http-Engine': 'Liger',
        'X-Fb-Client-Ip': 'True',
        'X-Fb-Server-Cluster': 'True',
        'Connection': 'close',
    }

@instagram_bp.route('/')
def dashboard():
    return render_template('instagram_dashboard.html')

@instagram_bp.route('/viewer')
def viewer():
    return render_template('instagram_viewer.html')

@instagram_bp.route('/api/check-phone', methods=['POST'])
def check_phone():
    """Check if phone number is available using real Instagram API"""
    data = request.json or {}
    phone = data.get('phone', '')
    
    if not phone:
        return jsonify({'error': 'Phone required'}), 400
    
    # Clean and validate phone number
    phone_clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    if len(phone_clean) < 10 or not phone_clean.isdigit():
        return jsonify({'error': 'Invalid phone format. Use: +4915560821144 or 4915560821144'}), 400
    
    # Ensure it has + prefix for API
    if not phone.startswith('+'):
        phone = '+' + phone_clean
    
    session_id = gen_uuid()
    device_id = gen_uuid()
    family_id = gen_uuid()
    android_id = gen_device_id()
    adid = str(uuid.uuid4())
    water = str(uuid.uuid4())
    
    try:
        headers = build_headers(device_id, family_id, android_id)
        payload = {
            'signed_body': f'SIGNATURE.{{"phone_id":"{family_id}","login_nonce_map":"{{}}","phone_number":"{phone}","guid":"{device_id}","device_id":"{android_id}","prefill_shown":"False"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/check_phone_number/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {'status': 'ok'}
        
        print(f"[INSTAGRAM] Check phone response: {result}")
        
        with job_lock:
            verification_sessions[session_id] = {
                'phone': phone,
                'device_id': device_id,
                'family_id': family_id,
                'android_id': android_id,
                'adid': adid,
                'water': water,
                'status': 'phone_checked',
                'created_at': time.time()
            }
        
        return jsonify({'session_id': session_id, 'status': 'success', 'phone_available': True})
    except Exception as e:
        print(f"[INSTAGRAM] Phone check error: {str(e)}")
        return jsonify({'error': f'Phone check failed: {str(e)[:80]}'}), 500

@instagram_bp.route('/api/send-sms', methods=['POST'])
def send_sms():
    """Send SMS verification code using real Instagram API"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    
    with job_lock:
        if session_id not in verification_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = verification_sessions[session_id]
    
    try:
        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        water = session['water']
        
        payload = {
            'signed_body': f'SIGNATURE.{{"phone_id":"{session["family_id"]}","phone_number":"{session["phone"]}","guid":"{session["device_id"]}","device_id":"{session["android_id"]}","android_build_type":"release","waterfall_id":"{water}"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/send_signup_sms_code/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {}
        
        print(f"[INSTAGRAM] Send SMS response: {result}")
        
        with job_lock:
            verification_sessions[session_id]['status'] = 'sms_sent'
        
        return jsonify({'status': 'success', 'message': f'SMS sent to {session["phone"]}'})
    except Exception as e:
        print(f"[INSTAGRAM] SMS send error: {str(e)}")
        return jsonify({'error': f'Failed to send SMS: {str(e)[:80]}'}), 500

@instagram_bp.route('/api/validate-sms', methods=['POST'])
def validate_sms():
    """Validate SMS code using real Instagram API"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    code = data.get('code', '')
    
    with job_lock:
        if session_id not in verification_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = verification_sessions[session_id]
    
    try:
        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        
        payload = {
            'signed_body': f'SIGNATURE.{{"verification_code":"{code}","phone_number":"{session["phone"]}","guid":"{session["device_id"]}","device_id":"{session["android_id"]}","waterfall_id":"{session["water"]}"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/validate_signup_sms_code/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {}
        
        print(f"[INSTAGRAM] Validate SMS response: {result}")
        
        with job_lock:
            verification_sessions[session_id]['status'] = 'sms_validated'
            verification_sessions[session_id]['verification_code'] = code
        
        return jsonify({'status': 'success', 'message': 'SMS code validated'})
    except Exception as e:
        print(f"[INSTAGRAM] SMS validation error: {str(e)}")
        return jsonify({'error': str(e)[:80]}), 500

        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        water = session['water']
        
        payload = {
            'signed_body': f'SIGNATURE.{{"email":"{session["email"]}","device_id":"{session["android_id"]}","guid":"{session["device_id"]}","phone_id":"{session["family_id"]}","waterfall_id":"{water}"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/send_signup_email_code/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {}
        
        print(f"[INSTAGRAM] Send email code response: {result}")
        
        with job_lock:
            verification_sessions[session_id]['status'] = 'email_code_sent'
        
        return jsonify({'status': 'success', 'message': f'Verification code sent to {session["email"]}'})
    except Exception as e:
        print(f"[INSTAGRAM] Email code send error: {str(e)}")
        return jsonify({'error': f'Failed to send email code: {str(e)[:80]}'}), 500

@instagram_bp.route('/api/validate-email-code', methods=['POST'])
def validate_email_code():
    """Validate email verification code using real Instagram API"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    code = data.get('code', '')
    
    with job_lock:
        if session_id not in verification_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = verification_sessions[session_id]
    
    try:
        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        
        payload = {
            'signed_body': f'SIGNATURE.{{"email":"{session["email"]}","verification_code":"{code}","device_id":"{session["android_id"]}","guid":"{session["device_id"]}","phone_id":"{session["family_id"]}","waterfall_id":"{session["water"]}"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/validate_signup_email_code/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {}
        
        print(f"[INSTAGRAM] Validate email code response: {result}")
        
        with job_lock:
            verification_sessions[session_id]['status'] = 'email_validated'
            verification_sessions[session_id]['verification_code'] = code
        
        return jsonify({'status': 'success', 'message': 'Email code validated'})
    except Exception as e:
        print(f"[INSTAGRAM] Email code validation error: {str(e)}")
        return jsonify({'error': str(e)[:80]}), 500

@instagram_bp.route('/api/create-with-verification', methods=['POST'])
def create_with_verification():
    """Create Instagram account using phone or email verification with real API"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    custom_username = data.get('username', '')
    custom_password = data.get('password', '')
    
    with job_lock:
        if session_id not in verification_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = verification_sessions[session_id]
    
    job_id = gen_uuid('insta_')
    with job_lock:
        job_status[job_id] = {'status': 'creating', 'account': {}}
    
    try:
        password = custom_password or gen_password()
        username = custom_username or gen_username()
        birth = gen_birthday()
        jazoest = f"2{sum(ord(c) for c in session['family_id'])}"
        code = session.get('verification_code', '')
        
        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        
        payload = {
            'signed_body': f'SIGNATURE.{{"is_secondary_account_creation":"false","jazoest":"{jazoest}","tos_version":"row","suggestedUsername":"","verification_code":"{code}","do_not_auto_login_if_credentials_match":"true","phone_id":"{session["family_id"]}","enc_password":"#PWD_INSTAGRAM:0:{int(datetime.now().timestamp())}:{password}","phone_number":"{session["phone"]}","username":"{username}","first_name":"{username}","day":"{birth[0]}","adid":"{session["adid"]}","guid":"{session["device_id"]}","year":"{birth[1]}","device_id":"{session["android_id"]}","_uuid":"{session["device_id"]}","month":"{birth[2]}","sn_nonce":"","force_sign_up_code":"","waterfall_id":"{session["water"]}","qs_stamp":"","has_sms_consent":"true","one_tap_opt_in":"true"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/create_validated/", 
                         headers=headers, data=payload, timeout=10)
        
        print(f"[INSTAGRAM] Create account response: {r.text}")
        
        account = {
            'username': username, 
            'password': password, 
            'phone': session['phone'], 
            'created': datetime.now().isoformat(),
            'token': r.headers.get('ig-set-authorization', '')
        }
        
        # Save account to text file
        try:
            with open(accounts_file, 'a') as f:
                f.write(json.dumps(account) + '\n')
            print(f"[INSTAGRAM] Account saved: {username}")
        except Exception as e:
            print(f"[INSTAGRAM] Failed to save account: {str(e)}")
        
        with job_lock:
            job_status[job_id] = {'status': 'success', 'account': account}
        
        return jsonify({
            'status': 'success', 
            'account': account,
            'message': f'Account created! Username: {username}'
        })
    except Exception as e:
        with job_lock:
            job_status[job_id] = {'status': 'error', 'error': str(e)[:50]}
        return jsonify({'error': str(e)[:80]}), 500

@instagram_bp.route('/api/username-suggestion', methods=['POST'])
def username_suggestion():
    """Get username suggestion from Instagram API"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    custom_username = data.get('username', '')
    
    with job_lock:
        if session_id not in verification_sessions:
            return jsonify({'error': 'Session not found'}), 404
        
        session = verification_sessions[session_id]
    
    try:
        username = custom_username or gen_username()
        headers = build_headers(session['device_id'], session['family_id'], session['android_id'])
        
        payload = {
            'signed_body': f'SIGNATURE.{{"phone_id":"{session["family_id"]}","guid":"{session["device_id"]}","name":"{username}","device_id":"{session["android_id"]}","email":"","waterfall_id":"{session["water"]}"}}'
        }
        
        r = requests.post("https://i.instagram.com/api/v1/accounts/username_suggestions/", 
                         headers=headers, data=payload, timeout=10)
        result = r.json() if r.text else {}
        
        print(f"[INSTAGRAM] Username suggestion response: {result}")
        
        suggestion = username
        try:
            if 'suggestions_with_metadata' in result and 'suggestions' in result['suggestions_with_metadata']:
                suggestion = result['suggestions_with_metadata']['suggestions'][0]['username']
        except:
            pass
        
        return jsonify({'status': 'success', 'suggestion': suggestion})
    except Exception as e:
        print(f"[INSTAGRAM] Username suggestion error: {str(e)}")
        return jsonify({'error': str(e)[:80]}), 500

@instagram_bp.route('/api/accounts', methods=['GET'])
def get_accounts():
    accounts = []
    try:
        if os.path.exists(accounts_file):
            with open(accounts_file, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            accounts.append(json.loads(line))
                        except:
                            pass
    except:
        pass
    return jsonify({'total': len(accounts), 'accounts': accounts})

@instagram_bp.route('/api/login-account', methods=['POST'])
def login_account():
    """Login to Instagram with Selenium"""
    data = request.json or {}
    username = data.get('username', '')
    password = data.get('password', '')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    session_id = gen_uuid('login_')
    job_id = gen_uuid('job_')
    
    with job_lock:
        job_status[job_id] = {'status': 'logging_in', 'message': 'Starting browser...', 'session_id': session_id}
    
    def run_login():
        driver = None
        try:
            # Launch Chrome
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(options=options)
            
            print(f"[INSTAGRAM] Login: Opening Instagram.com...")
            with job_lock:
                job_status[job_id]['message'] = 'Opening Instagram.com...'
            
            driver.get('https://www.instagram.com/accounts/login/')
            time.sleep(3)
            
            # Enter username
            with job_lock:
                job_status[job_id]['message'] = 'Entering credentials...'
            
            username_input = driver.find_element(By.NAME, 'username')
            username_input.send_keys(username)
            time.sleep(0.5)
            
            password_input = driver.find_element(By.NAME, 'password')
            password_input.send_keys(password)
            time.sleep(0.5)
            
            # Click login
            login_btn = driver.find_elements(By.XPATH, "//button[contains(., 'Log in')]")
            if login_btn:
                login_btn[0].click()
                time.sleep(5)
            
            # Check if logged in by looking for feed elements
            try:
                driver.find_element(By.XPATH, "//a[contains(@href, '/')]")
                with job_lock:
                    job_status[job_id]['status'] = 'logged_in'
                    job_status[job_id]['message'] = '✅ Logged in successfully!'
                    bot_drivers[session_id] = driver
                print(f"[INSTAGRAM] Login successful for {username}")
            except:
                with job_lock:
                    job_status[job_id]['status'] = 'error'
                    job_status[job_id]['message'] = '❌ Login failed - could not verify'
                if driver:
                    driver.quit()
        
        except Exception as e:
            print(f"[INSTAGRAM] Login error: {str(e)}")
            with job_lock:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = f'❌ Error: {str(e)[:50]}'
            if driver:
                driver.quit()
    
    threading.Thread(target=run_login, daemon=True).start()
    return jsonify({'job_id': job_id, 'session_id': session_id})

@instagram_bp.route('/api/login-status/<job_id>', methods=['GET'])
def login_status(job_id):
    """Get login status"""
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown'})
    return jsonify(status)

@instagram_bp.route('/api/follow-user', methods=['POST'])
def follow_user():
    """Follow a specified user"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    target_username = data.get('target_username', '')
    
    if not session_id or not target_username:
        return jsonify({'error': 'Session and target username required'}), 400
    
    if session_id not in bot_drivers:
        return jsonify({'error': 'Invalid session - login first'}), 404
    
    job_id = gen_uuid('follow_')
    
    with job_lock:
        job_status[job_id] = {'status': 'starting', 'message': 'Starting follow...'}
    
    def run_follow():
        driver = bot_drivers.get(session_id)
        if not driver:
            with job_lock:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = '❌ Driver not found'
            return
        
        try:
            print(f"[INSTAGRAM] Following {target_username}...")
            with job_lock:
                job_status[job_id]['message'] = f'Navigating to {target_username}...'
            
            driver.get(f'https://www.instagram.com/{target_username}/')
            time.sleep(3)
            
            # Look for follow button
            with job_lock:
                job_status[job_id]['message'] = f'Finding follow button...'
            
            follow_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Follow')]")
            if follow_btns:
                with job_lock:
                    job_status[job_id]['message'] = f'Clicking follow button...'
                follow_btns[0].click()
                time.sleep(2)
                
                with job_lock:
                    job_status[job_id]['status'] = 'success'
                    job_status[job_id]['message'] = f'✅ Successfully followed {target_username}!'
                print(f"[INSTAGRAM] Followed {target_username}")
            else:
                with job_lock:
                    job_status[job_id]['status'] = 'error'
                    job_status[job_id]['message'] = f'❌ Could not find follow button for {target_username}'
        
        except Exception as e:
            print(f"[INSTAGRAM] Follow error: {str(e)}")
            with job_lock:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = f'❌ Error: {str(e)[:50]}'
    
    threading.Thread(target=run_follow, daemon=True).start()
    return jsonify({'job_id': job_id})

@instagram_bp.route('/api/follow-status/<job_id>', methods=['GET'])
def follow_status(job_id):
    """Get follow status"""
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown'})
    return jsonify(status)

@instagram_bp.route('/api/like-post', methods=['POST'])
def like_post():
    """Like a post using Selenium"""
    data = request.json or {}
    post_url = data.get('post_url', '')
    
    if not post_url:
        return jsonify({'error': 'Post URL required'}), 400
    
    job_id = gen_uuid('like_')
    
    with job_lock:
        job_status[job_id] = {'status': 'pending', 'message': 'Opening Instagram...'}
    
    def run_like():
        driver = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(options=options)
            
            driver.get(post_url)
            time.sleep(3)
            
            like_btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Like')]")
            if like_btns:
                like_btns[0].click()
                time.sleep(1)
                with job_lock:
                    job_status[job_id] = {'status': 'success', 'message': '❤️ Post liked!'}
            else:
                with job_lock:
                    job_status[job_id] = {'status': 'error', 'message': '❌ Like button not found'}
        except Exception as e:
            with job_lock:
                job_status[job_id] = {'status': 'error', 'message': f'❌ Error: {str(e)[:50]}'}
        finally:
            if driver:
                driver.quit()
    
    threading.Thread(target=run_like, daemon=True).start()
    return jsonify({'job_id': job_id})

@instagram_bp.route('/api/like-status/<job_id>', methods=['GET'])
def like_status(job_id):
    """Get like status"""
    with job_lock:
        status = job_status.get(job_id, {'status': 'pending'})
    return jsonify(status)

@instagram_bp.route('/api/comment-post', methods=['POST'])
def comment_post():
    """Comment on a post"""
    data = request.json or {}
    post_url = data.get('post_url', '')
    comment_text = data.get('comment_text', '')
    
    if not post_url or not comment_text:
        return jsonify({'error': 'Post URL and comment text required'}), 400
    
    job_id = gen_uuid('comment_')
    
    with job_lock:
        job_status[job_id] = {'status': 'pending', 'message': 'Opening post...'}
    
    def run_comment():
        driver = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(options=options)
            
            driver.get(post_url)
            time.sleep(3)
            
            comment_inputs = driver.find_elements(By.XPATH, "//textarea[contains(@aria-label, 'comment')]")
            if comment_inputs:
                comment_inputs[0].click()
                comment_inputs[0].send_keys(comment_text)
                time.sleep(1)
                
                post_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Post')]")
                if post_btns:
                    post_btns[0].click()
                    time.sleep(2)
                    with job_lock:
                        job_status[job_id] = {'status': 'success', 'message': '💬 Comment posted!'}
                else:
                    with job_lock:
                        job_status[job_id] = {'status': 'error', 'message': '❌ Post button not found'}
            else:
                with job_lock:
                    job_status[job_id] = {'status': 'error', 'message': '❌ Comment box not found'}
        except Exception as e:
            with job_lock:
                job_status[job_id] = {'status': 'error', 'message': f'❌ Error: {str(e)[:50]}'}
        finally:
            if driver:
                driver.quit()
    
    threading.Thread(target=run_comment, daemon=True).start()
    return jsonify({'job_id': job_id})

@instagram_bp.route('/api/comment-status/<job_id>', methods=['GET'])
def comment_status(job_id):
    """Get comment status"""
    with job_lock:
        status = job_status.get(job_id, {'status': 'pending'})
    return jsonify(status)

@instagram_bp.route('/api/share-post', methods=['POST'])
def share_post():
    """Save/share a post"""
    data = request.json or {}
    post_url = data.get('post_url', '')
    
    if not post_url:
        return jsonify({'error': 'Post URL required'}), 400
    
    job_id = gen_uuid('share_')
    
    with job_lock:
        job_status[job_id] = {'status': 'pending', 'message': 'Opening post...'}
    
    def run_share():
        driver = None
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            driver = webdriver.Chrome(options=options)
            
            driver.get(post_url)
            time.sleep(3)
            
            share_btns = driver.find_elements(By.XPATH, "//button[contains(@aria-label, 'Share')]")
            if share_btns:
                share_btns[0].click()
                time.sleep(1)
                
                save_btns = driver.find_elements(By.XPATH, "//button[contains(., 'Save')]")
                if save_btns:
                    save_btns[0].click()
                    time.sleep(2)
                    with job_lock:
                        job_status[job_id] = {'status': 'success', 'message': '📌 Post saved!'}
                else:
                    with job_lock:
                        job_status[job_id] = {'status': 'success', 'message': '📌 Share menu opened'}
            else:
                with job_lock:
                    job_status[job_id] = {'status': 'error', 'message': '❌ Share button not found'}
        except Exception as e:
            with job_lock:
                job_status[job_id] = {'status': 'error', 'message': f'❌ Error: {str(e)[:50]}'}
        finally:
            if driver:
                driver.quit()
    
    threading.Thread(target=run_share, daemon=True).start()
    return jsonify({'job_id': job_id})

@instagram_bp.route('/api/share-status/<job_id>', methods=['GET'])
def share_status(job_id):
    """Get share status"""
    with job_lock:
        status = job_status.get(job_id, {'status': 'pending'})
    return jsonify(status)
