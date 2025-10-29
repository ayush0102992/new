from flask import Flask, request, redirect
import requests
from threading import Thread
import time
import random

app = Flask(__name__)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def send_messages(tokens, thread_ids, messages, mn, delay, random_delay, limit):
    sent = 0
    while limit is None or sent < limit:
        for tid in thread_ids:
            for msg in messages:
                full_msg = f"{mn} {msg}"
                for token in tokens:
                    if limit and sent >= limit: break
                    url = f'https://graph.facebook.com/v15.0/t_{tid}/'
                    params = {'access_token': token, 'message': full_msg}
                    d = random.uniform(1, 5) if random_delay else delay
                    try:
                        r = requests.post(url, data=params, headers=headers, timeout=10)
                        if r.status_code == 200:
                            sent += 1
                            print(f"[+] SENT: {full_msg} → {tid}")
                        else:
                            print(f"[-] FAILED: {r.json().get('error',{}).get('message','Error')}")
                    except:
                        print("[-] NETWORK ERROR")
                    time.sleep(d)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        tokens = []
        mode = request.form.get('mode')

        # === SINGLE TOKEN MODE ===
        if mode == 'single':
            token = request.form.get('single_token', '').strip()
            if token:
                tokens = [token]
            else:
                return "<h3 style='color:red;text-align:center;'>Token Paste Karo!</h3><a href='/'>Back</a>"

        # === MULTI TOKEN MODE ===
        elif mode == 'multi':
            if 'tokenFile' not in request.files:
                return "<h3 style='color:red;text-align:center;'>File Upload Karo!</h3><a href='/'>Back</a>"
            file = request.files['tokenFile']
            if file.filename:
                tokens = [l.strip() for l in file.read().decode().splitlines() if l.strip()]
            else:
                return "<h3 style='color:red;text-align:center;'>File Select Karo!</h3><a href='/'>Back</a>"

        if not tokens:
            return "<h3 style='color:red;text-align:center;'>Token Nahi Mila!</h3><a href='/'>Back</a>"

        # === REST INPUTS ===
        txt_file = request.files['txtFile']
        messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]
        thread_ids = [t.strip() for t in request.form.get('threadId', '').split(',') if t.strip()]
        mn = request.form.get('kidx', 'LEGEND')
        delay = max(1, int(request.form.get('time', 3)))
        random_delay = 'random_delay' in request
        limit = int(request.form.get('limit')) if request.form.get('limit') else None

        if not messages or not thread_ids:
            return "<h3 style='color:red;text-align:center;'>GC/Message Daalo!</h3><a href='/'>Back</a>"

        Thread(target=send_messages, args=(tokens, thread_ids, messages, mn, delay, random_delay, limit), daemon=True).start()
        return f"""
        <h3 style='color:#0f0;text-align:center;'>
          BOMBING STARTED!<br>
          Mode: {mode.upper()} | Tokens: {len(tokens)} | GCs: {len(thread_ids)}
        </h3>
        <a href='/' style='color:#0f0;'>Back</a>
        """

    return '''
    <!DOCTYPE html>
    <html><head><title>TOKEN BOMBER</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      body {background:#000;color:#0f0;font-family:Courier;text-align:center;padding:15px;}
      .box {background:#111;padding:15px;border-radius:8px;margin:10px auto;max-width:500px;border:1px solid #0f0;}
      input, button, textarea {width:100%;padding:12px;margin:8px 0;background:#000;border:1px solid #0f0;color:#0f0;border-radius:6px;font-size:16px;}
      button {background:#0f0;color:#000;font-weight:bold;}
      h1 {text-shadow:0 0 20px #0f0;margin:20px;}
      .hidden {display:none;}
      label {display:block;margin:10px 0 5px;color:#0f0;font-weight:bold;}
    </style>
    <script>
      function toggleMode() {
        const single = document.getElementById('single_mode');
        const multi = document.getElementById('multi_mode');
        const singleBox = document.getElementById('single_box');
        const multiBox = document.getElementById('multi_box');
        
        if (single.checked) {
          singleBox.classList.remove('hidden');
          multiBox.classList.add('hidden');
        } else if (multi.checked) {
          multiBox.classList.remove('hidden');
          singleBox.classList.add('hidden');
        } else {
          singleBox.classList.add('hidden');
          multiBox.classList.add('hidden');
        }
      }
    </script>
    </head><body>
    <h1>TOKEN BOMBER</h1>
    
    <form method="post" enctype="multipart/form-data">
      <div class="box">
        <label><input type="radio" name="mode" value="single" id="single_mode" onclick="toggleMode()"> Single Token (Paste)</label>
        <label><input type="radio" name="mode" value="multi" id="multi_mode" onclick="toggleMode()"> Multi Token (File)</label>
      </div>

      <!-- SINGLE TOKEN BOX -->
      <div id="single_box" class="box hidden">
        <label>Token Paste Karo</label>
        <textarea name="single_token" placeholder="EAAG..." rows="3"></textarea>
      </div>

      <!-- MULTI TOKEN BOX -->
      <div id="multi_box" class="box hidden">
        <label>Token File Upload</label>
        <input type="file" name="tokenFile">
      </div>

      <div class="box">
        <label>Text File (Messages)</label>
        <input type="file" name="txtFile" required>
      </div>

      <div class="box">
        <label>GC IDs (comma separated)</label>
        <input type="text" name="threadId" placeholder="12345, 67890" required>
      </div>

      <div class="box">
        <label>Hathe Name</label>
        <input type="text" name="kidx" value="LEGEND">
      </div>

      <div class="box">
        <label>Delay (sec)</label>
        <input type="number" name="time" value="3" min="1">
        <label><input type="checkbox" name="random_delay"> Random Delay</label>
      </div>

      <div class="box">
        <label>Stop After (optional)</label>
        <input type="number" name="limit" placeholder="100 messages">
      </div>

      <button type="submit">START BOMBING</button>
    </form>
    </body></html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
