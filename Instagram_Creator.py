# instagram_creator_full.py
import tkinter as tk
from tkinter import ttk
import requests, uuid, random, time, hashlib, threading, os
from datetime import datetime
import string
from faker import Faker

# Selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------------- Helper Functions ----------------
def generate_uuid(prefix: str = '', suffix: str = '') -> str:
    return f'{prefix}{uuid.uuid4()}{suffix}'

def generate_android_device_id() -> str:
    return "android-%s" % hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

def generate_useragent():
    try:
        with open("UserAgent.txt","r",encoding="utf-8") as f:
            agents = [l.strip() for l in f if l.strip()]
        if agents:
            a = random.choice(agents)
            parts = a.split(",")
            if len(parts)>=10:
                return f'Instagram 261.0.0.21.111 Android ({parts[7]}/{parts[6]}; {parts[5]}dpi; {parts[4]}; {parts[0]}; {parts[1]}; {parts[2]}; {parts[3]}; en_US; {parts[9]})'
            else:
                return a
    except: pass
    return 'Instagram 261.0.0.21.111 Android (28/9; 420dpi; Pixel 4 XL; Google; Pixel; 11; 1; en_US; 0)'

def get_mid():
    try:
        r = requests.get("https://i.instagram.com/api/v1/accounts/login",timeout=6)
        mid = r.cookies.get("mid")
        if mid: return mid
    except: pass
    u01 = 'QWERTYUIOPASDFGHJKLZXCVBNM'
    return f'Y4nS4g{"".join(random.choice(u01) for _ in range(8))}zwIrWdeYLcD9Shxj'

def Username():
    fake = Faker()
    return fake.user_name()

def Password():
    all_chars = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.sample(all_chars,10))

def generate_jazoest(symbols: str) -> str:
    return f"2{sum(ord(s) for s in symbols)}"

def Birthday():
    return [str(random.randint(1,28)), str(random.randint(1988,2003)), str(random.randint(1,12))]

def log_message(log_widget, message: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_widget.configure(state="normal")
    log_widget.insert(tk.END,f"[{ts}] {message}\n")
    log_widget.see(tk.END)
    log_widget.configure(state="disabled")

# ---------------- Main App ----------------
class InstagramCreatorApp:
    def __init__(self, root):
        self.root = root
        root.title("Instagram Creator + Selenium Follow")
        root.geometry("1000x700")
        root.configure(bg="#0f1724")
        self.current_driver = None
        self.accounts_file = "accounts.txt"

        # Tk Variables
        self.phone_var = tk.StringVar()
        self.sms_var = tk.StringVar()
        self.custom_user_var = tk.StringVar()
        self.custom_pass_var = tk.StringVar()
        self.custom_bio_var = tk.StringVar()
        self.follow_var = tk.StringVar()

        self.reset_identity()
        self.build_ui()
        self.refresh_accounts_tree()

    def reset_identity(self):
        self.Device_ID = generate_uuid()
        self.Family_ID = generate_uuid()
        self.Android_ID = generate_android_device_id()
        self.UserAgent = generate_useragent()
        self.X_Mid = get_mid()
        self.adid = str(uuid.uuid4())
        self.water = str(uuid.uuid4())
        self.username_auto = Username()
        self.password_auto = Password()
        self.jazoest = generate_jazoest(self.Family_ID)
        self.birth = Birthday()

    def threaded(self, fn):
        def wrapper():
            threading.Thread(target=fn, daemon=True).start()
        return wrapper

    def build_headers(self):
        return {
            'Host':'i.instagram.com',
            'X-Ig-App-Locale':'en_US',
            'X-Ig-Device-Locale':'en_US',
            'X-Ig-Mapped-Locale':'en_US',
            'X-Pigeon-Session-Id':generate_uuid('UFS-','-1'),
            'X-Pigeon-Rawclienttime':str(round(time.time(),3)),
            'X-Ig-Bandwidth-Speed-Kbps':str(random.randint(2500000,3000000)/1000),
            'X-Ig-Bandwidth-Totalbytes-B':str(random.randint(5000000,90000000)),
            'X-Ig-Bandwidth-Totaltime-Ms':str(random.randint(2000,9000)),
            'X-Bloks-Version-Id':'a399f367a2e4aa3e40cdb4aab6535045b23db15f3dea789880aa062',
            'X-Ig-Www-Claim':'0',
            'X-Bloks-Is-Layout-Rtl':'false',
            'X-Ig-Device-Id':self.Device_ID,
            'X-Ig-Family-Device-Id':self.Family_ID,
            'X-Ig-Android-Id':self.Android_ID,
            'X-Ig-Timezone-Offset':'16500',
            'X-Fb-Connection-Type':'WIFI',
            'X-Ig-Connection-Type':'WIFI',
            'X-Ig-Capabilities':'3brTv10=',
            'X-Ig-App-Id':'567067343352427',
            'Priority':'u=3',
            'User-Agent':self.UserAgent,
            'Accept-Language':'en-US',
            'X-Mid':self.X_Mid,
            'Ig-Intended-User-Id':'0',
            'Content-Type':'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Fb-Http-Engine':'Liger',
            'X-Fb-Client-Ip':'True',
            'X-Fb-Server-Cluster':'True',
            'Connection':'close',
        }

    def refresh_accounts_tree(self):
        for row in self.accounts_tree.get_children():
            self.accounts_tree.delete(row)
        if os.path.exists(self.accounts_file):
            with open(self.accounts_file,"r",encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(":")
                    username = parts[0] if len(parts)>0 else ""
                    password = parts[1] if len(parts)>1 else ""
                    token = ":".join(parts[2:]) if len(parts)>2 else ""
                    self.accounts_tree.insert("",tk.END,values=(username,password,token))

# ---------------- UI Build ----------------
    def build_ui(self):
        root = self.root
        # Left panel
        left = tk.Frame(root,bg="#0b1220",padx=14,pady=14)
        left.place(relx=0.005,rely=0.005,relwidth=0.48,relheight=0.98)
        tk.Label(left,text="Account Inputs",font=("Segoe UI",11,"bold"),fg="#06b6d4",bg="#0b1220").pack(anchor="w")

        fields = [("Phone Number",self.phone_var),("SMS Code",self.sms_var),
                  ("Custom Username",self.custom_user_var),("Custom Password",self.custom_pass_var),
                  ("Custom Bio",self.custom_bio_var),("Instagram Username to Follow",self.follow_var)]
        for lbl,var in fields:
            tk.Label(left,text=lbl,bg="#0b1220",fg="#94a3b8").pack(anchor="w",pady=2)
            show="*" if "Password" in lbl else ""
            tk.Entry(left,textvariable=var,width=36,bg="#071127",fg="#e6f7f6",insertbackground="#e6f7f6",show=show).pack(anchor="w",pady=2)

        # Buttons frame (will add buttons in Part 2)
        self.btn_frame = tk.Frame(left,bg="#0b1220")
        self.btn_frame.pack(fill="x",pady=10)

        # Right panel
        right = tk.Frame(root,bg="#0b1220",padx=14,pady=14)
        right.place(relx=0.49,rely=0.005,relwidth=0.495,relheight=0.98)
        tk.Label(right,text="Saved Accounts",font=("Segoe UI",11,"bold"),fg="#06b6d4",bg="#0b1220").pack(anchor="w")
        columns = ("username","password","token")
        self.accounts_tree = ttk.Treeview(right, columns=columns, show="headings", height=35)
        for col in columns:
            self.accounts_tree.heading(col,text=col.title())
            self.accounts_tree.column(col,width=200)
        self.accounts_tree.pack(fill="both",expand=True)

        # Log box
        self.log = tk.Text(left,height=12,bg="#071127",fg="#e6f7f6",state="disabled")
        self.log.pack(fill="both",expand=True,pady=10)

# ---------------- API Functions -----------------
def api_check_phone(self):
    num = self.phone_var.get()
    if not num:
        log_message(self.log,"Enter a phone number first")
        return
    data = {'signed_body': f'SIGNATURE.{{"phone_id":"{self.Family_ID}","login_nonce_map":"{{}}","phone_number":"{num}","guid":"{self.Device_ID}","device_id":"{self.Android_ID}","prefill_shown":"False"}}'}
    try:
        r = requests.post("https://i.instagram.com/api/v1/accounts/check_phone_number/", headers=self.build_headers(), data=data)
        log_message(self.log,f"[Check Phone] {r.text}")
    except Exception as e:
        log_message(self.log,f"[Check Phone] Error: {e}")

def api_send_sms(self):
    num = self.phone_var.get()
    if not num:
        log_message(self.log,"Enter a phone number first")
        return
    data = {'signed_body': f'SIGNATURE.{{"phone_id":"{self.Family_ID}","phone_number":"{num}","guid":"{self.Device_ID}","device_id":"{self.Android_ID}","android_build_type":"release","waterfall_id":"{self.water}"}}'}
    try:
        r = requests.post("https://i.instagram.com/api/v1/accounts/send_signup_sms_code/", headers=self.build_headers(), data=data)
        log_message(self.log,f"[Send SMS] {r.text}")
    except Exception as e:
        log_message(self.log,f"[Send SMS] Error: {e}")

def api_validate_sms(self):
    num = self.phone_var.get()
    code = self.sms_var.get()
    if not num or not code:
        log_message(self.log,"Enter phone and SMS code first")
        return
    data = {'signed_body': f'SIGNATURE.{{"verification_code":"{code}","phone_number":"{num}","guid":"{self.Device_ID}","device_id":"{self.Android_ID}","waterfall_id":"{self.water}"}}'}
    try:
        r = requests.post("https://i.instagram.com/api/v1/accounts/validate_signup_sms_code/", headers=self.build_headers(), data=data)
        log_message(self.log,f"[Validate SMS] {r.text}")
    except Exception as e:
        log_message(self.log,f"[Validate SMS] Error: {e}")

def api_username_suggestion(self):
    username = self.custom_user_var.get() or self.username_auto
    data = {'signed_body': f'SIGNATURE.{{"phone_id":"{self.Family_ID}","guid":"{self.Device_ID}","name":"{username}","device_id":"{self.Android_ID}","email":"","waterfall_id":"{self.water}"}}'}
    try:
        r = requests.post("https://i.instagram.com/api/v1/accounts/username_suggestions/", headers=self.build_headers(), data=data).json()
        suggestion = r['suggestions_with_metadata']['suggestions'][0]['username']
        self.custom_user_var.set(suggestion)
        log_message(self.log,f"[Username Suggestion] {suggestion}")
    except Exception as e:
        log_message(self.log,f"[Username Suggestion] Error: {e}")

def api_create_account(self):
    username = self.custom_user_var.get() or self.username_auto
    password = self.custom_pass_var.get() or self.password_auto
    num = self.phone_var.get()
    code = self.sms_var.get()
    if not num or not code:
        log_message(self.log,"Phone or SMS code missing")
        return
    birth = self.birth
    jazoest = self.jazoest
    data = {
        'signed_body': f'SIGNATURE.{{"is_secondary_account_creation":"false","jazoest":"{jazoest}","tos_version":"row","suggestedUsername":"","verification_code":"{code}","do_not_auto_login_if_credentials_match":"true","phone_id":"{self.Family_ID}","enc_password":"#PWD_INSTAGRAM:0:{int(datetime.now().timestamp())}:{password}","phone_number":"{num}","username":"{username}","first_name":"{username}","day":"{birth[0]}","adid":"{self.adid}","guid":"{self.Device_ID}","year":"{birth[1]}","device_id":"{self.Android_ID}","_uuid":"{self.Device_ID}","month":"{birth[2]}","sn_nonce":"","force_sign_up_code":"","waterfall_id":"{self.water}","qs_stamp":"","has_sms_consent":"true","one_tap_opt_in":"true"}}'
    }
    try:
        r = requests.post("https://i.instagram.com/api/v1/accounts/create_validated/", headers=self.build_headers(), data=data)
        log_message(self.log,f"[Create Account] {r.text}")
        if 'account_created":true' in r.text:
            token = r.headers.get('ig-set-authorization',"")
            with open("accounts.txt","a",encoding="utf-8") as f:
                f.write(f"{username}:{password}:{token}\n")
            self.refresh_accounts_tree()
            log_message(self.log,f"[Create Account] Success: {username}")
        else:
            log_message(self.log,f"[Create Account] Failed: {r.text}")
    except Exception as e:
        log_message(self.log,f"[Create Account] Error: {e}")

# ---------------- Selenium Login + Follow ----------------
def selenium_login_follow(self):
    selected = self.accounts_tree.selection()
    if not selected:
        log_message(self.log,"[Follow] Select an account first")
        return
    values = self.accounts_tree.item(selected[0],'values')
    username = values[0]
    password = values[1]
    target = self.follow_var.get()
    if not target:
        log_message(self.log,"[Follow] Enter username to follow")
        return

    def _login_follow():
        try:
            log_message(self.log,f"[Follow] Logging in {username} and navigating to {target}")
            options = webdriver.ChromeOptions()
            options.add_argument("--start-maximized")
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.get("https://www.instagram.com/accounts/login/")
            wait = WebDriverWait(driver,15)
            # Login
            user_field = wait.until(EC.presence_of_element_located((By.NAME,"username")))
            pass_field = driver.find_element(By.NAME,"password")
            user_field.send_keys(username)
            pass_field.send_keys(password)
            pass_field.send_keys(Keys.RETURN)
            time.sleep(5)
            driver.get(f"https://www.instagram.com/{target}/")
            # Wait and click follow
            try:
                follow_btn = WebDriverWait(driver,10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH,
                         "//div[normalize-space(text())='Follow'] | "
                         "//div[normalize-space(text())='Folgen'] | "
                         "//div[normalize-space(text())='Follow Back']"
                        )
                    )
                )
                follow_btn.click()
                log_message(self.log,f"[Follow] Successfully followed {target}")
            except Exception:
                log_message(self.log,f"[Follow] Could not find Follow button for {target}")
        except Exception as e:
            log_message(self.log,f"[Follow] Error: {e}")

    threading.Thread(target=_login_follow, daemon=True).start()

# ---------------- Attach functions to class -----------------
InstagramCreatorApp.check_phone = lambda self: threading.Thread(target=api_check_phone,args=(self,),daemon=True).start()
InstagramCreatorApp.send_sms = lambda self: threading.Thread(target=api_send_sms,args=(self,),daemon=True).start()
InstagramCreatorApp.validate_code = lambda self: threading.Thread(target=api_validate_sms,args=(self,),daemon=True).start()
InstagramCreatorApp.username_suggestions = lambda self: threading.Thread(target=api_username_suggestion,args=(self,),daemon=True).start()
InstagramCreatorApp.create_account = lambda self: threading.Thread(target=api_create_account,args=(self,),daemon=True).start()
InstagramCreatorApp.login_and_follow = lambda self: selenium_login_follow(self)

# ---------------- Run App -----------------
if __name__=="__main__":
    root = tk.Tk()
    app = InstagramCreatorApp(root)
    # Buttons
    tk.Button(app.btn_frame,text="Check Phone",command=app.check_phone,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)
    tk.Button(app.btn_frame,text="Send SMS",command=app.send_sms,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)
    tk.Button(app.btn_frame,text="Validate SMS",command=app.validate_code,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)
    tk.Button(app.btn_frame,text="Username Suggestion",command=app.username_suggestions,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)
    tk.Button(app.btn_frame,text="Create Account",command=app.create_account,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)
    tk.Button(app.btn_frame,text="Follow User",command=app.login_and_follow,bg="#06b6d4",fg="#0b1220").pack(side="left", padx=5)

    root.mainloop()
