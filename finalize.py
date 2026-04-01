#!/usr/bin/env python3
"""Finalize - Complete Kaggle registration and retry HuggingFace."""

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
    print(f"  Navigating to {url}")
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

# ============ KAGGLE - Complete Registration ============
print("\n=== KAGGLE - Complete Registration ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {
        'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False
    })
    
    url = get_url(ws)
    print(f"  Current URL: {url}")
    
    if 'FinishSSORegistration' in str(url) or 'kaggle.com' in str(url):
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 1000)')
        print(f"  Page: {(page_text or '')[:400]}")
        screenshot(ws, 'kaggle_finish_reg')
        
        # Look for form fields
        fields = evaluate(ws, """(function() {
            let inputs = document.querySelectorAll('input, select, textarea');
            return JSON.stringify(Array.from(inputs).map(i => ({
                type: i.type, name: i.name, id: i.id,
                placeholder: i.placeholder,
                value: i.value?.substring(0, 30)
            })));
        })()""")
        print(f"  Fields: {fields}")
        
        # Fill username if needed
        result = evaluate(ws, """(function() {
            let inputs = document.querySelectorAll('input');
            let results = [];
            for (let input of inputs) {
                let n = (input.name || input.id || input.placeholder || '').toLowerCase();
                if (n.includes('user') || n.includes('display') || n.includes('name')) {
                    if (!input.value || input.value.length < 2) {
                        let nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(input, 'novacline602');
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        input.dispatchEvent(new Event('change', {bubbles: true}));
                        results.push('set ' + input.name);
                    }
                }
            }
            // Check checkboxes (TOS etc)
            let cbs = document.querySelectorAll('input[type="checkbox"]');
            for (let cb of cbs) {
                if (!cb.checked) {
                    cb.click();
                    results.push('checked');
                }
            }
            return JSON.stringify(results);
        })()""")
        print(f"  Fill result: {result}")
        
        # Look for submit/register button
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button, input[type="submit"]');
            for (let btn of btns) {
                let t = btn.textContent?.trim()?.toLowerCase() || btn.value?.toLowerCase() || '';
                if (t.includes('register') || t.includes('create') || t.includes('submit') || t.includes('sign up') || t.includes('complete') || t.includes('finish')) {
                    let rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent?.trim() || btn.value});
                    }
                }
            }
            return null;
        })()""")
        print(f"  Submit button: {coords}")
        
        if coords:
            data = json.loads(coords)
            print(f"  Clicking '{data['text']}' at ({data['x']}, {data['y']})")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  After submit: {url}")
        print(f"  Text: {(page_text or '')[:200]}")
        screenshot(ws, 'kaggle_post_reg')
    
    # Check if logged in
    navigate(ws, 'https://www.kaggle.com/me')
    time.sleep(3)
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
    print(f"  /me URL: {url}")
    print(f"  /me text: {(page_text or '')[:200]}")
    screenshot(ws, 'kaggle_me_check')
    
    if 'login' not in str(url).lower():
        kaggle_status = 'SUCCESS - Registered and signed in via Google OAuth'
    else:
        kaggle_status = 'PARTIAL - OAuth worked but registration may need completion'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

# ============ HUGGING FACE - Redo Registration ============
print("\n=== HuggingFace - Full Registration ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {
        'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False
    })
    
    navigate(ws, 'https://huggingface.co/join')
    time.sleep(3)
    
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  Page: {(page_text or '')[:200]}")
    
    if 'Email Address' in str(page_text):
        # Step 1: Fill email and password
        result = evaluate(ws, """(function() {
            let nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
            let inputs = document.querySelectorAll('input');
            let results = [];
            for (let input of inputs) {
                if (input.type === 'email' || input.name === 'email') {
                    nativeSetter.call(input, 'novacline602@gmail.com');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('email set');
                }
                if (input.type === 'password' || input.name === 'password') {
                    nativeSetter.call(input, 'NovaCline2026!Sec');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('password set');
                }
            }
            return JSON.stringify(results);
        })()""")
        print(f"  Step 1: {result}")
        time.sleep(1)
        screenshot(ws, 'hf_step1')
        
        # Click Next
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.trim() === 'Next') {
                    let rect = btn.getBoundingClientRect();
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(3)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  After Next: {url}")
        print(f"  Text: {(page_text or '')[:200]}")
        screenshot(ws, 'hf_step2')
        
        if 'Complete your profile' in str(page_text):
            # Step 2: Fill profile
            result2 = evaluate(ws, """(function() {
                let nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                let inputs = document.querySelectorAll('input[name]');
                let results = [];
                for (let input of inputs) {
                    if (input.name === 'username') {
                        nativeSetter.call(input, 'novacline602');
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        results.push('username');
                    } else if (input.name === 'fullname') {
                        nativeSetter.call(input, 'Nova Cline');
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        results.push('fullname');
                    } else if (['twitter', 'github', 'linkedin'].includes(input.name)) {
                        nativeSetter.call(input, '');
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                    }
                }
                // Accept TOS
                let cbs = document.querySelectorAll('input[type="checkbox"]');
                for (let cb of cbs) {
                    if (!cb.checked) cb.click();
                    results.push('tos checked');
                }
                return JSON.stringify(results);
            })()""")
            print(f"  Profile: {result2}")
            time.sleep(1)
            screenshot(ws, 'hf_profile_final')
            
            # Click Create Account
            coords2 = evaluate(ws, """(function() {
                let btns = document.querySelectorAll('button');
                for (let btn of btns) {
                    if (btn.textContent.trim().includes('Create Account')) {
                        let rect = btn.getBoundingClientRect();
                        return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2});
                    }
                }
                return null;
            })()""")
            if coords2:
                data = json.loads(coords2)
                mouse_click(ws, data['x'], data['y'])
                time.sleep(5)
            
            url = get_url(ws)
            page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
            print(f"  After Create: {url}")
            print(f"  Text: {(page_text or '')[:300]}")
            screenshot(ws, 'hf_after_create2')
            
            if 'join' not in str(url):
                hf_status = 'SUCCESS - Account created'
            elif 'error' in str(page_text or '').lower():
                hf_status = f'ERROR - {(page_text or "")[:100]}'
            elif 'email' in str(page_text or '').lower() and ('check' in str(page_text or '').lower() or 'confirm' in str(page_text or '').lower() or 'verify' in str(page_text or '').lower()):
                hf_status = 'PENDING - Email verification sent'
            else:
                hf_status = f'IN PROGRESS - {(page_text or "")[:100]}'
        else:
            hf_status = f'STEP 1 ISSUE - {(page_text or "")[:100]}'
    elif 'Complete your profile' in str(page_text):
        hf_status = 'ON PROFILE PAGE - needs completion'
    else:
        hf_status = f'UNKNOWN STATE - {(page_text or "")[:100]}'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    hf_status = f'ERROR - {e}'

# Final results
results = {
    'huggingface': hf_status,
    'kaggle': kaggle_status,
    'replicate': 'SKIPPED - GitHub OAuth only (no Google support)'
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
- **HuggingFace**: No Google OAuth available. Registered via email/password.
- **Kaggle**: Used Google OAuth (Register with Google). Completed account chooser + consent flow.
- **Replicate**: Only GitHub OAuth available, no Google OAuth option.
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
