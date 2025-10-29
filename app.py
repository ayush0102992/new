from flask import Flask, request, Response, render_template_string, redirect, session
import requests
from threading import Thread, Event
import time
import json
from collections import deque
import threading
import random
import uuid

app = Flask(__name__)
app.secret_key = 'legend_bomber_secret_2025'

# === ADMIN CREDENTIALS ===
ADMIN_USER = "legend"
ADMIN_PASS = "error404"

# === STORAGE ===
tasks = {}
task_lock = threading.Lock()

headers = {'User-Agent': 'Mozilla/50 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

def generate_task_id():
    return f"TASK-{str(uuid.uuid4())[:8].upper()}"

def task_log(task_id, data):
    with task_lock:
        if task_id in tasks:
            if isinstance(data, dict):
                tasks[task_id]['logs'].append(data)
            else:
                tasks[task_id]['logs'].append({"type": "log", "msg": str(data), "time": time.strftime('%H:%M:%S')})

def send_messages(task_id):
    data = tasks[task_id]
    stop_event = data['stop_event']
    stats = data['stats']
    token_status = data['token_status']
    tokens = data['tokens']
    thread_ids = data['thread_ids']
    messages = data['messages']
    mn = data['mn']
    time_interval = data['time_interval']
    random_delay = data['random_delay']
    limit = data['limit']

    stats["start_time"] = time.time()
    stats["total_target"] = len(messages) * len(tokens) * len(thread_ids) * 10
    token_status.update({t[:10]: "active" for t in tokens})

    while not stop_event.is_set() and (limit is None or stats["sent"] < limit):
        for tid in thread_ids:
            if stop_event.is_set(): break
            for msg in messages:
                if stop_event.is_set(): break
                full_msg = f"{mn} {msg}"
                for token in tokens:
                    if stop_event.is_set(): break
                    url = f'https://graph.facebook.com/v15.0/t_{tid}/'
                    params = {'access_token': token, 'message': full_msg}
                    delay = random.uniform(1, 5) if random_delay else time_interval
                    try:
                        r = requests.post(url, data=params, headers=headers, timeout=10)
                        if r.status_code == 200:
                            task_log(task_id, {"type": "success", "msg": full_msg, "token": token, "thread": tid})
                            stats["sent"] += 1
                        else:
                            err = r.json().get("error", {}).get("message", "Unknown")
                            task_log(task_id, {"type": "fail", "msg": err, "token": token, "thread": tid})
                            stats["failed"] += 1
                            if "invalid" in err.lower():
                                token_status[token[:10]] = "dead"
                    except Exception as e:
                        task_log(task_id, {"type": "error", "msg": str(e), "thread": tid})
                        stats["failed"] += 1
                    time.sleep(delay)

@app.route('/console/stream/<task_id>')
def stream(task_id):
    def gen():
        last = -1
        while True:
            with task_lock:
                if task_id not in tasks: break
                logs = tasks[task_id]['logs']
                if last < len(logs) - 1:
                    for i in range(last + 1, len(logs)):
                        yield f"data: {json.dumps(logs[i])}\n\n"
                    last = len(logs) - 1
                stats = tasks[task_id]['stats']
                if stats["start_time"]:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["sent"] / elapsed if elapsed > 0 else 0
                    prog = min(100, (stats["sent"] / stats["total_target"]) * 100) if stats["total_target"] > 0 else 0
                    yield f"data: {json.dumps({'type': 'stats', 'sent': stats['sent'], 'failed': stats['failed'], 'speed': round(speed,1), 'progress': round(prog,1)})}\n\n"
                yield f"data: {json.dumps({'type': 'token_status', 'data': tasks[task_id]['token_status']})}\n\n"
            time.sleep(0.6)
    return Response(gen(), mimetype="text/event-stream")

# === ADMIN LOGIN ===
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        if request.form.get('user') == ADMIN_USER and request.form.get('pass') == ADMIN_PASS:
            session['admin'] = True
            return redirect('/admin/dashboard')
        return "Wrong credentials"

    if session.get('admin'):
        return redirect('/admin/dashboard')

    return '''
    <form method="post" style="text-align:center;margin-top:100px;">
      <h2>ADMIN ROOM</h2>
      <input type="text" name="user" placeholder="Username" required><br><br>
      <input type="password" name="pass" placeholder="Password" required><br><br>
      <button type="submit">Login</button>
    </form>
    '''

# === ADMIN DASHBOARD ===
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/admin')

    with task_lock:
        task_list = []
        for tid, data in tasks.items():
            task_list.append({
                'id': tid,
                'threads': ', '.join(data['thread_ids']),
                'tokens': len(data['tokens']),
                'sent': data['stats']['sent'],
                'failed': data['stats']['failed'],
                'active': data.get('thread', None) and data['thread'].is_alive()
            })

    tasks_html = ""
    for t in task_list:
        tasks_html += f'''
        <div class="card mb-2">
          <div class="card-body">
            <b>{t['id']}</b> | GC: {t['threads']} | Tokens: {t['tokens']} | Sent: {t['sent']} | Failed: {t['failed']}
            <a href="/admin/view/{t['id']}" class="btn btn-sm btn-info">View</a>
            <form method="post" action="/admin/stop/{t['id']}" style="display:inline;">
              <button type="submit" class="btn btn-sm btn-danger">Stop</button>
            </form>
          </div>
        </div>
        '''

    return f'''
    <!DOCTYPE html>
    <html><head><title>ADMIN DASHBOARD</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head><body class="bg-dark text-white">
    <div class="container"><h2>ADMIN DASHBOARD</h2>
    <a href="/admin" class="btn btn-sm btn-secondary">Logout</a><hr>
    {tasks_html or "<p>No tasks running.</p>"}
    </div></body></html>
    '''

# === ADMIN VIEW TASK ===
@app.route('/admin/view/<task_id>')
def admin_view(task_id):
    if not session.get('admin') or task_id not in tasks:
        return redirect('/admin')

    data = tasks[task_id]
    tokens_html = "<br>".join([f"<code>{t}</code> [{data['token_status'].get(t[:10], 'unknown')}]" for t in data['tokens']])
    msgs_html = "<br>".join([f"<code>{m}</code>" for m in data['messages']])

    return f'''
    <!DOCTYPE html>
    <html><head><title>View {task_id}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>body {{background:#000;color:#0f0;font-family:Courier;}}</style>
    </head><body>
    <div class="container">
      <h3>TASK: {task_id}</h3>
      <b>GCs:</b> {', '.join(data['thread_ids'])}<br>
      <b>Full Tokens:</b><div style="background:#111;padding:10px;border-radius:5px;font-size:12px;">{tokens_html}</div>
      <b>Messages:</b><div style="background:#111;padding:10px;border-radius:5px;font-size:12px;">{msgs_html}</div>
      <hr>
      <div id="console" style="height:400px;overflow:auto;background:#000;color:#0f0;padding:10px;font-family:Courier;"></div>
      <form method="post" action="/admin/stop/{task_id}"><button class="btn btn-danger mt-2">STOP THIS TASK</button></form>
      <a href="/admin/dashboard" class="btn btn-secondary mt-2">Back</a>
    </div>
    <script>
      const es = new EventSource('/console/stream/{task_id}');
      const c = document.getElementById('console');
      es.onmessage = function(e) {{
        const d = JSON.parse(e.data);
        if (d.type !== 'stats' && d.type !== 'token_status') {{
          const line = document.createElement('div');
          line.style.color = d.type === 'success' ? '#0f0' : d.type === 'fail' ? '#f00' : '#ff0';
          line.textContent = `[${{d.type.toUpperCase()}}] ${{d.msg || ''}} [GC:${{d.thread}}]`;
          c.appendChild(line);
          c.scrollTop = c.scrollHeight;
        }}
      }};
    </script>
    </body></html>
    '''

# === ADMIN STOP TASK ===
@app.route('/admin/stop/<task_id>', methods=['POST'])
def admin_stop(task_id):
    if not session.get('admin') or task_id not in tasks:
        return redirect('/admin')
    tasks[task_id]['stop_event'].set()
    if 'thread' in tasks[task_id]:
        tasks[task_id]['thread'].join(timeout=2)
    task_log(task_id, {"type": "info", "msg": "STOPPED BY ADMIN"})
    return redirect('/admin/dashboard')

# === MAIN PAGE ===
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        token_file = request.files['tokenFile']
        tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
        txt_file = request.files['txtFile']
        messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]
        thread_ids = [t.strip() for t in request.form.get('threadId', '').split(',') if t.strip()]
        mn = request.form.get('kidx', 'LEGEND')
        time_interval = max(1, int(request.form.get('time', 3)))
        random_delay = 'random_delay' in request.form
        limit = int(request.form.get('limit')) if request.form.get('limit') else None

        task_id = generate_task_id()
        with task_lock:
            tasks[task_id] = {
                'logs': deque(maxlen=1000),
                'stats': {"sent": 0, "failed": 0, "start_time": None, "total_target": 0},
                'token_status': {},
                'tokens': tokens,
                'messages': messages,
                'thread_ids': thread_ids,
                'mn': mn,
                'time_interval': time_interval,
                'random_delay': random_delay,
                'limit': limit,
                'stop_event': Event()
            }
            task_log(task_id, {"type": "info", "msg": f"Task {task_id} STARTED"})

        thread = Thread(target=send_messages, args=(task_id,))
        thread.start()
        tasks[task_id]['thread'] = thread
        session['last_task'] = task_id

    last_task = session.get('last_task', '')
    return MAIN_HTML.replace('{{LAST_TASK}}', last_task)

@app.route('/console')
def console_page():
    task_id = request.args.get('task')
    if not task_id or task_id not in tasks:
        return '<form method="get" style="text-align:center;margin:100px;"><input type="text" name="task" placeholder="TASK-XXX" required><button>Open Console</button></form>'
    return CONSOLE_HTML.replace('{{TASK_ID}}', task_id)

@app.route('/stop_task', methods=['POST'])
def stop_task():
    task_id = request.form.get('task_id')
    if task_id in tasks:
        tasks[task_id]['stop_event'].set()
        tasks[task_id]['thread'].join(timeout=2)
        task_log(task_id, {"type": "info", "msg": "STOPPED BY USER"})
    return redirect('/')

# === HTML TEMPLATES ===
MAIN_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>LEGEND BOMBER</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background: #111 url('https://i.imgur.com/92rqE1X.jpeg') center/cover; color: #fff; }
  .container { max-width: 400px; padding: 20px; }
  .form-control { background: rgba(0,0,0,0.7); border: 1px solid #444; color: #fff; }
  .btn-submit { width: 100%; margin: 10px 0; }
</style></head><body>
<div class="container text-center">
  <h1 class="mt-3">LEGEND BOMBER</h1>
  <form method="post" enctype="multipart/form-data">
    <div class="mb-3"><label>TOKEN FILE</label><input type="file" name="tokenFile" class="form-control" required></div>
    <div class="mb-3"><label>THREAD IDs</label><input type="text" name="threadId" class="form-control" placeholder="12345, 67890" required></div>
    <div class="mb-3"><label>HATHE NAME</label><input type="text" name="kidx" class="form-control" value="LEGEND"></div>
    <div class="mb-3"><label>DELAY</label><input type="number" name="time" class="form-control" value="3" min="1"></div>
    <div class="form-check"><input type="checkbox" name="random_delay" class="form-check-input"><label class="form-check-label text-light">Random Delay</label></div>
    <div class="mb-3"><label>STOP AFTER</label><input type="number" name="limit" class="form-control" placeholder="Optional"></div>
    <div class="mb-3"><label>TEXT FILE</label><input type="file" name="txtFile" class="form-control" required></div>
    <button type="submit" class="btn btn-success btn-submit">START BOMBING</button>
  </form>

  <a href="/console" class="btn btn-primary mt-3">OPEN CONSOLE</a>

  <form method="post" action="/stop_task" class="mt-3">
    <input type="text" name="task_id" placeholder="TASK-XXX to stop" class="form-control">
    <button type="submit" class="btn btn-danger btn-submit mt-2">STOP TASK</button>
  </form>

  <div class="mt-3 p-2 bg-dark rounded">Last Task: <b>{{LAST_TASK}}</b></div>
</div>
</body></html>
'''

CONSOLE_HTML = '''
<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Console - {{TASK_ID}}</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body { background: #000; color: #0f0; font-family: 'Courier New'; }
  .console { height: 70vh; overflow-y: auto; padding: 15px; background: #111; border: 1px solid #0f0; }
</style></head><body>
<div class="container-fluid">
  <h3 class="text-center">CONSOLE: {{TASK_ID}}</h3>
  <div class="progress mb-2"><div id="progress" class="progress-bar" style="width:0%">0%</div></div>
  <div>Sent: <span id="sent">0</span> | Failed: <span id="failed">0</span> | Speed: <span id="speed">0</span>/s</div>
  <div id="tokenList" class="mt-2"></div>
  <div id="console" class="console mt-3"></div>
</div>
<script>
  const es = new EventSource('/console/stream/{{TASK_ID}}');
  const c = document.getElementById('console');
  es.onmessage = function(e) {
    const d = JSON.parse(e.data);
    if (d.type === 'stats') {
      document.getElementById('sent').textContent = d.sent;
      document.getElementById('failed').textContent = d.failed;
      document.getElementById('speed').textContent = d.speed;
      document.getElementById('progress').style.width = d.progress + '%';
      document.getElementById('progress').textContent = d.progress.toFixed(1) + '%';
    } else if (d.type === 'token_status') {
      const list = document.getElementById('tokenList');
      list.innerHTML = '<b>Tokens:</b><br>';
      for (const [t, s] of Object.entries(d.data)) {
        list.innerHTML += `<span style="color:${s==='active'?'#0f0':'#f00'}">${t}... [${s.toUpperCase()}]</span><br>`;
      }
    } else {
      const line = document.createElement('div');
      line.style.color = d.type === 'success' ? '#0f0' : d.type === 'fail' ? '#f00' : '#ff0';
      line.textContent = `[${d.type.toUpperCase()}] [${d.time || ''}] ${d.msg || ''} [GC:${d.thread || ''}]`;
      c.appendChild(line);
      c.scrollTop = c.scrollHeight;
    }
  };
</script>
</body></html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
