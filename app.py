from flask import Flask, request, redirect
import requests
from threading import Thread
import time
import random
import re

app = Flask(__name__)
app.secret_key = 'fixed_cookies_2025'

def send_with_cookies(cookies_str, thread_ids, messages, mn, delay, random_delay, limit):
    sent = 0
    session = requests.Session()
    
    # === PARSE COOKIES ===
    cookies = {}
    for item in cookies_str.split(';'):
        item = item.strip()
        if '=' in item and item.count('=') == 1:
            k, v = item.split('=', 1)
            cookies[k] = v
    
    if 'c_user' not in cookies or 'xs' not in cookies:
        print("[-] MISSING c_user or xs → INVALID COOKIES!")
        return

    session.cookies.update(cookies)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Mobile Safari/537.36',
        'Referer': 'https://m.facebook.com/',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Origin': 'https://m.facebook.com',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    print(f"[+] COOKIES LOADED: c_user={cookies['c_user']} | GCs: {len(thread_ids)}")

    while limit is None or sent < limit:
        for tid in thread_ids:
            if limit and sent >= limit: break
            for msg in messages:
                if limit and sent >= limit: break
                full_msg = f"{mn} {msg}"

                try:
                    # === GET CONVERSATION ===
                    conv_url = f'https://m.facebook.com/messages/read/?tid=cid.g.{tid}'
                    r = session.get(conv_url, headers=headers, timeout=20)
                    
                    if 'login' in r.url.lower() or 'checkpoint' in r.url:
                        print("[-] COOKIES EXPIRED OR BLOCKED!")
                        return

                    # === EXTRACT fb_dtsg & jazoest ===
                    fb_dtsg = re.search(r'name="fb_dtsg" value="([^"]+)"', r.text)
                    jazoest = re.search(r'name="jazoest" value="([^"]+)"', r.text)
                    if not fb_dtsg or not jazoest:
                        print("[-] fb_dtsg NOT FOUND")
                        time.sleep(3)
                        continue

                    # === SEND MESSAGE ===
                    send_url = 'https://m.facebook.com/messages/send/'
                    data = {
                        'fb_dtsg': fb_dtsg.group(1),
                        'jazoest': jazoest.group(1),
                        'body': full_msg,
                        'tids': f'cid.g.{tid}',
                        'wwwupp': 'C3',
                        'ids[0]': tid,
                        'referrer': '',
                        'ctype': '',
                        'cver': 'legacy'
                    }

                    r2 = session.post(send_url, data=data, headers=headers, timeout=20)
                    if r2.status_code == 200 and ('"success":true' in r2.text or 'sent' in r2.text):
                        sent += 1
                        print(f"[+] SENT [{sent}] → {full_msg} | GC: {tid}")
                    else:
                        print(f"[-] FAILED → Rate limit | Response: {r2.status_code}")

                except Exception as e:
                    print(f"[-] ERROR: {str(e)[:100]}")

                time.sleep(random.uniform(3, 8) if random_delay else delay)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        cookies = request.form.get('cookies', '').strip()
        if not cookies:
            return error("Cookies Daalo!")

        txt_file = request.files.get('txtFile')
        if not txt_file or not txt_file.filename:
            return error("Text File Daalo!")
        messages = [l.strip() for l in txt_file.read().decode('utf-8', errors='ignore').splitlines() if l.strip()]

        thread_ids = [t.strip() for t in request.form.get('threadId', '').split(',') if t.strip()]
        if not thread_ids:
            return error("GC ID Daalo!")

        mn = request.form.get('kidx', 'LEGEND')
        delay = max(3, int(request.form.get('time', 4)))
        random_delay = 'random_delay' in request
        limit = request.form.get('limit')
        limit = int(limit) if limit and limit.isdigit() else None

        Thread(target=send_with_cookies, args=(cookies, thread_ids, messages, mn, delay, random_delay, limit), daemon=True).start()
        
        return success(f"STARTED! GCs: {len(thread_ids)} | Msgs: {len(messages)}")

    return '''
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>COOKIES BOMBER</title>
    <style>
      body {background:#000;color:#0f0;font-family:Courier;text-align:center;padding:20px;}
      .box {background:#111;border:1px solid #0f0;padding:15px;border-radius:8px;margin:10px auto;max-width:500px;}
      textarea, input, button {width:100%;padding:12px;margin:8px 0;background:#000;border:1px solid #0f0;color:#0f0;border-radius:6px;}
      button {background:#0f0;color:#000;font-weight:bold;}
      h1 {text-shadow:0 0 20px #0f0;}
    </style></head><body>
    <h1>COOKIES BOMBER</h1>
    <form method="post" enctype="multipart/form-data">
      <div class="box">
        <textarea name="cookies" placeholder="c_user=...; xs=..." rows="5" required></textarea>
        <small>copy(document.cookie)</small>
      </div>
      <div class="box"><input type="file" name="txtFile" required></div>
      <div class="box"><input type="text" name="threadId" placeholder="GC ID" required></div>
      <div class="box"><input type="text" name="kidx" value="LEGEND"></div>
      <div class="box"><input type="number" name="time" value="4" min="3"></div>
      <div class="box"><input type="checkbox" name="random_delay"> Random Delay</div>
      <div class="box"><input type="number" name="limit" placeholder="Stop after"></div>
      <button type="submit">START</button>
    </form>
    </body></html>
    '''

def error(msg): return f'<div style="background:#000;color:#f00;text-align:center;padding:50px;font-family:Courier;"><h2>ERROR</h2><p>{msg}</p><a href="/" style="color:#0f0;">Back</a></div>'
def success(msg): return f'<div style="background:#000;color:#0f0;text-align:center;padding:50px;font-family:Courier;"><h2>SUCCESS</h2><p>{msg}</p><a href="/" style="color:#0f0;">Back</a></div>'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
