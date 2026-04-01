#!/usr/bin/env python3
"""Verify Kaggle login and check HF captcha situation."""

import json, subprocess, time, websocket, base64

cmd_id = 0
def send_cmd(ws, method, params=None):
    global cmd_id
    cmd_id += 1
    msg = {'id': cmd_id, 'method': method}
    if params:
        msg['params'] = params
    ws.send(json.dumps(msg))
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            ws.settimeout(5)
            resp = json.loads(ws.recv())
            if resp.get('id') == cmd_id:
                return resp
        except websocket.WebSocketTimeoutException:
            continue
    return None

def evaluate(ws, expr):
    resp = send_cmd(ws, 'Runtime.evaluate', {'expression': expr, 'awaitPromise': True, 'timeout': 15000})
    if resp and 'result' in resp:
        return resp['result'].get('result', {}).get('value')
    return None

def get_url(ws):
    return evaluate(ws, 'window.location.href')

def screenshot(ws, name):
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    if resp and 'result' in resp:
        data = base64.b64decode(resp['result']['data'])
        path = f'/home/x/striker/{name}.png'
        with open(path, 'wb') as f:
            f.write(data)
        print(f"  Screenshot: {path}")

def navigate(ws, url):
    send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(4)

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

ws_url = [p for p in get_pages() if p['type'] == 'page' and 'webSocketDebuggerUrl' in p][0]['webSocketDebuggerUrl']
ws = websocket.create_connection(ws_url, timeout=10)
send_cmd(ws, 'Page.enable')
send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})

# Verify Kaggle
print("=== Verifying Kaggle ===")
navigate(ws, 'https://www.kaggle.com/account')
time.sleep(3)
url = get_url(ws)
print(f"Account URL: {url}")
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
print(f"Text: {(page_text or '')[:300]}")
screenshot(ws, 'kaggle_verify')

# Check username
navigate(ws, 'https://www.kaggle.com/me')  
time.sleep(3)
url = get_url(ws)
print(f"/me URL: {url}")
screenshot(ws, 'kaggle_me_verify')

# Also check user settings
navigate(ws, 'https://www.kaggle.com/settings')
time.sleep(3)
url = get_url(ws)
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
print(f"Settings: {url}")
print(f"Text: {(page_text or '')[:200]}")

ws.close()
