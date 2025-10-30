from flask import Flask, request
import requests
from threading import Thread
import time
import random
import re

app = Flask(__name__)
app.secret_key = 'legend_cookies_2025'

def bomber(cookies_str, gc_ids, messages, prefix, delay, random_delay, limit):
    sent = 0
    session = requests.Session()

    # === COOKIES PARSE ===
    cookies = {}
    for part in [x.strip() for x in cookies_str.split(';') if x.strip()]:
        if '=' in part:
            k, v = part.split('=', 1)
            cookies[k] = v
    session.cookies.update(cookies)

    # === HEADERS (MOST IMPORTANT) ===
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36',
        'Referer': 'https://m.facebook.com/',
        'Origin': 'https://m.facebook.com',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'text/html,application/xhtml+xml',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }

    print(f"[+] BOMBER STARTED | c_user: {cookies.get('c_user','?')} | GCs: {len(gc_ids)}")

    while limit is None or sent < limit:
        for gc in gc_ids:
            if limit and sent >= limit: break
            for msg in messages:
                if limit and sent >= limit: break
                full_msg = f"{prefix} {msg}"

                try:
                    # Open chat
                    chat_url = f'https://m.facebook.com/messages/read/?tid=cid.g.{gc}'
                    r = session.get(chat_url, headers=headers, timeout=15)
                    
                    if 'login' in r.url.lower():
                        print("[-] COOKIES EXPIRED!")
                        return

                    # Extract fb_dtsg & jazoest
                    dtsg = re.search(r'name="fb_dtsg" value="([^"]+)"', r.text)
                    jazo = re.search(r'name="jazoest" value="([^"]+)"', r.text)
                    if not dtsg or not jazo:
                        print("[-] fb_dtsg NOT FOUND")
                        continue

                    # Send message
                    payload = {
                        'fb_dtsg': dtsg.group(1),
                        'jazoest': jazo.group(1),
                        'body': full_msg,
                        'tids': f'cid.g.{gc}',
                        'ids[0]': gc,
                        'wwwupp': 'C3'
                    }

                    send_url = 'https://m.facebook.com/messages/send/'
                    r2 = session.post(send_url, data=payload, headers=headers, timeout=15)

                    if r2.status_code == 200:
                        sent += 1
                        print(f"[+] SENT [{sent}] → {full_msg} | GC: {gc}")
                    else:
                        print(f"[-] FAILED → Status: {r2.status_code}")

                except Exception as e:
                    print(f"[-] ERROR: {e}")

                time.sleep(random.uniform(5, 10) if random_delay else delay)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        cookies = request.form.get('cookies', '').strip()
        if not cookies or 'c_user' not in cookies:
            return error("Cookies Invalid!")

        file = request.files['txtFile']
        messages = [l.strip() for l in file.read().decode('utf-8', 'ignore').splitlines() if l.strip()]
        if not messages:
            return error("Messages Empty!")

        gc_ids = [g.strip() for g in request.form.get('gc', '').split(',') if g.strip()]
        if not gc_ids:
            return error("GC ID Daalo!")

        prefix = request.form.get('prefix', 'LEGEND')
        delay = max(5, int(request.form.get('delay', '6')))
        random_delay = 'random' in request.form
        limit = request.form.get('limit')
        limit = int(limit) if limit and limit.isdigit() else None

        Thread(target=bomber, args=(cookies, gc_ids, messages, prefix, delay, random_delay, limit), daemon=True).start()
        return success(f"BOMBING STARTED!<br>Sent: 0 | GCs: {len(gc_ids)} | Msgs: {len(messages)}")

    return '''
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>COOKIES BOMBER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body{background:#000;color:#0f0;font-family:Courier;text-align:center;padding:20px;}
      .box{background:#111;border:1px solid #0f0;padding:18px;border-radius:10px;margin:15px auto;max-width:500px;box-shadow:0 0 15px #0f0;}
      textarea, input, button{width:100%;padding:14px;margin:10px 0;background:#000;border:1px solid #0f0;color:#0f0;border-radius:8px;font-size:16px;}
      button{background:#0f0;color:#000;font-weight:bold;}
      h1{text-shadow:0 0 25px #0f0;}
      small{color:#0a0;}
    </style></head><body>
    <h1>COOKIES BOMBER</h1>
    <form method="post" enctype="multipart/form-data">
      <div class="box">
        <b>Cookies (copy(document.cookie))</b><br>
        <textarea name="cookies" rows="5" placeholder="c_user=...; xs=..." required></textarea>
      </div>
      <div class="box"><input type="file" name="txtFile" required></div>
      <div class="box"><input type="text" name="gc" placeholder="GC ID (comma separated)" required></div>
      <div class="box"><input type="text" name="prefix" value="LEGEND"></div>
      <div class="box"><input type="number" name="delay" value="6" min="5"></div>
      <div class="box"><input type="checkbox" name="random"> Random Delay (5-10s)</div>
      <div class="box"><input type="number" name="limit" placeholder="Stop after messages"></div>
      <button type="submit">START BOMBING</button>
    </form>
    </body></html>
    '''

def error(msg): 
    return f'<div style="background:#000;color:#f00;padding:50px;text-align:center;font-family:Courier;"><h2>ERROR</h2><p>{msg}</p><a href="/" style="color:#0f0;">BACK</a></div>'

def success(msg): 
    return f'<div style="background:#000;color:#0f0;padding:50px;text-align:center;font-family:Courier;"><h2>SUCCESS</h2><p>{msg}</p><a href="/" style="color:#0f0;">BACK</a></div>'

if __name__ == '__main__':
    print("COOKIES BOMBER FINAL → http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=False)
