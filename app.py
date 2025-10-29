from flask import Flask, request, Response
import requests
from threading import Thread, Event
import time
import json
from collections import deque
import threading

app = Flask(__name__)
app.debug = True

headers = {
    'Connection': 'keep-alive',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9',
}

stop_event = Event()
threads = []

# Thread-safe log & stats
log_lock = threading.Lock()
log_messages = deque(maxlen=500)
stats = {"sent": 0, "failed": 0, "start_time": None}

def log(data):
    with log_lock:
        if isinstance(data, dict):
            log_messages.append(data)
        else:
            log_messages.append({"type": "log", "msg": data, "time": time.strftime('%H:%M:%S')})

def update_stats(success=True):
    with log_lock:
        if success:
            stats["sent"] += 1
        else:
            stats["failed"] += 1

def send_messages(access_tokens, thread_id, mn, time_interval, messages):
    stats["start_time"] = time.time()
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set(): break
            for access_token in access_tokens:
                if stop_event.is_set(): break
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                full_msg = f"{mn} {message1}"
                params = {'access_token': access_token, 'message': full_msg}
                try:
                    r = requests.post(api_url, data=params, headers=headers, timeout=10)
                    if r.status_code == 200:
                        log({"type": "success", "msg": f"Sent: {full_msg[:40]}...", "token": access_token[:8]})
                        update_stats(True)
                    else:
                        log({"type": "fail", "msg": f"Failed ({r.status_code}): {full_msg[:30]}...", "token": access_token[:8]})
                        update_stats(False)
                except Exception as e:
                    log({"type": "error", "msg": f"Error: {str(e)[:50]}"})
                    update_stats(False)
                time.sleep(time_interval)

# SSE Stream
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
                # Send stats
                if stats["start_time"]:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["sent"] / elapsed if elapsed > 0 else 0
                    yield f"data: {json.dumps({'type': 'stats', 'sent': stats['sent'], 'failed': stats['failed'], 'speed': round(speed, 1)})}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")

@app.route('/', methods=['GET', 'POST'])
def index():
    global threads
    if request.method == 'POST':
        token_file = request.files['tokenFile']
        access_tokens = [line.strip() for line in token_file.read().decode().splitlines() if line.strip()]

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = max(1, int(request.form.get('time', 3)))

        txt_file = request.files['txtFile']
        messages = [line.strip() for line in txt_file.read().decode().splitlines() if line.strip()]

        if access_tokens and thread_id and messages:
            if not any(t.is_alive() for t in threads):
                stop_event.clear()
                with log_lock:
                    log_messages.clear()
                    stats.update({"sent": 0, "failed": 0, "start_time": None})
                log({"type": "info", "msg": "Bot Started!"})
                thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages))
                thread.start()
                threads = [thread]

    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>LEGEND BOY ERROR</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    body {
        background: linear-gradient(135deg, #000, #111);
        background-image: url('https://i.imgur.com/92rqE1X.jpeg');
        background-size: cover;
        color: #0f0;
        font-family: 'Courier New', monospace;
        min-height: 100vh;
    }
    .container { max-width: 400px; padding: 20px; }
    .form-control {
        background: rgba(0,0,0,0.6); border: 1px solid #0f0; color: #0f0; border-radius: 8px;
        box-shadow: 0 0 5px #0f0;
    }
    .form-control::placeholder { color: #0a0; }
    .btn-submit { width: 100%; margin: 8px 0; }
    .console {
        background: #000; color: #0f0; padding: 15px; border-radius: 10px; height: 220px; overflow-y: auto;
        font-size: 13px; margin-top: 15px; border: 1px solid #0f0; box-shadow: 0 0 15px #0f0;
        animation: glow 2s infinite alternate;
    }
    @keyframes glow {
        from { box-shadow: 0 0 10px #0f0; }
        to { box-shadow: 0 0 25px #0f0, 0 0 35px #0f0; }
    }
    .console::-webkit-scrollbar { width: 8px; }
    .console::-webkit-scrollbar-track { background: #111; }
    .console::-webkit-scrollbar-thumb { background: #0f0; border-radius: 4px; }
    .stats { background: #111; padding: 10px; border-radius: 8px; border: 1px solid #0f0; font-weight: bold; }
    .search-box { background: #000; border: 1px solid #0f0; color: #0f0; }
    .glow-btn { box-shadow: 0 0 10px #0f0; }
    .glow-btn:hover { box-shadow: 0 0 20px #0f0; }
  </style>
</head>
<body>
  <div class="container text-center">
    <h1 class="mt-3 mb-4 text-shadow" style="text-shadow: 0 0 10px #0f0;">LEGEND BOY ERROR</h1>

    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label class="form-label">TOKEN FILE</label>
        <input type="file" class="form-control" name="tokenFile" required>
      </div>
      <div class="mb-3">
        <label class="form-label">CONVO ID</label>
        <input type="text" class="form-control" name="threadId" required>
      </div>
      <div class="mb-3">
        <label class="form-label">HATHE NAME</label>
        <input type="text" class="form-control" name="kidx" required>
      </div>
      <div class="mb-3">
        <label class="form-label">DELAY (sec)</label>
        <input type="number" class="form-control" name="time" value="3" min="1" required>
      </div>
      <div class="mb-3">
        <label class="form-label">TEXT FILE</label>
        <input type="file" class="form-control" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-success btn-submit glow-btn">START BOMBING</button>
    </form>

    <form method="post" action="/stop" class="mt-2">
      <button type="submit" class="btn btn-danger btn-submit glow-btn">STOP NOW</button>
    </form>

    <!-- Stats -->
    <div class="stats mt-3 text-center">
      Sent: <span id="sent">0</span> | 
      Failed: <span id="failed">0</span> | 
      Speed: <span id="speed">0</span>/sec
    </div>

    <!-- Search -->
    <div class="mt-3">
      <input type="text" id="search" placeholder="Search logs..." class="form-control search-box">
    </div>

    <!-- Console -->
    <div class="mt-2">
      <div class="d-flex justify-content-between mb-2">
        <button onclick="copyLogs()" class="btn btn-sm btn-outline-light glow-btn">Copy</button>
        <button onclick="downloadLogs()" class="btn btn-sm btn-outline-success glow-btn">Download</button>
        <button onclick="clearConsole()" class="btn btn-sm btn-outline-warning glow-btn">Clear</button>
      </div>
      <div id="console" class="console"></div>
    </div>
  </div>

  <script>
    const consoleDiv = document.getElementById('console');
    const eventSource = new EventSource('/logs');
    const failSound = new Audio('https://assets.mixkit.co/sfx/preview/mixkit-alarm-digital-clock-beep-989.mp3');

    function addLog(data) {
      const line = document.createElement('div');
      const time = data.time ? `[${data.time}] ` : '';
      let color = '#0f0';
      let icon = '';

      if (data.type === 'success') { color = '#0f0'; icon = '✓'; }
      else if (data.type === 'fail') { color = '#f00'; icon = '✗'; failSound.play(); }
      else if (data.type === 'error') { color = '#ff0'; icon = '⚠'; }
      else if (data.type === 'info') { color = '#0ff'; icon = 'ℹ'; }

      line.innerHTML = `<span style="color:${color}">${icon} ${time}${data.msg || data}</span>`;
      consoleDiv.appendChild(line);
      consoleDiv.scrollTop = consoleDiv.scrollHeight;
    }

    eventSource.onmessage = function(e) {
      const data = JSON.parse(e.data);
      if (data.type === 'stats') {
        document.getElementById('sent').textContent = data.sent;
        document.getElementById('failed').textContent = data.failed;
        document.getElementById('speed').textContent = data.speed;
      } else {
        addLog(data);
      }
    };

    document.getElementById('search').addEventListener('keyup', function() {
      const query = this.value.toLowerCase();
      Array.from(consoleDiv.children).forEach(line => {
        line.style.display = line.textContent.toLowerCase().includes(query) ? 'block' : 'none';
      });
    });

    function copyLogs() {
      const text = Array.from(consoleDiv.children).map(l => l.textContent).join('\\n');
      navigator.clipboard.writeText(text);
      alert('Logs copied!');
    }

    function downloadLogs() {
      const text = Array.from(consoleDiv.children).map(l => l.textContent).join('\\n');
      const blob = new Blob([text], {type: 'text/plain'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'legend_bomber_log.txt'; a.click();
    }

    function clearConsole() {
      if (confirm('Clear console?')) consoleDiv.innerHTML = '';
    }
  </script>
</body>
</html>
    '''

@app.route('/stop', methods=['POST'])
def stop():
    stop_event.set()
    log({"type": "info", "msg": "Bot Stopped by User."})
    return 'Stopped.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
