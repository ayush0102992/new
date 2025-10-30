from flask import Flask, request, redirect
import requests
from threading import Thread
import time
import random
import re

app = Flask(__name__)
app.secret_key = 'cookies_legend_2025'

# === SEND WITH COOKIES ===
def send_with_cookies(cookies_str, thread_ids, messages, mn, delay, random_delay, limit):
    sent = 0
    session = requests.Session()
    
    # Parse cookies from text
    cookies = {}
    for item in cookies_str.split(';'):
        item = item.strip()
        if '=' in item:
            k, v = item.split('=', 1)
            cookies[k] = v
    
    session.cookies.update(cookies)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'Referer': 'https://m.facebook.com/',
        'Accept': 'text/html,application/xhtml+xml',
        'Origin': 'https://m.facebook.com',
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print(f"[+] COOKIES LOADED: {len(cookies)} cookies | GCs: {len(thread_ids)} | Msgs: {len(messages)}")

    while limit is None or sent < limit:
        for tid in thread_ids:
            if limit and sent >= limit: break
            for msg in messages:
                if limit and sent >= limit: break
                full_msg = f"{mn} {msg}"

                try:
                    # Get conversation page to extract fb_dtsg
                    conv_url = f'https://m.facebook.com/messages/thread/{tid}/'
                    r = session.get(conv_url, headers=headers, timeout=15)
                    
                    if 'Log in to Facebook' in r.text or 'login' in r.url:
                        print("[-] LOGIN FAILED - COOKIES EXPIRED!")
                        return

                    fb_dtsg = re.search(r'name="fb_dtsg" value="([^"]+)"', r.text)
                    jazoest = re.search(r'name="jazoest" value="([^"]+)"', r.text)
                    if not fb_dtsg or not jazoest:
                        print("[-] fb_dtsg NOT FOUND - Page changed?")
                        time.sleep(3)
                        continue

                    data = {
                        'fb_dtsg': fb_dtsg.group(1),
                        'jazoest': jazoest.group(1),
                        'body': full_msg,
                        'send': 'Send'
                    }

                    # Send message
                    send_url = f'https://m.facebook.com/messages/send/?tid=cid.g.{tid}&source=messenger_web'
                    r2 = session.post(send_url, data=data, headers=headers, timeout=15)

                    if r2.status_code == 200 and ('"success":true' in r2.text or 'message_sent' in r2.text):
                        sent += 1
                        print(f"[+] SENT [{sent}] → {full_msg} | GC: {tid}")
                    else:
                        print(f"[-] FAILED → Rate limit / Block | GC: {tid}")

                except Exception as e:
                    print(f"[-] ERROR: {e}")

                # Delay
                sleep_time = random.uniform(2, 7) if random_delay else delay
                time.sleep(sleep_time)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        cookies = request.form.get('cookies', '').strip()
        if not cookies:
            return "<h3 style='color:red;text-align:center;'>Cookies Daalo!</h3><a href='/'>Back</a>"

        # Messages file
        txt_file = request.files['txtFile']
        if not txt_file or not txt_file.filename:
            return "<h3 style='color:red;text-align:center;'>Text File Daalo!</h3><a href='/'>Back</a>"
        messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

        # GC IDs
        thread_ids = [t.strip() for t in request.form.get('threadId', '').split(',') if t.strip()]
        if not thread_ids:
            return "<h3 style='color:red;text-align:center;'>GC ID Daalo!</h3><a href='/'>Back</a>"

        mn = request.form.get('kidx', 'LEGEND')
        delay = max(3, int(request.form.get('time', 4)))
        random_delay = 'random_delay' in request
        limit = int(request.form.get('limit')) if request.form.get('limit') else None

        # Start bombing in background
        Thread(target=send_with_cookies, args=(cookies, thread_ids, messages, mn, delay, random_delay, limit), daemon=True).start()
        
        return f"""
        <div style="background:#000;color:#0f0;text-align:center;padding:50px;font-family:Courier;">
          <h2>COOKIES BOMBER STARTED!</h2>
          <p>GCs: {len(thread_ids)} | Messages: {len(messages)} | Delay: {delay}s</p>
          <a href="/" style="color:#0f0;">Back to Home</a>
        </div>
        """

    return '''
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>COOKIES BOMBER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body {background:#000;color:#0f0;font-family:'Courier New';text-align:center;padding:20px;}
      .box {background:rgba(0,20,0,0.8);border:1px solid #0f0;border-radius:10px;padding:18px;margin:15px auto;max-width:500px;box-shadow:0 0 20px #0f0;}
      textarea, input, button {width:100%;padding:14px;margin:8px 0;background:#111;border:1px solid #0f0;color:#0f0;border-radius:8px;font-size:16px;}
      button {background:#0f0;color:#000;font-weight:bold;font-size:18px;}
      h1 {text-shadow:0 0 25px #0f0;margin:20px;}
      small {color:#0a0;font-size:12px;}
      a {color:#0f0;}
    </style>
    </head><body>
    <h1>COOKIES BOMBER</h1>
    
    <form method="post" enctype="multipart/form-data">
      <div class="box">
        <b>Facebook Cookies (Paste from SmartCookieWeb)</b><br>
        <textarea name="cookies" placeholder="c_user=...; xs=...; fr=..." rows="6" required></textarea>
        <small>
          <b>SmartCookieWeb → Dev Tools → Console → </b><code style="background:#222;padding:2px;">copy(document.cookie)</code>
        </small>
      </div>

      <div class="box">
        <b>Messages File</b><br>
        <input type="file" name="txtFile" required>
      </div>

      <div class="box">
        <b>GC IDs (comma separated)</b><br>
        <input type="text" name="threadId" placeholder="2208341826321706, 123456789" required>
      </div>

      <div class="box">
        <b>Hathe Name</b><br>
        <input type="text" name="kidx" value="LEGEND">
      </div>

      <div class="box">
        <b>Delay (seconds)</b><br>
        <input type="number" name="time" value="4" min="3">
        <label><input type="checkbox" name="random_delay"> Random Delay (3-8s)</label>
      </div>

      <div class="box">
        <b>Stop After (optional)</b><br>
        <input type="number" name="limit" placeholder="100 messages">
      </div>

      <button type="submit">START BOMBING</button>
    </form>

    <div class="box">
      <small>
        <a href="https://github.com/CookieJarApps/SmartCookieWeb" target="_blank">SmartCookieWeb Download</a> | 
        <a href="https://m.facebook.com" target="_blank">Login Here</a>
      </small>
    </div>
    </body></html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)
