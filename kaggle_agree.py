#!/usr/bin/env python3
"""Accept Kaggle terms and complete registration."""

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

def mouse_click(ws, x, y):
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': int(x), 'y': int(y)})
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': int(x), 'y': int(y), 'button': 'left', 'clickCount': 1})
    time.sleep(0.05)
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': int(x), 'y': int(y), 'button': 'left', 'clickCount': 1})

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

ws_url = [p for p in get_pages() if p['type'] == 'page' and 'webSocketDebuggerUrl' in p][0]['webSocketDebuggerUrl']
ws = websocket.create_connection(ws_url, timeout=10)
send_cmd(ws, 'Page.enable')
send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})

# Start fresh - sign in
navigate(ws, 'https://www.kaggle.com/account/login?phase=startSignInTab')
time.sleep(5)

evaluate(ws, """(function() { document.querySelectorAll('button, a').forEach(b => { if (b.textContent.includes('OK, Got it')) b.click(); }); })()""")
time.sleep(1)

# Click Sign in with Google  
coords = evaluate(ws, """(function() {
    let btns = document.querySelectorAll('button');
    for (let btn of btns) {
        if (btn.textContent.includes('Sign in with Google')) {
            let r = btn.getBoundingClientRect();
            return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
        }
    }
    return null;
})()""")
if coords:
    data = json.loads(coords)
    mouse_click(ws, data['x'], data['y'])
    time.sleep(8)

url = get_url(ws)
print(f"After Google click: {url[:120]}")

# Handle Google if needed
if 'accounts.google.com' in str(url):
    if 'accountchooser' in str(url):
        coords = evaluate(ws, """(function() {
            let el = document.querySelector('[data-identifier="novacline602@gmail.com"]');
            if (el) { let r = el.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
    
    url = get_url(ws)
    if 'accounts.google.com' in str(url):
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) { if (btn.textContent.trim() === 'Continue') { let r = btn.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); } }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(8)

url = get_url(ws)
print(f"Now at: {url[:120]}")
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
print(f"Text: {(page_text or '')[:300]}")
screenshot(ws, 'kaggle_step')

# Handle multi-step registration
for step in range(5):
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    
    if 'kaggle.com' in str(url) and 'login' not in str(url) and 'FinishSSO' not in str(url):
        print(f"  Done! Redirected to: {url}")
        break
    
    print(f"\n  Step {step}: {(page_text or '')[:150]}")
    
    # Click any visible action button (Next, I Agree, Register, etc.)
    coords = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button[type="submit"], button');
        let priorities = ['i agree', 'agree', 'next', 'register', 'complete', 'submit', 'finish', 'accept'];
        for (let p of priorities) {
            for (let btn of btns) {
                let t = (btn.textContent || '').trim().toLowerCase();
                if (t === p || t.includes(p)) {
                    let r = btn.getBoundingClientRect();
                    if (r.width > 0 && !btn.disabled) {
                        return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2, text: btn.textContent.trim()});
                    }
                }
            }
        }
        return null;
    })()""")
    
    if coords:
        data = json.loads(coords)
        print(f"  Clicking '{data['text']}'")
        
        # Need to scroll to see button? Check if it's in viewport
        if data['y'] > 900:
            evaluate(ws, f"window.scrollTo(0, {data['y'] - 400})")
            time.sleep(0.5)
            # Recalculate coords after scroll
            coords2 = evaluate(ws, f"""(function() {{
                let btns = document.querySelectorAll('button');
                for (let btn of btns) {{
                    if (btn.textContent.trim() === '{data["text"]}') {{
                        let r = btn.getBoundingClientRect();
                        return JSON.stringify({{x: r.x+r.width/2, y: r.y+r.height/2}});
                    }}
                }}
                return null;
            }})()""")
            if coords2:
                data = json.loads(coords2)
        
        mouse_click(ws, data['x'], data['y'])
        time.sleep(5)
    else:
        # Check for checkboxes first
        evaluate(ws, """(function() {
            document.querySelectorAll('input[type="checkbox"]').forEach(c => { if (!c.checked) c.click(); });
        })()""")
        time.sleep(1)
        # Try form submit
        evaluate(ws, "document.querySelector('form')?.submit()")
        time.sleep(3)
    
    screenshot(ws, f'kaggle_step{step}')

# Final verification
url = get_url(ws)
print(f"\nFinal URL: {url}")

# Check login
navigate(ws, 'https://www.kaggle.com/')
time.sleep(3)
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 200)')
print(f"Home text: {(page_text or '')[:200]}")
screenshot(ws, 'kaggle_final_home')

# Check for user-specific elements
user_check = evaluate(ws, """(function() {
    let html = document.body?.innerHTML || '';
    if (html.includes('novacline') || html.includes('nova cline')) return 'found username in page';
    let signIn = Array.from(document.querySelectorAll('a, button')).filter(e => e.textContent.trim() === 'Sign In');
    if (signIn.length > 0) return 'Sign In button present - not logged in';
    return 'no clear indicator';
})()""")
print(f"User check: {user_check}")

ws.close()
