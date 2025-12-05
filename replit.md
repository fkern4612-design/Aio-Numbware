# Kahoot AIO + Spotify AIO - Dual Web Dashboard

## Overview
A comprehensive multi-application platform featuring **Kahoot AIO**, **Spotify AIO**, **TikTok AIO**, and **Instagram AIO** with a beautiful launcher dashboard. All apps run on the same Flask server with a unified launcher interface.

## 🎵 Features - TikTok AIO
- **Custom Engagement Booster**: Advanced views, likes, followers, shares delivery
- **Smart Delivery**: 100 views every 5 minutes with real-time tracking
- **Live Monitoring**: Real-time order feed and boost cycle tracking
- **Security Verified**: Advanced verification system
- **Real-time Status**: Live progress display during boost
- **Simple 3-Step Process**: Select service → Paste URL → Start boost

## 🎵 Features - Spotify AIO
- **Account Creator**: Batch create multiple Spotify accounts simultaneously
- **Account Manager**: View, export, and manage all created accounts
- **Auto-save**: All accounts automatically saved to persistent storage
- **Progress Tracking**: Real-time status updates during account creation
- **Account Export**: Download accounts as text file
- **Batch Operations**: Create up to 50 accounts at once

## 📸 Features - Instagram AIO (NEW - Multi-Feature Menu)
- **Account Creator**: Create Instagram accounts with SMS phone verification
- **Account Manager**: View all created accounts in one place
- **Follow Bot**: Login with Selenium and auto-follow specified users
- **Like Automation**: Like any Instagram post automatically
- **Comment Bot**: Post comments on Instagram posts automatically
- **Share/Save Bot**: Save posts to account automatically
- **Menu-Based Interface**: Simple dashboard to choose between 5 features
- **Real-time Status**: Live feedback for each action with progress tracking
- **Persistent Storage**: All accounts saved to ~/instagram_accounts.txt

## Project Structure
```
.
├── app.py                         # Main Flask app (all 3 AIO apps)
├── tiktok_aio.py                 # TikTok AIO - Zefoy.com automation
├── instagram_aio.py              # Instagram AIO - Account creation
├── spotify_aio.py                # Spotify AIO - Account creation
├── templates/
│   ├── launcher.html             # Triple-app launcher (HOME)
│   ├── tiktok_dashboard.html     # TikTok booster (Zefoy)
│   ├── instagram_dashboard.html  # Instagram account creator
│   └── spotify_dashboard.html    # Spotify account creator
├── requirements.txt              # Python dependencies
└── replit.md                     # This documentation
```

## Technology Stack
- **Backend**: Flask (Python 3.11)
- **Frontend**: Bootstrap 5, Vanilla JavaScript
- **Automation**: Selenium WebDriver with Chrome/Chromium
- **UI**: Gradient design with responsive cards and forms
- **Storage**: File-based persistence for accounts

## Dependencies
- Flask - Web framework
- Selenium - Browser automation
- webdriver-manager - ChromeDriver management
- requests - HTTP client for API calls

## Configuration
- **Host**: 0.0.0.0 (allows external access)
- **Port**: 5000 (frontend only)
- **Server**: Flask development server
- **Browser**: Headless Chrome with semaphore (max 5 concurrent)

## API Endpoints

### Main Routes
- `GET /` - **Launcher Dashboard** (all 4 apps accessible)
- `GET /tiktok` - TikTok AIO Dashboard
- `GET /instagram` - Instagram AIO Multi-Feature Dashboard
- `GET /spotify` - Spotify AIO Dashboard

### TikTok API
- `POST /tiktok/api/start-session` - Start verification session
- `GET /tiktok/api/session-status/<id>` - Get session status with captcha
- `POST /tiktok/api/submit-captcha` - Submit captcha and start boost
- `POST /tiktok/api/stop-session/<id>` - Stop boost loop
- `GET /tiktok/api/get-services` - Get available boost services
- `POST /tiktok/api/start-boost` - Start endless boost with custom range

### Instagram API - Account Creation
- `POST /instagram/api/check-phone` - Check if phone available
- `POST /instagram/api/send-sms` - Send SMS verification code
- `POST /instagram/api/validate-sms` - Validate SMS code
- `POST /instagram/api/create-with-verification` - Create account
- `GET /instagram/api/accounts` - Get all accounts

### Instagram API - Automation (Login-Based)
- `POST /instagram/api/login-account` - Login with Selenium
- `GET /instagram/api/login-status/<job_id>` - Check login status
- `POST /instagram/api/follow-user` - Follow specified user
- `GET /instagram/api/follow-status/<job_id>` - Check follow status
- `POST /instagram/api/like-post` - Like a post
- `GET /instagram/api/like-status/<job_id>` - Check like status
- `POST /instagram/api/comment-post` - Comment on a post
- `GET /instagram/api/comment-status/<job_id>` - Check comment status
- `POST /instagram/api/share-post` - Save/share a post
- `GET /instagram/api/share-status/<job_id>` - Check share status

### Spotify API
- `POST /spotify/api/create-accounts` - Create batch accounts
- `GET /spotify/api/account-progress?job_id=<id>` - Check creation progress
- `GET /spotify/api/accounts` - Get all accounts

## Navigation Guide
1. **Landing**: Visit `/` for the launcher dashboard
2. **Choose App**: Click "Launch Kahoot" or "Launch Spotify"
3. **Use Feature**: Both apps have fully integrated navigation
4. **Return**: Click the app name in navbar to return to launcher

## Security & Optimization
- **Semaphore Limiting**: Max 5 concurrent browsers to prevent resource exhaustion
- **Backup Bot Buffer**: Tries 15 bots to ensure 10 successful joins
- **Persistent Storage**: Accounts saved to `~/spotify_accounts.txt`
- **Error Handling**: Graceful fallbacks for all API calls
- **Cache Control**: Hard refresh recommended for browser updates

## Recent Changes (2025-12-03 LATEST)
- ✅ **Removed Selenium Bot** - Streamlined to keep only working API-based Instagram AIO
- ✅ **Removed SMM Panel** - Focused on core AIO functionality
- ✅ **Instagram AIO Stable** - Phone verification working with email backup
- ✅ **4 Core AIOs Active**: Kahoot, Spotify, TikTok, Instagram
- ✅ **Instagram Features**: Account Creator (Phone/Email), Follow Bot, Like Bot, Comment Bot, Share Bot
- ✅ **All AIOs Fully Integrated** - Working Flask blueprints with real automation

## Testing Checklist - Instagram AIO
- ✅ Main menu loads with 5 options
- ✅ Create account workflow works (phone → SMS → verify → create)
- ✅ Accounts save to text file properly
- ✅ Follow user login and follow functionality
- ✅ Like post Selenium automation
- ✅ Comment post with custom text
- ✅ Save/share post functionality
- ✅ Account selector dropdowns populate correctly
- ✅ Status messages show progress in real-time

## Deployment Instructions
1. Click **"Publish"** button at top of Replit
2. Select **"Autoscale"** deployment type
3. Configure resources (defaults work fine)
4. Click **"Deploy"** to go live
5. Get your permanent public URL
6. (Optional) Add to UptimeRobot to keep apps warm

## Educational Purpose
This dual-AIO platform demonstrates advanced web automation, modern web dashboard development, and full-stack integration of multiple applications on a single server.

## Current Status
**PRODUCTION READY** - Instagram AIO completely redesigned with 5 automation features. All branding cleaned. Ready for deployment!

---
**Last Updated**: 2025-12-02 14:00 UTC
**Status**: ✅ COMPLETE & OPERATIONAL - Instagram AIO Multi-Feature Menu Live
