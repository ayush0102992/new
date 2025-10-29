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

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

# Global stop event
stop_event = Event()

# Per-thread logs: {thread_id: deque()}
thread_logs = {}
logs_lock = threading.Lock()

# Active threads
active_threads = {}

def log_to_thread(thread_id, data):
    with logs_lock:
        if thread_id not in thread_logs:
            thread_logs[thread_id] = deque(maxlen=200)
        thread_logs[thread_id].append(data)

def send_to_thread(access_tokens, thread_id, mn, time_interval, messages, random_delay=False):
    stats = {"sent": 0, "failed": 0}
    log_to_thread(thread_id, {"type": "info", "msg": f"Thread {thread_id} started!"})

    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set(): break
            for token in access_tokens:
                if stop_event.is_set(): break
                full_msg = f"{mn} {message1}"
                url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                params = {'access_token': token, 'message': full_msg}
                delay = random.uniform(1, 5) if random_delay else time_interval

                try:
                    r = requests.post(url, data=params, headers=headers, timeout=10)
                    if r.status_code == 200:
                        log_to_thread(thread_id, {"type": "success", "msg": full_msg[:50]})
                        stats["sent"] += 1
                    else:
                        log_to_thread(thread_id, {"type": "fail", "msg": f"{r.status_code}"})
                        stats["failed"] += 1
                except:
                    log_to_thread(thread_id, {"type": "error", "msg": "Request failed"})
                    stats["failed"] += 1
                time.sleep(delay)

    log_to_thread(thread_id, {"type": "info", "msg": "Thread stopped."})

@app.route('/logs/<thread_id>')
def stream_thread_logs(thread_id):
    def generate():
        last_idx = -1
        while True:
            with logs_lock:
                if thread_id in thread_logs and last_idx < len(thread_logs[thread_id]) - 1:
                    logs = thread_logs[thread_id]
                    for i in range(last_idx + 1, len(logs)):
                        yield f"data: {json.dumps(logs[i])}\n\n"
                    last_idx = len(logs) - 1
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")

@app.route('/', methods=['GET', 'POST'])
def index():
    global active_threads
    if request.method == 'POST':
        # Files
        token_file = request.files['tokenFile']
        access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]

        thread_ids = request.form.get('threadIds').strip().splitlines()
        thread_ids = [tid.strip() for tid in thread_ids if tid.strip()]

        mn = request.form.get('kidx')
        time_interval = max(1, int(request.form.get('time', 3)))
        random_delay = 'random_delay' in request.form

        txt_file = request.files['txtFile']
        messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

        if access_tokens and thread_ids and messages:
            stop_event.clear()
            with logs_lock:
                thread_logs.clear()

            # Start one thread per thread_id
            for tid in thread_ids:
                if tid not in active_threads:
                    t = Thread(target=send_to_thread, args=(access_tokens, tid, mn, time_interval, messages, random_delay))
                    t.daemon = True
                    t.start()
                    active_threads[tid] = t
                    log_to_thread(tid, {"type": "info", "msg": f"Bombing started with {len(access_tokens)} tokens"})

    return '''
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Multi-Thread Bomber</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { background: #111 url('https://i.imgur.com/92rqE1X.jpeg') center/cover; color: #fff; font-family: 'Courier New'; }
    .container { max-width: 500px; }
    .form-control { background: #000; border: 1px solid #0f0; color: #0f0; }
    .console-tab { background: #000; color: #0f0; border: 1px solid #333; height: 250px; overflow-y: auto; padding: 10px; font-size: 13px; }
    .nav-tabs .nav-link { color: #0f0; background: #111; border: 1px solid #0f0; }
    .nav-tabs .nav-link.active { background: #0f0; color: #000; }
    textarea { height: 100px; }
  </style>
</head>
<body>
<div class="container mt-4">
  <h1 class="text-center mb-4" style="text-shadow: 0 0 10px #0f0;">LEGEND MULTI-THREAD</h1>

  <form method="post" enctype="multipart/form-data">
    <div class="mb-3">
      <label>TOKEN FILE</label>
      <input type="file" name="tokenFile" class="form-control" required>
    </div>
    <div class="mb-3">
      <label>THREAD IDs (One per line)</label>
      <textarea name="threadIds" class="form-control" placeholder="t_10001234...\nt_10005678..." required></textarea>
    </div>
    <div class="mb-3">
      <label>HATHE NAME</label>
      <input type="text" name="kidx" class="form-control" required>
    </div>
    <div class="mb-3">
      <label>DELAY (sec)</label>
      <input type="number" name="time" class="form-control" value="3" min="1">
    </div>
    <div class="form-check mb-3">
      <input type="checkbox" name="random_delay" class="form-check-input">
      <label class="form-check-label">Random Delay</label>
    </div>
    <div class="mb-3">
      <label>TEXT FILE</label>
      <input type="file" name="txtFile" class="form-control" required>
    </div>
    <button type="submit" class="btn btn-success w-100">START ALL THREADS</button>
  </form>

  <form method="post" action="/stop" class="mt-2">
    <button type="submit" class="btn btn-danger w-100">STOP ALL</button>
  </form>

  <!-- Tabs for Each Thread Console -->
  <div class="mt-4">
    <ul class="nav nav-tabs" id="threadTabs"></ul>
    <div class="tab-content mt-2" id="threadConsoles"></div>
  </div>
</div>

<script>
  const tabs = document.getElementById('threadTabs');
  const consoles = document.getElementById('threadConsoles');

  function addThreadTab(threadId) {
    const tabId = 'tab-' + threadId;
    const consoleId = 'console-' + threadId;

    // Tab
    const li = document.createElement('li');
    li.className = 'nav-item';
    li.innerHTML = `<a class="nav-link" href="#" data-thread="${threadId}">${threadId.slice(0,12)}...</a>`;
    tabs.appendChild(li);

    // Console
    const div = document.createElement('div');
    div.className = 'tab-pane console-tab';
    div.id = consoleId;
    consoles.appendChild(div);

    // SSE
    const es = new EventSource(`/logs/${threadId}`);
    es.onmessage = e => {
      const data = JSON.parse(e.data);
      const line = document.createElement('div');
      let color = '#0f0';
      if (data.type === 'fail') color = '#f00';
      if (data.type === 'error') color = '#ff0';
      if (data.type === 'info') color = '#0ff';
      line.innerHTML = `<span style="color:${color}">[${data.time||''}] ${data.msg}</span>`;
      div.appendChild(line);
      div.scrollTop = div.scrollHeight;
    };

    // Click to switch
    li.querySelector('a').onclick = () => {
      document.querySelectorAll('.tab-pane').forEach(d => d.style.display = 'none');
      div.style.display = 'block';
      document.querySelectorAll('.nav-link').forEach(a => a.classList.remove('active'));
      li.querySelector('a').classList.add('active');
    };

    // Auto-select first
    if (tabs.children.length === 1) li.querySelector('a').click();
  }

  // Auto-add tabs when threads start
  setInterval(() => {
    fetch('/active_threads').then(r => r.json()).then(data => {
      data.forEach(tid => {
        if (!document.getElementById('tab-' + tid)) {
          addThreadTab(tid);
        }
      });
    });
  }, 2000);
</script>
</body>
</html>
    '''

@app.route('/active_threads')
def active_threads_list():
    return json.dumps(list(active_threads.keys()))

@app.route('/stop', methods=['POST'])
def stop():
    stop_event.set()
    return 'All threads stopped.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
