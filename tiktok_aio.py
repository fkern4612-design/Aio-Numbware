# TikTok AIO - Advanced Engagement Booster with Custom Backend
from flask import Blueprint, render_template, request, jsonify, send_file
import threading
import time
import os
import base64
from io import BytesIO
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from threading import Semaphore
from PIL import Image

tiktok_bp = Blueprint('tiktok', __name__, url_prefix='/tiktok')

job_status = {}
job_lock = threading.Lock()
browser_semaphore = Semaphore(1)
active_sessions = {}
stop_flags = {}  # Track stop flags for each session

# Import the services
from tiktok_services import get_service, VideoInfoFetcher, get_screenshot, ZefameService

def launch_browser():
    """Launch Chrome for Freer.in automation"""
    import random
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    ]
    selected_ua = random.choice(user_agents)
    
    options = webdriver.ChromeOptions()
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument(f'user-agent={selected_ua}')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    driver = webdriver.Chrome(options=options)
    return driver

@tiktok_bp.route('/')
def dashboard():
    return render_template('tiktok_dashboard.html')

@tiktok_bp.route('/api/get-video-info', methods=['POST'])
def get_video_info_endpoint():
    """Get current video stats (views, likes, shares)"""
    data = request.json or {}
    url = data.get('url', '')
    
    if not url:
        return jsonify({'error': 'No URL provided'})
    
    info = VideoInfoFetcher.get_video_info(url)
    return jsonify(info)

@tiktok_bp.route('/api/get-services', methods=['GET'])
def get_services():
    """Get available TikTok engagement services"""
    provider = request.args.get('provider', 'boost').lower()
    
    # All services use our custom backend
    services = ZefameService.get_available_services()
    
    if not services:
        return jsonify({'error': 'Could not fetch services'}), 500
    
    # Map service IDs to names
    service_names = {
        229: "TikTok Views",
        228: "TikTok Followers",
        232: "TikTok Likes",
        235: "TikTok Shares",
        236: "TikTok Favorites"
    }
    
    formatted = []
    for svc in services:
        sid = svc.get('id', 0)
        name = service_names.get(int(sid), svc.get('name', f'Service {sid}'))
        qty = svc.get('quantity', 0)
        timer = svc.get('timer', 'Unknown')
        available = svc.get('available', False)
        
        formatted.append({
            'id': sid,
            'name': name,
            'quantity': qty,
            'timer': timer,
            'available': available,
            'display': f"{name} - {qty} per {timer}" if available else f"{name} (UNAVAILABLE)"
        })
    
    return jsonify(formatted)

@tiktok_bp.route('/api/start-boost', methods=['POST'])
def start_boost():
    """Start endless boost with custom view range"""
    data = request.json or {}
    provider = data.get('provider', 'boost').lower()
    service_id = int(data.get('service_id', 229))
    url = data.get('url', '')
    min_views = int(data.get('min_views', 100))
    max_views = int(data.get('max_views', 500))
    session_id = f"session_{int(time.time())}"
    
    # Validate range
    if min_views > max_views:
        min_views, max_views = max_views, min_views
    if min_views < 10:
        min_views = 10
    if max_views > 100000:
        max_views = 100000
    
    # Create stop flag for this session
    stop_flags[session_id] = {'stop': False}
    
    with job_lock:
        job_status[session_id] = {
            'status': 'boosting',
            'message': '🚀 Initializing boost...',
            'service': provider,
            'progress': 0,
            'total_sent': 0
        }
    
    def run_boost():
        try:
            # Run boost with custom backend
            success, message = ZefameService.boost(url, service_id, session_id, stop_flags[session_id], job_status, job_lock, min_views, max_views)
            
            with job_lock:
                if success:
                    job_status[session_id]['status'] = 'stopped'
                    job_status[session_id]['message'] = message
                else:
                    job_status[session_id]['status'] = 'error'
                    job_status[session_id]['message'] = message
                job_status[session_id]['progress'] = 100
        except Exception as e:
            print(f"[BOOST] Error: {str(e)}")
            with job_lock:
                job_status[session_id]['status'] = 'error'
                job_status[session_id]['message'] = f'❌ Error: {str(e)[:80]}'
    
    threading.Thread(target=run_boost, daemon=True).start()
    return jsonify({'session_id': session_id})

@tiktok_bp.route('/api/stop-boost/<session_id>', methods=['POST'])
def stop_boost(session_id):
    """Stop the boost for a session"""
    if session_id in stop_flags:
        stop_flags[session_id]['stop'] = True
        print(f"[BOOST] Stop signal sent to {session_id}")
        return jsonify({'status': 'stopped'})
    return jsonify({'error': 'Session not found'}), 404

@tiktok_bp.route('/api/session-status/<session_id>', methods=['GET'])
def get_session_status(session_id):
    """Get current session status"""
    with job_lock:
        status = job_status.get(session_id, {'status': 'error', 'message': 'Session not found'})
    return jsonify(status)

@tiktok_bp.route('/api/session-screenshot/<session_id>', methods=['GET'])
def get_session_screenshot(session_id):
    """Get live screenshot from session (both Selenium and HTTP-based services)"""
    try:
        from tiktok_services import screenshots as service_screenshots
        
        # First try to get screenshot from tiktok_services (TikTool HTTP/Selenium)
        screenshot_data = service_screenshots.get(session_id)
        
        if screenshot_data:
            if isinstance(screenshot_data, bytes):
                return send_file(BytesIO(screenshot_data), mimetype='image/png')
            elif isinstance(screenshot_data, str):
                try:
                    img_data = base64.b64decode(screenshot_data)
                    return send_file(BytesIO(img_data), mimetype='image/png')
                except:
                    pass
            
            # Try converting PIL Image to bytes
            try:
                img_byte_arr = BytesIO()
                screenshot_data.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                return send_file(img_byte_arr, mimetype='image/png')
            except:
                pass
        
        # Try browser-based screenshot capture
        if session_id in active_sessions:
            try:
                driver = active_sessions[session_id]['driver']
                screenshot = driver.get_screenshot_as_png()
                return send_file(BytesIO(screenshot), mimetype='image/png')
            except:
                pass
        
        # Return placeholder
        from PIL import ImageDraw
        img = Image.new('RGB', (1920, 1080), color=(30, 30, 30))
        d = ImageDraw.Draw(img)
        d.text((960, 540), "Waiting for screenshot...", fill='white')
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return send_file(img_byte_arr, mimetype='image/png')
    except Exception as e:
        print(f"[SCREENSHOT] Error: {str(e)}")
        img = Image.new('RGB', (1920, 1080), color=(40, 40, 40))
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return send_file(img_byte_arr, mimetype='image/png')

@tiktok_bp.route('/api/start-session', methods=['POST'])
def start_session():
    """Start a new session and load captcha verification"""
    data = request.json or {}
    session_id = f"session_{int(time.time())}"
    
    with job_lock:
        job_status[session_id] = {
            'status': 'loading',
            'message': '🔄 Loading verification page...',
            'captcha_image': None
        }
    
    def load_verification():
        driver = None
        try:
            driver = launch_browser()
            active_sessions[session_id] = {'driver': driver, 'captcha': None}
            
            with job_lock:
                job_status[session_id]['message'] = '🌐 Connecting to Freer.in (bypassing Cloudflare)...'
            
            # Navigate to Freer.in - undetected Chrome handles Cloudflare automatically
            driver.get("https://freer.in")
            time.sleep(5)  # Wait for page to load
            
            with job_lock:
                job_status[session_id]['message'] = '🔐 Clicking Cloudflare checkbox...'
            
            # Try JavaScript injection first to handle Cloudflare
            try:
                driver.execute_script("""
                    // Try to find and click Cloudflare checkbox via JavaScript
                    try {
                        // Method 1: Direct querySelector
                        let checkbox = document.querySelector('[name="cf_challenge"] input[type="checkbox"]');
                        if (checkbox) checkbox.click();
                        
                        // Method 2: Find by class patterns
                        let elements = document.querySelectorAll('input[type="checkbox"]');
                        for (let el of elements) {
                            if (el.offsetParent !== null) {  // Visible element
                                el.click();
                                break;
                            }
                        }
                        
                        // Method 3: Look for iframes
                        let iframes = document.querySelectorAll('iframe');
                        for (let iframe of iframes) {
                            try {
                                let iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                                let iframeCheckbox = iframeDoc.querySelector('input[type="checkbox"]');
                                if (iframeCheckbox) iframeCheckbox.click();
                            } catch (e) {}
                        }
                    } catch (e) {}
                """)
                time.sleep(2)
            except:
                pass
            
            # Click Cloudflare checkbox using screen coordinates - AGGRESSIVE approach
            try:
                # Find checkboxes on page and click them
                checkboxes = driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                for checkbox in checkboxes:
                    try:
                        # Check if visible
                        if checkbox.is_displayed():
                            driver.execute_script("arguments[0].scrollIntoView(true);", checkbox)
                            time.sleep(0.3)
                            # Try clicking with JavaScript first
                            driver.execute_script("arguments[0].click();", checkbox)
                            time.sleep(0.5)
                            # If JS click fails, try ActionChains
                            try:
                                actions = ActionChains(driver)
                                actions.move_to_element(checkbox).click().perform()
                                time.sleep(0.5)
                            except:
                                pass
                    except:
                        pass
            except:
                pass
            
            # Try coordinate-based clicking on common Cloudflare checkbox positions
            try:
                positions = [
                    (60, 380), (70, 400), (50, 420), (80, 350), (100, 400), 
                    (40, 400), (70, 450), (90, 390), (50, 350), (100, 420),
                    (65, 385), (75, 395), (55, 415), (85, 355), (95, 405)
                ]
                
                for attempt in range(3):
                    for x, y in positions:
                        try:
                            actions = ActionChains(driver)
                            actions.move_by_offset(x, y).click().perform()
                            time.sleep(0.3)
                        except:
                            pass
                    time.sleep(1)
            except:
                pass
            
            time.sleep(8)  # Wait for Cloudflare to verify and process
            
            with job_lock:
                job_status[session_id]['message'] = '⏱️ Processing request...'
            
            # Extract verification information
            timer_text = "Timer not found"
            try:
                # Look for timer elements on page
                timer_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'sec') or contains(text(), 'min') or contains(text(), ':')]")
                if timer_elements:
                    for elem in timer_elements:
                        text = elem.text.strip()
                        if text and any(c.isdigit() for c in text):
                            timer_text = text
                            break
            except:
                pass
            
            with job_lock:
                job_status[session_id]['message'] = '📸 Capturing captcha...'
                job_status[session_id]['timer'] = timer_text
            
            # Find and capture captcha image
            captcha_img = None
            try:
                # Try multiple methods to find captcha
                captcha_element = None
                
                # Method 1: Look for img with captcha in alt/class
                try:
                    captcha_element = driver.find_element(By.XPATH, "//img[contains(@alt, 'captcha') or contains(@class, 'captcha')]")
                except:
                    pass
                
                # Method 2: Look for div containing image
                if not captcha_element:
                    try:
                        captcha_element = driver.find_element(By.XPATH, "//*[contains(@class, 'captcha-image') or contains(@id, 'captcha')]")
                    except:
                        pass
                
                # Method 3: Look for any visible image in the page
                if not captcha_element:
                    try:
                        images = driver.find_elements(By.TAG_NAME, "img")
                        if images:
                            # Get the largest visible image (likely the captcha)
                            captcha_element = images[0]
                    except:
                        pass
                
                if captcha_element:
                    captcha_img = captcha_element.screenshot_as_png
            except:
                pass
            
            # If no specific element found, take full page screenshot
            if not captcha_img:
                try:
                    screenshot = driver.get_screenshot_as_png()
                    img = Image.open(BytesIO(screenshot))
                    # Save full page as captcha display
                    captcha_bytes = BytesIO()
                    img.save(captcha_bytes, format='PNG')
                    captcha_img = captcha_bytes.getvalue()
                except:
                    pass
            
            if captcha_img:
                captcha_b64 = base64.b64encode(captcha_img).decode()
                with job_lock:
                    job_status[session_id]['captcha_image'] = captcha_b64
                    job_status[session_id]['status'] = 'captcha_ready'
                    job_status[session_id]['message'] = '✅ Ready - Solve the captcha'
            else:
                with job_lock:
                    job_status[session_id]['status'] = 'error'
                    job_status[session_id]['message'] = '❌ Could not load verification page'
                    
        except Exception as e:
            with job_lock:
                job_status[session_id]['status'] = 'error'
                job_status[session_id]['message'] = f'❌ Error: {str(e)[:50]}'
            print(f"[ZEFOY] Error: {str(e)}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    threading.Thread(target=load_verification, daemon=True).start()
    return jsonify({'session_id': session_id})

@tiktok_bp.route('/api/session-status/<session_id>', methods=['GET'])
def session_status(session_id):
    """Get session status with live screen"""
    with job_lock:
        if session_id not in job_status:
            return jsonify({'error': 'Session not found'}), 404
        status = job_status[session_id].copy()
        
        # Add screen data if available
        if session_id in active_sessions:
            try:
                driver = active_sessions[session_id]['driver']
                screenshot = driver.get_screenshot_as_png()
                screen_b64 = base64.b64encode(screenshot).decode()
                status['screen_data'] = screen_b64
            except:
                pass
        
        if status.get('cloudflare_image'):
            status['has_cloudflare'] = True
            del status['cloudflare_image']
        return jsonify(status)

@tiktok_bp.route('/api/cloudflare-image/<session_id>', methods=['GET'])
def get_cloudflare_image(session_id):
    """Get Cloudflare screenshot"""
    with job_lock:
        if session_id not in job_status or not job_status[session_id].get('cloudflare_image'):
            return jsonify({'error': 'No image'}), 404
        img = job_status[session_id]['cloudflare_image']
    return jsonify({'image': img})

@tiktok_bp.route('/api/click-cloudflare', methods=['POST'])
def click_cloudflare():
    """Handle manual Cloudflare click with scaled coordinates"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    x = data.get('x', 60)
    y = data.get('y', 380)
    
    # Click at the exact coordinates using pyautogui if available
    try:
        import subprocess
        # Use xdotool to click at absolute screen position (for server environment)
        subprocess.run(['xdotool', 'mousemove', str(x), str(y), 'click', '1'], timeout=2)
    except:
        # Fallback: just record for the bot to handle
        pass
    
    with job_lock:
        if session_id in job_status:
            job_status[session_id]['cloudflare_clicked'] = True
            job_status[session_id]['cloudflare_coords'] = {'x': x, 'y': y}
    return jsonify({'success': True})

@tiktok_bp.route('/api/submit-captcha', methods=['POST'])
def submit_captcha():
    """Submit captcha and start boost loop"""
    data = request.json or {}
    session_id = data.get('session_id', '')
    captcha = data.get('captcha', '').strip()
    tiktok_url = data.get('url', '').strip()
    boost_type = data.get('type', 'views')
    
    if not session_id or session_id not in active_sessions:
        return jsonify({'error': 'Invalid session'}), 400
    
    if not captcha or not tiktok_url:
        return jsonify({'error': 'Captcha and URL required'}), 400
    
    driver = active_sessions[session_id]['driver']
    
    with job_lock:
        job_status[session_id]['status'] = 'submitting'
        job_status[session_id]['message'] = '⌨️ Entering captcha...'
    
    def boost_loop():
        try:
            # Submit captcha - try multiple methods
            captcha_entered = False
            
            # Method 1: Find by various XPath patterns
            xpath_patterns = [
                "//input[@name='captcha']",
                "//input[@id*='captcha']",
                "//input[@placeholder*='captcha']",
                "//input[@type='text' and @placeholder*='answer']",
                "//input[@type='number']",
                "//input[contains(@class, 'captcha')]"
            ]
            
            for xpath in xpath_patterns:
                try:
                    captcha_input = driver.find_element(By.XPATH, xpath)
                    if captcha_input:
                        # Click to focus
                        driver.execute_script("arguments[0].click();", captcha_input)
                        time.sleep(0.3)
                        # Clear via JavaScript
                        driver.execute_script("arguments[0].value = '';", captcha_input)
                        time.sleep(0.2)
                        # Enter captcha using send_keys
                        captcha_input.send_keys(str(captcha))
                        time.sleep(0.3)
                        # Verify it was entered
                        value = driver.execute_script("return arguments[0].value;", captcha_input)
                        if str(value) == str(captcha):
                            captcha_entered = True
                            print(f"[FREER] Captcha entered successfully: {captcha}")
                            break
                except:
                    pass
            
            # Method 2: If normal input didn't work, try clicking all inputs and filling the one with focus
            if not captcha_entered:
                try:
                    inputs = driver.find_elements(By.TAG_NAME, "input")
                    for inp in inputs:
                        try:
                            if inp.is_displayed():
                                driver.execute_script("arguments[0].focus();", inp)
                                driver.execute_script("arguments[0].value = '';", inp)
                                inp.send_keys(str(captcha))
                                time.sleep(0.2)
                                value = driver.execute_script("return arguments[0].value;", inp)
                                if str(value) == str(captcha):
                                    captcha_entered = True
                                    break
                        except:
                            pass
                except:
                    pass
            
            time.sleep(0.5)
            
            # Click submit button for captcha
            with job_lock:
                job_status[session_id]['message'] = '🔘 Clicking send button...'
            
            try:
                submit_patterns = [
                    "//button[contains(text(), 'Send')]",
                    "//button[contains(text(), 'Submit')]",
                    "//button[contains(text(), 'Verify')]",
                    "//button[contains(text(), 'Boost')]",
                    "//button[@type='submit']"
                ]
                
                for pattern in submit_patterns:
                    try:
                        submit_btn = driver.find_element(By.XPATH, pattern)
                        driver.execute_script("arguments[0].click();", submit_btn)
                        time.sleep(1)
                        break
                    except:
                        pass
            except:
                pass
            
            # NOW: Show Cloudflare screenshot for manual clicking or auto-attempt
            with job_lock:
                job_status[session_id]['message'] = '🔐 Cloudflare checkpoint - show screenshot'
                job_status[session_id]['status'] = 'cloudflare_waiting'
            
            # Capture Cloudflare screenshot
            try:
                screenshot = driver.get_screenshot_as_png()
                cloudflare_img = base64.b64encode(screenshot).decode()
                with job_lock:
                    job_status[session_id]['cloudflare_image'] = cloudflare_img
            except:
                pass
            
            # Wait for user to click or auto-attempt
            cloudflare_clicked = False
            for wait_attempt in range(120):  # Wait up to 60 seconds for user interaction
                time.sleep(0.5)
                with job_lock:
                    if session_id in job_status and job_status[session_id].get('cloudflare_clicked'):
                        cloudflare_clicked = True
                        click_data = job_status[session_id].get('cloudflare_coords', {})
                        # Click the Cloudflare checkbox directly by finding it in iframes
                        try:
                            clicked = False
                            
                            # Method 1: Click checkbox in Cloudflare iframe
                            try:
                                iframes = driver.find_elements(By.TAG_NAME, 'iframe')
                                print(f"[CLOUDFLARE] Found {len(iframes)} iframes on page")
                                for iframe in iframes:
                                    try:
                                        driver.switch_to.frame(iframe)
                                        # Look for Cloudflare checkbox in this iframe
                                        checkbox = driver.find_element(By.CSS_SELECTOR, 'input[type="checkbox"]')
                                        driver.execute_script("arguments[0].click();", checkbox)
                                        driver.switch_to.default_content()
                                        clicked = True
                                        print("[CLOUDFLARE] ✅ Clicked checkbox in iframe")
                                        time.sleep(1)
                                        break
                                    except:
                                        try:
                                            driver.switch_to.default_content()
                                        except:
                                            pass
                            except Exception as e:
                                print(f"[CLOUDFLARE] Iframe method failed: {str(e)}")
                                try:
                                    driver.switch_to.default_content()
                                except:
                                    pass
                            
                            # Method 2: If iframe method didn't work, try main page checkboxes
                            if not clicked:
                                try:
                                    checkboxes = driver.find_elements(By.CSS_SELECTOR, 'input[type="checkbox"]')
                                    for checkbox in checkboxes:
                                        try:
                                            if checkbox.is_displayed():
                                                driver.execute_script("arguments[0].click();", checkbox)
                                                clicked = True
                                                print("[CLOUDFLARE] ✅ Clicked checkbox on main page")
                                                time.sleep(1)
                                                break
                                        except:
                                            pass
                                except Exception as e:
                                    print(f"[CLOUDFLARE] Main page method failed: {str(e)}")
                            
                            # Method 3: Try all button-like elements
                            if not clicked:
                                try:
                                    elements = driver.find_elements(By.CSS_SELECTOR, 'button, [role="button"], .button')
                                    for elem in elements:
                                        try:
                                            text = elem.text.lower()
                                            if 'check' in text or 'verify' in text or 'challenge' in text:
                                                driver.execute_script("arguments[0].click();", elem)
                                                clicked = True
                                                print(f"[CLOUDFLARE] ✅ Clicked element: {text}")
                                                time.sleep(1)
                                                break
                                        except:
                                            pass
                                except:
                                    pass
                            
                            time.sleep(1)
                            if clicked:
                                print("[CLOUDFLARE] ✅ Successfully clicked Cloudflare checkbox")
                            else:
                                print("[CLOUDFLARE] ⚠️ Could not find clickable element")
                        except Exception as e:
                            print(f"[CLOUDFLARE] Click error: {str(e)}")
                        # Reset flag
                        job_status[session_id]['cloudflare_clicked'] = False
                        job_status[session_id]['cloudflare_image'] = None
                        break
            
            # If user didn't click, try auto-clicking
            if not cloudflare_clicked:
                try:
                    for attempt in range(2):
                        for x, y in [(60, 380), (70, 400), (50, 420), (80, 350)]:
                            try:
                                actions = ActionChains(driver)
                                actions.move_by_offset(x, y).click().perform()
                                time.sleep(0.3)
                            except:
                                pass
                        time.sleep(1)
                except:
                    pass
                with job_lock:
                    job_status[session_id]['cloudflare_image'] = None
            
            time.sleep(2)  # Wait for Cloudflare to process
            
            with job_lock:
                job_status[session_id]['message'] = f'📋 Selecting {boost_type}...'
            
            # Select boost type
            try:
                type_btn = driver.find_element(By.XPATH, f"//button[contains(text(), '{boost_type.title()}') or contains(text(), '{boost_type}')]")
                type_btn.click()
                time.sleep(1)
            except:
                pass
            
            # Loop for repeated boosts
            boost_count = 0
            while True:
                with job_lock:
                    if session_id not in job_status or job_status[session_id]['status'] == 'stopped':
                        break
                    
                    job_status[session_id]['message'] = f'✏️ Entering TikTok link... (Boost #{boost_count + 1})'
                
                # Enter TikTok URL
                try:
                    url_input = driver.find_element(By.XPATH, "//input[@placeholder*='TikTok' or @placeholder*='Link' or @type='text']")
                    url_input.click()
                    url_input.clear()
                    url_input.send_keys(tiktok_url)
                    time.sleep(1)
                except:
                    pass
                
                with job_lock:
                    job_status[session_id]['message'] = f'🚀 Clicking send button... (Boost #{boost_count + 1})'
                
                # Click send/boost button
                try:
                    send_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Send') or contains(text(), 'Submit') or contains(text(), 'Boost')]")
                    send_btn.click()
                    boost_count += 1
                    
                    with job_lock:
                        job_status[session_id]['message'] = f'✅ Boost #{boost_count} sent! Next in 90 seconds...'
                    
                    time.sleep(90)  # Wait 1.5 minutes before next boost
                except Exception as e:
                    with job_lock:
                        job_status[session_id]['message'] = f'⏳ Waiting... (Boost #{boost_count + 1})'
                    time.sleep(5)
        
        except Exception as e:
            with job_lock:
                job_status[session_id]['status'] = 'error'
                job_status[session_id]['message'] = f'❌ Error: {str(e)[:50]}'
    
    threading.Thread(target=boost_loop, daemon=True).start()
    return jsonify({'message': 'Boost loop started'})

@tiktok_bp.route('/api/stop-session/<session_id>', methods=['POST'])
def stop_session(session_id):
    """Stop session and close browser"""
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    with job_lock:
        job_status[session_id]['status'] = 'stopped'
        job_status[session_id]['message'] = '⏹️ Stopping...'
    
    try:
        driver = active_sessions[session_id]['driver']
        driver.quit()
        del active_sessions[session_id]
        del job_status[session_id]
    except:
        pass
    
    return jsonify({'message': 'Session stopped'})

