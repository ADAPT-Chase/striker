#!/usr/bin/env python3
"""Click the Google account on the chooser page using CDP mouse events."""

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
    """Simulate a real mouse click at coordinates."""
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseMoved', 'x': x, 'y': y
    })
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mousePressed', 'x': x, 'y': y,
        'button': 'left', 'clickCount': 1
    })
    time.sleep(0.05)
    send_cmd(ws, 'Input.dispatchMouseEvent', {
        'type': 'mouseReleased', 'x': x, 'y': y,
        'button': 'left', 'clickCount': 1
    })

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

def handle_google_flow(ws, max_wait=30):
    """Handle the full Google OAuth flow - account chooser + consent."""
    start = time.time()
    while time.time() - start < max_wait:
        url = get_url(ws)
        if not url or 'accounts.google.com' not in url:
            print(f"  Left Google, now at: {url}")
            return True
        
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  Google page text: {(page_text or '')[:200]}")
        
        # Find the account element coordinates
        coords = evaluate(ws, """(function() {
            // Account chooser - find the account row
            let el = document.querySelector('[data-identifier="novacline602@gmail.com"]');
            if (el) {
                let rect = el.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, type: 'account'});
            }
            // Consent page - find Continue button
            // Google consent pages use specific button patterns
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                let text = btn.textContent.trim().toLowerCase();
                if (text === 'continue' || text === 'allow' || text === 'confirm') {
                    let rect = btn.getBoundingClientRect();
                    if (rect.width > 0) {
                        return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, type: 'button', text: text});
                    }
                }
            }
            // Look for submit-like elements
            let submits = document.querySelectorAll('[type="submit"], [jsname="LgbsSe"]');
            for (let s of submits) {
                let rect = s.getBoundingClientRect();
                if (rect.width > 0) {
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, type: 'submit'});
                }
            }
            return null;
        })()""")
        
        if coords:
            data = json.loads(coords)
            print(f"  Clicking {data['type']} at ({data['x']}, {data['y']})")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(4)
        else:
            # Maybe it's the consent page with "Sign in to Kaggle" - need to scroll or find button
            # Try finding any clickable action area
            coords2 = evaluate(ws, """(function() {
                // The consent page might have the Continue button hidden or use a different structure
                // Look for the main action area
                let el = document.querySelector('[data-is-consent] button, .JYXaTc button, [jsname="LgbsSe"], [jsname="Njthtb"]');
                if (el) {
                    let rect = el.getBoundingClientRect();
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, type: 'consent-btn'});
                }
                // The page says "Sign in to Kaggle" with info - look for any action div at the bottom
                let actionDiv = document.querySelector('.JYXaTc');
                if (actionDiv) {
                    // The action div might be empty when data-is-consent is false
                    // This means it's still loading or we need to wait
                    return JSON.stringify({empty: true, consent: actionDiv.getAttribute('data-is-consent')});
                }
                return null;
            })()""")
            print(f"  Alt search: {coords2}")
            
            if coords2:
                try:
                    data2 = json.loads(coords2)
                    if 'x' in data2:
                        mouse_click(ws, data2['x'], data2['y'])
                        time.sleep(3)
                except:
                    pass
            
            time.sleep(2)
    
    return False

# ============ KAGGLE ============
print("\n=== KAGGLE - Full OAuth Flow ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    # Start fresh
    navigate(ws, 'https://www.kaggle.com/account/login?phase=startRegisterTab')
    time.sleep(5)
    
    # Dismiss cookies
    evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button, a');
        for (let b of btns) {
            if (b.textContent.includes('OK, Got it')) { b.click(); return 'done'; }
        }
        return 'no cookie banner';
    })()""")
    time.sleep(1)
    
    # Find and click "Register with Google" using coordinates
    coords = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button');
        for (let btn of btns) {
            if (btn.textContent.includes('Register with Google')) {
                let rect = btn.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2});
            }
        }
        return null;
    })()""")
    
    if coords:
        data = json.loads(coords)
        print(f"  Clicking Register with Google at ({data['x']}, {data['y']})")
        mouse_click(ws, data['x'], data['y'])
        time.sleep(5)
    
    url = get_url(ws)
    print(f"  After click: {url}")
    
    if 'accounts.google.com' in str(url):
        success = handle_google_flow(ws, max_wait=45)
        time.sleep(3)
        url = get_url(ws)
        print(f"  After Google flow: {url}")
        screenshot(ws, 'kaggle_after_flow')
    
    # Check if we need to complete registration
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 1000)')
    print(f"  Current page: {url}")
    print(f"  Text: {(page_text or '')[:300]}")
    
    # Navigate to check login
    navigate(ws, 'https://www.kaggle.com/me')
    time.sleep(3)
    url = get_url(ws)
    screenshot(ws, 'kaggle_me_final')
    print(f"  /me URL: {url}")
    
    if 'login' in str(url).lower():
        kaggle_status = 'FAILED'
    else:
        kaggle_status = 'SUCCESS'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

# ============ HUGGING FACE ============
print("\n=== HUGGING FACE - Email Registration ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    # HF doesn't have Google OAuth, so we need to register with email
    navigate(ws, 'https://huggingface.co/join')
    time.sleep(3)
    screenshot(ws, 'hf_join2')
    
    # Fill in registration form
    # Check what fields exist
    fields = evaluate(ws, """(function() {
        let inputs = document.querySelectorAll('input');
        return JSON.stringify(Array.from(inputs).map(i => ({
            type: i.type, name: i.name, id: i.id, placeholder: i.placeholder
        })));
    })()""")
    print(f"  Form fields: {fields}")
    
    # Fill email, username, password
    evaluate(ws, """(function() {
        let inputs = document.querySelectorAll('input');
        for (let input of inputs) {
            let n = (input.name || input.id || input.placeholder || '').toLowerCase();
            if (n.includes('email') || input.type === 'email') {
                input.value = 'novacline602@gmail.com';
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (n.includes('password') || input.type === 'password') {
                input.value = 'NovaCline2026!Secure';
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
            if (n.includes('user') || n.includes('name')) {
                input.value = 'novacline602';
                input.dispatchEvent(new Event('input', {bubbles: true}));
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
        }
        return 'filled';
    })()""")
    time.sleep(1)
    screenshot(ws, 'hf_filled')
    
    # Click Next/Submit
    result = evaluate(ws, """(function() {
        let btn = document.querySelector('button[type="submit"], button.btn-primary');
        if (!btn) {
            let btns = document.querySelectorAll('button');
            for (let b of btns) {
                if (b.textContent.includes('Next') || b.textContent.includes('Sign') || b.textContent.includes('Create')) {
                    btn = b;
                    break;
                }
            }
        }
        if (btn) {
            btn.click();
            return 'clicked: ' + btn.textContent.trim();
        }
        return 'no button found';
    })()""")
    print(f"  Submit: {result}")
    time.sleep(3)
    
    url = get_url(ws)
    screenshot(ws, 'hf_after_submit')
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  After submit URL: {url}")
    print(f"  After submit text: {(page_text or '')[:300]}")
    
    # HF registration is multi-step, may need to verify email
    hf_status = f'REGISTRATION ATTEMPTED - check email for verification (URL: {url})'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    hf_status = f'ERROR - {e}'

# Update results
results = {
    'huggingface': hf_status,
    'kaggle': kaggle_status,
    'replicate': 'SKIPPED - GitHub OAuth only (no Google OAuth)'
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

## Notes
- **Replicate** only supports GitHub OAuth, not Google OAuth
- **HuggingFace** does not offer Google OAuth - uses email/password registration only
- **Kaggle** supports Google OAuth (Register with Google button)
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
