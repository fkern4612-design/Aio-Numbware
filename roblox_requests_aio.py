from flask import Blueprint, render_template, request, jsonify
import threading
import uuid
import time
import random
import string
import requests
from datetime import datetime, timedelta

roblox_bp = Blueprint('roblox', __name__, url_prefix='/roblox')

job_lock = threading.Lock()
job_status = {}

def gen_uuid():
    return str(uuid.uuid4())

def gen_username():
    prefixes = ['user', 'play', 'gamer', 'pro', 'max', 'star', 'ultra', 'sonic', 'legend', 'ninja']
    prefix = random.choice(prefixes)
    return f"{prefix}{random.randint(100000, 999999)}"

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(12))

@roblox_bp.route('/')
def dashboard():
    return render_template('roblox_dashboard.html')

@roblox_bp.route('/api/create-account', methods=['POST'])
def create_account():
    data = request.json or {}
    custom_username = data.get('username', '')
    custom_password = data.get('password', '')
    
    job_id = gen_uuid()
    
    with job_lock:
        job_status[job_id] = {
            'status': 'running',
            'message': '🚀 Starting account creation...',
            'username': None,
            'password': None
        }
    
    thread = threading.Thread(target=create_account_thread, args=(job_id, custom_username, custom_password))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id})

def create_account_thread(job_id, custom_username, custom_password):
    try:
        username = custom_username if custom_username else gen_username()
        password = custom_password if custom_password else gen_password()
        
        with job_lock:
            job_status[job_id]['message'] = f'🔐 Getting CSRF token...'
        
        csrf_token = get_csrf_token()
        if not csrf_token:
            with job_lock:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = '❌ Failed to get CSRF token'
            return
        
        with job_lock:
            job_status[job_id]['message'] = f'👤 Creating account: {username}...'
        
        birthday = (datetime.now() - timedelta(days=365*15)).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        gender = random.choice([1, 2])
        
        payload = {
            'username': username,
            'password': password,
            'birthday': birthday,
            'gender': gender,
            'isTosAgreementBoxChecked': True,
            'agreementIds': [
                '848d8d8f-0e33-4176-bcd9-aa4e22ae7905',
                '54d8a8f0-d9c8-4cf3-bd26-0cbf8af0bba3'
            ]
        }
        
        headers = {
            'x-csrf-token': csrf_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.post(
            'https://auth.roblox.com/v2/signup',
            headers=headers,
            json=payload,
            timeout=10
        )
        
        with job_lock:
            if response.status_code == 200:
                job_status[job_id]['status'] = 'success'
                job_status[job_id]['message'] = f'✅ Account created! {username}'
                job_status[job_id]['username'] = username
                job_status[job_id]['password'] = password
                
                try:
                    roblosecurity = response.cookies.get('.ROBLOSECURITY', '')
                    if roblosecurity:
                        with open('roblox_accounts.txt', 'a') as f:
                            f.write(f"{username}:{password}:{roblosecurity}\n")
                except:
                    pass
            elif response.status_code == 429:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = '⏱️ Rate limited. Try again later.'
            elif 'errors' in response.json():
                error = response.json()['errors'][0]['message'] if response.json()['errors'] else 'Unknown error'
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = f'❌ {error}'
            else:
                job_status[job_id]['status'] = 'error'
                job_status[job_id]['message'] = f'❌ Error: {response.status_code}'
    
    except Exception as e:
        with job_lock:
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['message'] = f'❌ Error: {str(e)[:50]}'

def get_csrf_token():
    try:
        response = requests.post(
            'https://catalog.roblox.com/v1/catalog/items/details',
            timeout=5
        )
        return response.headers.get('x-csrf-token', '')
    except:
        return None

@roblox_bp.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown', 'message': 'Job not found'})
    return jsonify(status)
