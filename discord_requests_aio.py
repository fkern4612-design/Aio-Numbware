from flask import Blueprint, render_template, request, jsonify
import threading
import uuid
import time
import random
import string
import requests
from datetime import datetime, timedelta

discord_bp = Blueprint('discord', __name__, url_prefix='/discord')

job_lock = threading.Lock()
job_status = {}

def gen_uuid():
    return str(uuid.uuid4())

def gen_username():
    """Discord usernames with variety"""
    strategies = random.randint(1, 3)
    if strategies == 1:
        prefixes = ['player', 'user', 'gamer', 'pro', 'elite', 'master', 'admin', 'phantom', 'mystic']
        return f"{random.choice(prefixes)}{random.randint(1000, 9999)}"
    elif strategies == 2:
        adjectives = ['dark', 'swift', 'sharp', 'fierce', 'silent', 'bright', 'cool', 'epic', 'cyber']
        animals = ['tiger', 'wolf', 'eagle', 'dragon', 'phoenix', 'ninja', 'warrior']
        return f"{random.choice(adjectives)}{random.choice(animals)}{random.randint(100, 999)}"
    else:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choices(chars, k=random.randint(8, 12)))

def gen_password():
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(random.randint(10, 16)))

def gen_email():
    """Generate unique Discord account emails with multiple providers"""
    providers = ['tempmail.com', 'temp-mail.org', 'guerrillamail.com', 'maildrop.cc', 'mailnesia.com']
    return f"user{random.randint(100000, 999999)}@{random.choice(providers)}"

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
    
    with job_lock:
        job_status[job_id] = {
            'status': 'running',
            'message': '🚀 Starting account creation...',
            'email': None,
            'username': None,
            'password': None
        }
    
    thread = threading.Thread(target=create_account_thread, args=(job_id, custom_email, custom_username, custom_password))
    thread.daemon = True
    thread.start()
    
    return jsonify({'job_id': job_id})

def create_account_thread(job_id, custom_email, custom_username, custom_password):
    try:
        email = custom_email if custom_email else gen_email()
        username = custom_username if custom_username else gen_username()
        password = custom_password if custom_password else gen_password()
        
        with job_lock:
            job_status[job_id]['message'] = f'✉️ Email: {email}'
        time.sleep(0.5)
        
        with job_lock:
            job_status[job_id]['message'] = f'👤 Username: {username}'
        time.sleep(0.5)
        
        with job_lock:
            job_status[job_id]['message'] = f'🔐 Password: {"*" * len(password)}'
        time.sleep(0.5)
        
        with job_lock:
            job_status[job_id]['message'] = f'📅 Birthday: Generating...'
        
        birth_day = random.randint(1, 28)
        birth_month = random.randint(1, 12)
        birth_year = random.randint(1990, 2001)
        
        with job_lock:
            job_status[job_id]['message'] = f'📅 Birthday: {birth_month:02d}/{birth_day:02d}/{birth_year}'
        time.sleep(0.5)
        
        with job_lock:
            job_status[job_id]['message'] = f'📤 Sending registration request...'
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        payload = {
            'email': email,
            'username': username,
            'password': password,
            'date_of_birth': f"{birth_year:04d}-{birth_month:02d}-{birth_day:02d}",
            'consent': {
                'personalization': True,
                'marketing': random.choice([True, False])
            },
            'captcha_key': None,
            'gift_code_sku_id': None
        }
        
        response = session.post(
            'https://discord.com/api/v9/auth/register',
            json=payload,
            timeout=10
        )
        
        with job_lock:
            if response.status_code == 201:
                job_status[job_id]['status'] = 'success'
                job_status[job_id]['message'] = f'✅ Account created!'
                job_status[job_id]['email'] = email
                job_status[job_id]['username'] = username
                job_status[job_id]['password'] = password
                
                try:
                    with open('discord_accounts.txt', 'a') as f:
                        f.write(f"{email}:{username}:{password}\n")
                except:
                    pass
            elif response.status_code == 400:
                error_msg = response.json().get('message', 'Invalid request')
                with job_lock:
                    job_status[job_id]['status'] = 'error'
                    job_status[job_id]['message'] = f'❌ {error_msg}'
            elif response.status_code == 429:
                with job_lock:
                    job_status[job_id]['status'] = 'error'
                    job_status[job_id]['message'] = '⏱️ Rate limited. Try again later.'
            else:
                with job_lock:
                    job_status[job_id]['status'] = 'error'
                    job_status[job_id]['message'] = f'❌ Error: {response.status_code}'
    
    except Exception as e:
        with job_lock:
            job_status[job_id]['status'] = 'error'
            job_status[job_id]['message'] = f'❌ Error: {str(e)[:50]}'

@discord_bp.route('/api/status/<job_id>', methods=['GET'])
def get_status(job_id):
    with job_lock:
        status = job_status.get(job_id, {'status': 'unknown', 'message': 'Job not found'})
    return jsonify(status)
