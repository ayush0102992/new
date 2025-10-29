from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import secrets
import logging

# LOGGING OFF
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
app.debug = False  # DEBUG OFF = NO EXTRA LOGS

# GLOBAL
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j)',
    'Accept': 'application/json',
    'referer': 'https://www.facebook.com'
}

# TASK & LOGS
tasks = {}
logs = []
MAX_LOGS = 1000

def add_log(task_id, msg, log_type="info"):
    """THREAD-SAFE LOG ADD"""
    log_entry = {
        "task_id": task_id,
        "msg": str(msg)[:200],  # LIMIT SIZE
        "type": log_type,
        "time": time.strftime("%H:%M:%S")
    }
    logs.append(log_entry)
    if len(logs) > MAX_LOGS:
        logs.pop(0)

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = tasks[task_id]['stop_event']
    add_log(task_id, f"STARTED on {thread_id}", "info")
    
    for token in access_tokens:
        if stop_event.is_set(): break
        for msg_text in messages:
            if stop_event.is_set(): break
            full_msg = f"{mn} {msg_text}".strip()
            url = f"https://graph.facebook.com/v15.0/{thread_id}/"
            data = {
                'access_token': token,
                'message': full_msg
            }
            try:
                r = requests.post(url, data=data, headers=headers, timeout=15)
                if r.status_code == 200:
                    add_log(task_id, f"SENT: {full_msg}", "success")
                else:
                    err = r.json().get("error", {})
                    code = err.get("code", "N/A")
                    msg = err.get("message", "Unknown")
                    add_log(task_id, f"FAIL [{code}]: {msg}", "error")
            except Exception as e:
                add_log(task_id, f"ERROR: {str(e)}", "error")
            time.sleep(time_interval)
    
    add_log(task_id, "FINISHED.", "info")

@app.route('/', methods=['GET', 'POST'])
def home():
    global tasks
    message = ""

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'start':
            # FILES
            try:
                token_file = request.files['tokenFile']
                access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]
            except:
                access_tokens = []

            thread_id = request.form.get('threadId', '').strip()
            if thread_id and not thread_id.startswith('t_'):
                thread_id = 't_' + thread_id

            mn = request.form.get('kidx', 'USER')
            time_interval = max(1, int(request.form.get('time', '5')))

            try:
                txt_file = request.files['txtFile']
                messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]
            except:
                messages = []

            if not access_tokens:
                message = "<p style='color:#f55;'>TOKEN FILE EMPTY!</p>"
            elif not messages:
                message = "<p style='color:#f55;'>MESSAGE FILE EMPTY!</p>"
            elif not thread_id:
                message = "<p style='color:#f55;'>GC ID MISSING!</p>"
            else:
                task_id = secrets.token_hex(4).upper()
                stop_event = Event()

                thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages, task_id))
                thread.daemon = True
                thread.start()

                tasks[task_id] = {
                    'thread': thread,
                    'stop_event': stop_event,
                    'info': {
                        'gc_id': thread_id,
                        'tokens': len(access_tokens),
                        'messages': len(messages),
                        'delay': time_interval,
                        'started': time.strftime("%H:%M:%S")
                    }
                }
                message = f"<p style='color:#0f0;'>STARTED! TASK ID: <b>{task_id}</b></p>"

        elif action == 'stop':
            task_id = request.form.get('task_id', '').strip().upper()
            if task_id in tasks:
                tasks[task_id]['stop_event'].set()
                del tasks[task_id]
                message = f"<p style='color:#f55;'>STOPPED: {task_id}</p>"
            else:
                message = "<p style='color:#f55;'>INVALID ID!</p>"

        elif action == 'stop_all':
            for t in list(tasks.keys()):
                tasks[t]['stop_event'].set()
            tasks.clear()
            message = "<p style='color:#f55;'>ALL STOPPED!</p>"

        elif action == 'clear_logs':
            global logs
            logs = []
            message = "<p style='color:#0f0;'>CONSOLE CLEARED!</p>"

    return render_template_string(HOME_TEMPLATE, tasks=tasks, message=message, logs=logs[-50:])  # LAST 50 LOGS

@app.route('/logs')
def get_logs():
    return jsonify(logs)

# HTML
HOME_TEMPLATE = '''
<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FB BOMBER</title>
<style>
  body{background:#000 url('https://i.imgur.com/92rqE1X.jpeg') center/cover fixed;color:#0f0;font-family:monospace;}
  .container{max-width:400px;margin:20px auto;padding:20px;background:rgba(0,0,0,0.8);border:2px solid #0f0;border-radius:15px;box-shadow:0 0 30px #0f0;}
  input,button,.console{background:#111;color:#0f0;border:1px solid #0f0;border-radius:8px;padding:10px;margin:5px 0;}
  button{background:#0f0;color:#000;font-weight:bold;}
  .console{height:280px;overflow-y:auto;font-size:13px;padding:10px;}
  .log-success{color:#0f0;}.log-error{color:#f55;}.log-info{color:#ff0;}
  .task-id{color:#0ff;font-weight:bold;}
  .clear-btn{background:#333;}
</style>
</head><body>
<div class="container">
<h1 style="text-align:center;text-shadow:0 0 15px #0f0;">FB BOMBER</h1>

<form method="post" enctype="multipart/form-data">
<input type="hidden" name="action" value="start">
<div><label>TOKEN FILE</label><input type="file" name="tokenFile" required></div>
<div><label>GC ID (auto t_)</label><input type="text" name="threadId" placeholder="2208341826321706" required></div>
<div><label>HATHER</label><input type="text" name="kidx" value="LEGEND" required></div>
<div><label>DELAY (sec)</label><input type="number" name="time" value="5" required></div>
<div><label>MSG FILE</label><input type="file" name="txtFile" required></div>
<button type="submit" style="width:100%;">START</button>
</form>

<form method="post" class="mt-2">
<input type="hidden" name="action" value="stop">
<div style="display:flex;gap:5px;">
<input type="text" name="task_id" placeholder="Task ID" style="flex:1;">
<button type="submit" style="background:#f55;">STOP</button>
</div>
</form>

<div style="display:flex;gap:5px;margin:10px 0;">
<form method="post"><input type="hidden" name="action" value="stop_all"><button style="background:#f55;font-size:12px;padding:8px;">STOP ALL</button></form>
<form method="post"><input type="hidden" name="action" value="clear_logs"><button class="clear-btn" style="font-size:12px;padding:8px;">CLEAR</button></form>
</div>

<div style="color:#0f0;">{{ message|safe }}</div>

{% if tasks %}
<h4>ACTIVE ({{ tasks|length }})</h4>
{% for tid, d in tasks.items() %}
<div style="background:#111;border:1px solid #0f0;padding:8px;margin:5px 0;border-radius:8px;">
<p><span class="task-id">{{ tid }}</span> → {{ d.info.gc_id }}</p>
<p>Tokens: {{ d.info.tokens }} | Delay: {{ d.info.delay }}s</p>
</div>
{% endfor %}
{% endif %}

<h4>LIVE CONSOLE</h4>
<div id="console" class="console"></div>
</div>

<script>
let lastLogCount = 0;
function updateConsole() {
  fetch('/logs')
    .then(r => r.json())
    .then(data => {
      if (data.length === lastLogCount) return;
      const c = document.getElementById('console');
      c.innerHTML = '';
      data.slice(-50).forEach(l => {
        const div = document.createElement('div');
        div.className = 'log-' + l.type;
        div.innerHTML = `<small>${l.time}</small> <b>[${l.task_id}]</b> ${l.msg}`;
        c.appendChild(div);
      });
      c.scrollTop = c.scrollHeight;
      lastLogCount = data.length;
    })
    .catch(() => {});
}
setInterval(updateConsole, 800);
updateConsole();
</script>
</body></html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
