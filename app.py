from flask import Flask, request, Response
import requests
from threading import Thread, Event
import time
import json
from collections import deque
import threading
import random

app = Flask(__name__)
app.debug = True

# Headers
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
}

# Global
stop_event = Event()
threads = []  # Ab yeh list append karegi, overwrite nahi!
log_lock = threading.Lock()
log_messages = deque(maxlen=1000)
stats = {"sent": 0, "failed": 0, "start_time": None, "total_target": 0}
token_status = {}
typing_active = False

# Logging
def log(data):
    with log_lock:
        if isinstance(data, dict):
            log_messages.append(data)
        else:
            log_messages.append({"type": "log", "msg": str(data), "time": time.strftime('%H:%M:%S')})

def update_stats(success=True):
    with log_lock:
        if success: stats["sent"] += 1
        else: stats["failed"] += 1

def set_typing(on=True, thread_id=None):
    global typing_active
    typing_active = on
    log({"type": "typing", "status": "on" if on else "off", "thread": thread_id})

# Send Message Function
def send_messages(access_tokens, thread_id, mn, time_interval, messages, random_delay=False, limit=None):
    global token_status
    start_time = time.time()
    total_msgs = len(messages) * len(access_tokens) * 10
    stats["total_target"] += total_msgs
    stats["start_time"] = stats["start_time"] or start_time
    token_status.update({t[:10]: "active" for t in access_tokens})

    round_count = 0
    while not stop_event.is_set() and (limit is None or stats["sent"] < limit):
        round_count += 1
        for msg_idx, message1 in enumerate(messages):
            if stop_event.is_set(): break
            set_typing(True, thread_id)
            time.sleep(0.5)
            for token in access_tokens:
                if stop_event.is_set(): break
                full_msg = f"{mn} {message1}"
                url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                params = {'access_token': token, 'message': full_msg}
                delay = random.uniform(1, 5) if random_delay else time_interval

                try:
                    r = requests.post(url, data=params, headers=headers, timeout=10)
                    if r.status_code == 200:
                        log({"type": "success", "msg": full_msg[:50], "token": token[:10], "thread": thread_id})
                        update_stats(True)
                    else:
                        error_msg = r.json().get("error", {}).get("message", "Unknown")
                        log({"type": "fail", "msg": f"{r.status_code}: {error_msg[:40]}", "token": token[:10], "thread": thread_id})
                        update_stats(False)
                        if "invalid" in error_msg.lower():
                            token_status[token[:10]] = "dead"
                except Exception as e:
                    log({"type": "error", "msg": f"Error: {str(e)[:40]}", "thread": thread_id})
                    update_stats(False)
                time.sleep(delay)
            set_typing(False, thread_id)
        if limit and stats["sent"] >= limit:
            log({"type": "info", "msg": f"Limit reached: {limit}", "thread": thread_id})
            break

# SSE Logs
@app.route('/logs')
def stream_logs():
    def generate():
        last_idx = 0
        while True:
            with log_lock:
                if last_idx < len(log_messages):
                    for i in range(last_idx, len(log_messages)):
                        yield f"data: {json.dumps(log_messages[i])}\n\n"
                    last_idx = len(log_messages)
                if stats["start_time"]:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["sent"] / elapsed if elapsed > 0 else 0
                    progress = min(100, (stats["sent"] / stats["total_target"]) * 100) if stats["total_target"] > 0 else 0
                    yield f"data: {json.dumps({'type': 'stats', 'sent': stats['sent'], 'failed': stats['failed'], 'speed': round(speed,1), 'progress': round(progress,1)})}\n\n"
                yield f"data: {json.dumps({'type': 'token_status', 'data': token_status})}\n\n"
            time.sleep(0.6)
    return Response(generate(), mimetype="text/event-stream")

# Main Route
@app.route('/', methods=['GET', 'POST'])
def index():
    global threads
    if request.method == 'POST':
        # Files
        token_file = request.files['tokenFile']
        access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
        txt_file = request.files['txtFile']
        messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

        # Form data
        thread_id_input = request.form.get('threadId', '')
        thread_ids = [tid.strip() for tid in thread_id_input.split(',') if tid.strip()]
        mn = request.form.get('kidx', 'LEGEND')
        time_interval = max(1, int(request.form.get('time', 3)))
        random_delay = 'random_delay' in request.form
        limit = request.form.get('limit')
        limit = int(limit) if limit and limit.isdigit() else None

        if not access_tokens or not thread_ids or not messages:
            log({"type": "error", "msg": "Missing tokens, thread IDs, or messages"})
            return HTML

        # MULTIPLE THREADS — NO OVERWRITE
        for tid in thread_ids:
            thread = Thread(
                target=send_messages,
                args=(access_tokens, tid, mn, time_interval, messages, random_delay, limit)
            )
            thread.start()
            threads.append(thread)
            log({"type": "info", "msg": f"Bombing STARTED in GC: {tid}"})

    return HTML

# Stop All
@app.route('/stop', methods=['POST'])
def stop():
    stop_event.set()
    for t in threads:
        if t.is_alive():
            t.join(timeout=2)
    threads.clear()
    log({"type": "info", "msg": "All bombings STOPPED!"})
    return 'All stopped.'

# HTML Template
HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LEGEND BOMBER</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #111 url('https://i.imgur.com/92rqE1X.jpeg') center/cover; color: #fff; font-family: 'Segoe UI'; min-height: 100vh; }
    .container { max-width: 420px; padding: 20px; }
    .form-control { background: rgba(0,0,0,0.7); border: 1px solid #444; color: #fff; border-radius: 8px; }
    .form-control::placeholder { color: #aaa; }
    .btn-submit { width: 100%; margin: 8px 0; }
    .console { background: #000; color: #0f0; padding: 15px; border-radius: 10px; height: 220px; overflow-y: auto; font-size: 13px; margin-top: 15px; border: 1px solid #333; }
    .console::-webkit-scrollbar { width: 6px; }
    .console::-webkit-scrollbar-thumb { background: #444; }
    .progress { height: 8px; background: #333; border-radius: 4px; }
    .progress-bar { background: linear-gradient(90deg, #0f0, #0c0); }
    .typing { color: #0f0; font-style: italic; display: none; }
    .token-list { max-height: 80px; overflow-y: auto; background: #000; padding: 8px; border-radius: 6px; font-size: 12px; }
    .dark-mode { filter: invert(1) hue-rotate(180deg); }
    .glow-btn { box-shadow: 0 0 8px rgba(0,255,0,0.5); }
  </style>
</head>
<body>
  <div class="container text-center">
    <h1 class="mt-3 mb-4">LEGEND BOMBER</h1>

    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label class="form-label">TOKEN FILE</label>
        <input type="file" class="form-control" name="tokenFile" required>
      </div>
      <div class="mb-3">
        <label class="form-label">THREAD IDs (comma se alag)</label>
        <input type="text" class="form-control" name="threadId" placeholder="12345, 67890" required>
        <small class="text-muted">Ek ya zyada GC IDs daal sakte ho</small>
      </div>
      <div class="mb-3">
        <label class="form-label">HATHE NAME</label>
        <input type="text" class="form-control" name="kidx" value="LEGEND" required>
      </div>
      <div class="mb-3">
        <label class="form-label">DELAY (sec)</label>
        <input type="number" class="form-control" name="time" value="3" min="1" required>
      </div>
      <div class="form-check mb-2">
        <input class="form-check-input" type="checkbox" name="random_delay">
        <label class="form-check-label text-light">Random Delay (1-5s)</label>
      </div>
      <div class="mb-3">
        <label class="form-label">STOP AFTER (messages)</label>
        <input type="number" class="form-control" name="limit" placeholder="Optional">
      </div>
      <div class="mb-3">
        <label class="form-label">TEXT FILE</label>
        <input type="file" class="form-control" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-success btn-submit glow-btn">START IN ALL GCs</button>
    </form>

    <form method="post" action="/stop" class="mt-2">
      <button type="submit" class="btn btn-danger btn-submit glow-btn">STOP ALL</button>
    </form>

    <!-- Stats -->
    <div class="mt-3 p-2 bg-dark rounded">
      <div>Sent: <span id="sent">0</span> | Failed: <span id="failed">0</span> | Speed: <span id="speed">0</span>/sec</div>
      <div class="progress mt-2">
        <div id="progressBar" class="progress-bar" style="width:0%">0%</div>
      </div>
    </div>

    <!-- Typing -->
    <div id="typing" class="typing mt-2">Typing in <span id="typingThread"></span>...</div>

    <!-- Token Status -->
    <div class="mt-3">
      <b>Token Status:</b>
      <div id="tokenList" class="token-list mt-1"></div>
    </div>

    <!-- Controls -->
    <div class="mt-3 d-flex gap-2 justify-content-center flex-wrap">
      <button onclick="copyLogs()" class="btn btn-sm btn-outline-light">Copy</button>
      <button onclick="downloadLogs()" class="btn btn-sm btn-outline-success">Download</button>
      <button onclick="clearConsole()" class="btn btn-sm btn-outline-warning">Clear</button>
      <button onclick="toggleDark()" class="btn btn-sm btn-outline-secondary">Dark Mode</button>
      <button onclick="startVoice()" class="btn btn-sm btn-primary">Voice</button>
    </div>

    <!-- Search -->
    <div class="mt-3">
      <input type="text" id="search" placeholder="Search logs..." class="form-control form-control-sm">
    </div>

    <!-- Console -->
    <div id="console" class="console mt-2"></div>
  </div>

  <script>
    const consoleDiv = document.getElementById('console');
    const eventSource = new EventSource('/logs');
    const recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    let recog = recognition ? new recognition() : null;
    let darkMode = false;

    if (recog) {
      recog.continuous = false;
      recog.lang = 'en-US';
      recog.onresult = e => {
        const cmd = e.results[0][0].transcript.toLowerCase();
        if (cmd.includes('start')) submitForm();
        if (cmd.includes('stop')) document.querySelector('[action="/stop"] button').click();
      };
    }

    function startVoice() {
      if (recog) { alert('Say: "start" or "stop"'); recog.start(); }
      else alert('Voice not supported');
    }

    function submitForm() { document.querySelector('form').submit(); }

    function addLog(data) {
      const line = document.createElement('div');
      let color = '#fff', icon = '', thread = data.thread ? ` [GC:${data.thread}]` : '';
      if (data.type === 'success') { color = '#0f0'; icon = '[Success]'; }
      else if (data.type === 'fail') { color = '#f00'; icon = '[Failed]'; }
      else if (data.type === 'error') { color = '#ff0'; icon = '[Error]'; }
      else if (data.type === 'info') { color = '#0ff'; icon = '[Info]'; }
      line.innerHTML = `<span style="color:${color}">${icon} [${data.time || ''}] ${data.msg || ''}${thread}</span>`;
      consoleDiv.appendChild(line);
      consoleDiv.scrollTop = consoleDiv.scrollHeight;
    }

    eventSource.onmessage = function(e) {
      const data = JSON.parse(e.data);
      if (data.type === 'stats') {
        document.getElementById('sent').textContent = data.sent;
        document.getElementById('failed').textContent = data.failed;
        document.getElementById('speed').textContent = data.speed;
        document.getElementById('progressBar').style.width = data.progress + '%';
        document.getElementById('progressBar').textContent = data.progress.toFixed(1) + '%';
      }
      else if (data.type === 'typing') {
        const el = document.getElementById('typing');
        el.style.display = data.status === 'on' ? 'block' : 'none';
        document.getElementById('typingThread').textContent = data.thread || 'GC';
      }
      else if (data.type === 'token_status') {
        const list = document.getElementById('tokenList');
        list.innerHTML = '';
        for (const [t, s] of Object.entries(data.data)) {
          list.innerHTML += `<div style="color:${s==='active'?'#0f0':'#f00'}">${t}... [${s.toUpperCase()}]</div>`;
        }
      }
      else addLog(data);
    };

    document.getElementById('search').addEventListener('keyup', function() {
      const q = this.value.toLowerCase();
      Array.from(consoleDiv.children).forEach(l => {
        l.style.display = l.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      });
    });

    function copyLogs() { navigator.clipboard.writeText(Array.from(consoleDiv.children).map(l => l.textContent).join('\\n')); }
    function downloadLogs() {
      const blob = new Blob([Array.from(consoleDiv.children).map(l => l.textContent).join('\\n')], {type: 'text/plain'});
      const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'legend_bomber.txt'; a.click();
    }
    function clearConsole() { if(confirm('Clear?')) consoleDiv.innerHTML = ''; }
    function toggleDark() {
      darkMode = !darkMode;
      document.body.classList.toggle('dark-mode', darkMode);
    }
  </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
