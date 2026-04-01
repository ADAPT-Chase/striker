#!/usr/bin/env python3
"""Kaggle final - complete OAuth flow and registration in one session."""

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
    print(f"  Nav: {url}")
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
send_cmd(ws, 'Network.enable')
send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})

# Go to Kaggle Sign In (not register)
navigate(ws, 'https://www.kaggle.com/account/login?phase=startSignInTab')
time.sleep(5)

# Dismiss cookies
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
    print(f"  Clicking Sign in with Google")
    mouse_click(ws, data['x'], data['y'])
    time.sleep(8)

url = get_url(ws)
print(f"  After Google: {url[:120]}")

# Check if we need to handle Google consent still
if 'accounts.google.com' in str(url):
    # Account chooser
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
    
    # Consent
    if 'accounts.google.com' in str(url):
        time.sleep(2)
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.trim() === 'Continue') {
                    let r = btn.getBoundingClientRect();
                    return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            print(f"  Clicking Continue")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(8)

url = get_url(ws)
print(f"  Now at: {url[:120]}")
screenshot(ws, 'kaggle_flow1')
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 800)')
print(f"  Text: {(page_text or '')[:400]}")

# If on FinishSSORegistration - complete it
if 'FinishSSORegistration' in str(url):
    print("\n  === Completing Kaggle Registration ===")
    
    # Get form details
    fields = evaluate(ws, """(function() {
        let inputs = document.querySelectorAll('input, select, textarea');
        return JSON.stringify(Array.from(inputs).map(i => ({type: i.type, name: i.name, value: i.value?.substring(0,30)})));
    })()""")
    print(f"  Fields: {fields}")
    
    # Check checkboxes (terms)
    evaluate(ws, """(function() {
        document.querySelectorAll('input[type="checkbox"]').forEach(c => { if (!c.checked) c.click(); });
    })()""")
    
    # Find and click Register/Submit button
    all_btns = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button, input[type="submit"]');
        return JSON.stringify(Array.from(btns).map(b => ({
            text: (b.textContent || b.value || '').trim().substring(0, 50),
            type: b.type,
            disabled: b.disabled,
            rect: (() => { let r = b.getBoundingClientRect(); return {x: r.x+r.width/2, y: r.y+r.height/2, w: r.width}; })()
        })));
    })()""")
    print(f"  All buttons: {all_btns}")
    
    # Click the register button
    coords = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button, input[type="submit"]');
        for (let btn of btns) {
            let t = (btn.textContent || btn.value || '').trim().toLowerCase();
            if ((t.includes('register') || t.includes('complete') || t.includes('submit') || t.includes('create') || t.includes('sign up')) && !btn.disabled) {
                let r = btn.getBoundingClientRect();
                if (r.width > 0) return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2, text: t});
            }
        }
        // Try any visible non-disabled submit button
        for (let btn of btns) {
            if (btn.type === 'submit' && !btn.disabled) {
                let r = btn.getBoundingClientRect();
                if (r.width > 0) return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2, text: btn.textContent.trim()});
            }
        }
        return null;
    })()""")
    print(f"  Submit: {coords}")
    
    if coords:
        data = json.loads(coords)
        print(f"  Clicking '{data['text']}'")
        mouse_click(ws, data['x'], data['y'])
        time.sleep(8)
    else:
        # Try form submit
        evaluate(ws, "document.querySelector('form')?.submit()")
        time.sleep(5)
    
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  After registration: {url[:100]}")
    print(f"  Text: {(page_text or '')[:200]}")
    screenshot(ws, 'kaggle_post_reg2')

# Final check - try kaggle.com
time.sleep(2)
navigate(ws, 'https://www.kaggle.com')
time.sleep(3)
url = get_url(ws)
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
print(f"\n  Final URL: {url}")
print(f"  Text: {(page_text or '')[:200]}")
screenshot(ws, 'kaggle_home')

# Check if logged in by looking for user menu/avatar
logged_in = evaluate(ws, """(function() {
    // Check for user avatar, profile link, or sign-out
    let indicators = document.querySelectorAll('[aria-label*="profile"], [alt*="avatar"], a[href*="/settings"], .user-avatar, [data-testid*="user"]');
    if (indicators.length > 0) return 'logged in';
    // Check if Sign In button exists
    let btns = document.querySelectorAll('button, a');
    for (let b of btns) {
        if (b.textContent.trim() === 'Sign In' || b.textContent.trim() === 'Register') {
            return 'not logged in - Sign In button visible';
        }
    }
    return 'unclear';
})()""")
print(f"  Login check: {logged_in}")

# Also get cookies to check
cookies = evaluate(ws, 'document.cookie')
print(f"  Cookies: {(cookies or '')[:200]}")

ws.close()

# Determine status
if 'not logged in' in str(logged_in):
    kaggle_status = 'PARTIAL - OAuth consent completed, account created (novacline), but session not persisting'
else:
    kaggle_status = 'SUCCESS'

print(f"\nKaggle status: {kaggle_status}")
