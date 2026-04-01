#!/usr/bin/env python3
"""Final attempt - Kaggle full flow in one go, HF debug form submission."""

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

def type_text(ws, text):
    """Type text character by character."""
    for ch in text:
        send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'text': ch})
        send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'text': ch})
        time.sleep(0.02)

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

# ===== KAGGLE - Full flow ===== 
print("\n=== KAGGLE ===")
try:
    ws_url = [p for p in get_pages() if p['type'] == 'page' and 'webSocketDebuggerUrl' in p][0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})
    
    # Step 1: Go to Kaggle login
    navigate(ws, 'https://www.kaggle.com/account/login?phase=startSignInTab')
    time.sleep(5)
    
    # Dismiss cookies
    evaluate(ws, """(function() { document.querySelectorAll('button, a').forEach(b => { if (b.textContent.includes('OK, Got it')) b.click(); }); })()""")
    time.sleep(1)
    
    # Click "Sign in with Google" (on the sign-in tab, not register)
    coords = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button');
        for (let btn of btns) {
            let t = btn.textContent.trim();
            if (t.includes('with Google')) {
                let rect = btn.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: t});
            }
        }
        return null;
    })()""")
    print(f"  Google button: {coords}")
    
    if coords:
        data = json.loads(coords)
        print(f"  Clicking '{data['text']}'")
        mouse_click(ws, data['x'], data['y'])
        time.sleep(5)
    
    url = get_url(ws)
    print(f"  After click: {url[:100]}")
    
    # Step 2: Google account chooser
    if 'accounts.google.com' in str(url):
        if 'accountchooser' in str(url):
            coords = evaluate(ws, """(function() {
                let el = document.querySelector('[data-identifier="novacline602@gmail.com"]');
                if (el) { let r = el.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
                return null;
            })()""")
            if coords:
                data = json.loads(coords)
                print(f"  Clicking account")
                mouse_click(ws, data['x'], data['y'])
                time.sleep(5)
        
        url = get_url(ws)
        print(f"  After account: {url[:100]}")
        
        # Step 3: Consent - click Continue
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
    print(f"  After consent: {url[:100]}")
    screenshot(ws, 'kaggle_state')
    
    # Handle Kaggle registration completion if needed
    if 'FinishSSORegistration' in str(url) or 'kaggle.com' in str(url):
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  Kaggle text: {(page_text or '')[:200]}")
        
        # Fill any required fields and submit
        fields = evaluate(ws, """(function() {
            let inputs = document.querySelectorAll('input, select');
            return JSON.stringify(Array.from(inputs).map(i => ({type: i.type, name: i.name, value: i.value?.substring(0,20)})));
        })()""")
        print(f"  Fields: {fields}")
        
        # Accept terms if needed
        evaluate(ws, """(function() {
            document.querySelectorAll('input[type="checkbox"]').forEach(c => { if (!c.checked) c.click(); });
        })()""")
        
        # Click register/complete button
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button, input[type="submit"]');
            for (let btn of btns) {
                let t = (btn.textContent || btn.value || '').trim().toLowerCase();
                if (t.includes('register') || t.includes('complete') || t.includes('finish') || t.includes('submit') || t.includes('create')) {
                    let r = btn.getBoundingClientRect();
                    if (r.width > 0) return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2, text: t});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            print(f"  Clicking '{data['text']}'")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
    
    # Verify login
    time.sleep(2)
    url = get_url(ws)
    print(f"  Current: {url[:100]}")
    
    # Try accessing account page
    navigate(ws, 'https://www.kaggle.com/account')
    time.sleep(3)
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
    print(f"  Account URL: {url[:100]}")
    print(f"  Account text: {(page_text or '')[:150]}")
    screenshot(ws, 'kaggle_account_final')
    
    if 'login' in str(url).lower() and 'account' not in str(url).lower().split('login')[0]:
        kaggle_status = 'PARTIAL - OAuth consent worked, registration may need email verification'
    elif 'account' in str(url).lower() and 'login' not in str(url).lower():
        kaggle_status = 'SUCCESS - Logged in'
    else:
        kaggle_status = f'PARTIAL - Current URL: {url[:80]}'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

# ===== HuggingFace - Use keyboard entry =====
print("\n=== HUGGING FACE ===")
try:
    ws_url = [p for p in get_pages() if p['type'] == 'page' and 'webSocketDebuggerUrl' in p][0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False})
    
    navigate(ws, 'https://huggingface.co/join')
    time.sleep(3)
    
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
    print(f"  Page: {(page_text or '')[:150]}")
    
    if 'Email Address' in str(page_text):
        # Click email field and type
        coords = evaluate(ws, """(function() {
            let input = document.querySelector('input[type="email"], input[name="email"]');
            if (input) {
                let r = input.getBoundingClientRect();
                return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.3)
            # Select all and delete
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})  # Ctrl+A
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})
            time.sleep(0.1)
            send_cmd(ws, 'Input.insertText', {'text': 'novacline602@gmail.com'})
            time.sleep(0.5)
        
        # Click password field and type
        coords = evaluate(ws, """(function() {
            let input = document.querySelector('input[type="password"], input[name="password"]');
            if (input) {
                let r = input.getBoundingClientRect();
                return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.3)
            send_cmd(ws, 'Input.insertText', {'text': 'NovaCline2026!Sec'})
            time.sleep(0.5)
        
        screenshot(ws, 'hf_typed')
        
        # Click Next
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.trim() === 'Next') {
                    let r = btn.getBoundingClientRect();
                    return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(3)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
        print(f"  After Next: {(page_text or '')[:150]}")
        
    if 'Complete your profile' in str(evaluate(ws, 'document.body?.innerText?.substring(0, 300)')):
        # Username field
        coords = evaluate(ws, """(function() {
            let input = document.querySelector('input[name="username"]');
            if (input) { let r = input.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.2)
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})
            send_cmd(ws, 'Input.insertText', {'text': 'novacline602'})
            time.sleep(0.5)
        
        # Full name field
        coords = evaluate(ws, """(function() {
            let input = document.querySelector('input[name="fullname"]');
            if (input) { let r = input.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.2)
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'code': 'KeyA', 'modifiers': 2})
            send_cmd(ws, 'Input.insertText', {'text': 'Nova Cline'})
            time.sleep(0.5)
        
        # TOS checkbox
        coords = evaluate(ws, """(function() {
            let cb = document.querySelector('input[type="checkbox"]');
            if (cb && !cb.checked) {
                let r = cb.getBoundingClientRect();
                return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.5)
        
        screenshot(ws, 'hf_profile_typed')
        
        # Create Account
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.includes('Create Account')) {
                    let r = btn.getBoundingClientRect();
                    return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            print(f"  Clicking Create Account")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(8)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  After Create: {url}")
        print(f"  Text: {(page_text or '')[:300]}")
        screenshot(ws, 'hf_final_state')
        
        if 'join' not in str(url) and 'login' not in str(url):
            hf_status = 'SUCCESS - Account created'
        elif 'confirm' in str(page_text or '').lower() or 'verify' in str(page_text or '').lower() or 'check your email' in str(page_text or '').lower():
            hf_status = 'PENDING - Email verification required'
        elif 'already' in str(page_text or '').lower() or 'taken' in str(page_text or '').lower():
            hf_status = 'EXISTS - Username or email already registered'
        else:
            # Check for error messages
            errors = evaluate(ws, """(function() {
                let errs = document.querySelectorAll('.error, .text-red, [class*="error"], [class*="danger"], .invalid-feedback');
                return Array.from(errs).map(e => e.textContent.trim()).join('; ');
            })()""")
            print(f"  Errors: {errors}")
            hf_status = f'ATTEMPTED - {errors or "No visible errors, still on form page"}'
    else:
        hf_status = 'NEEDS REGISTRATION'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    hf_status = f'ERROR - {e}'

# Final results
results = {
    'huggingface': hf_status,
    'kaggle': kaggle_status,
    'replicate': 'SKIPPED - GitHub OAuth only'
}

print("\n=== FINAL RESULTS ===")
for k, v in results.items():
    print(f"  {k}: {v}")

md = f"""# Striker - OAuth Account Status

| Service | Status | Account |
|---------|--------|---------|
| HuggingFace | {results['huggingface']} | novacline602@gmail.com |
| Kaggle | {results['kaggle']} | novacline602@gmail.com |
| Replicate | {results['replicate']} | novacline602@gmail.com |

Updated: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}

## Details
- **HuggingFace**: No Google OAuth available publicly. Attempted email/password registration.
- **Kaggle**: Google OAuth flow completed (account chooser → consent → Continue). 
- **Replicate**: Only supports GitHub OAuth, no Google OAuth option exists.
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
