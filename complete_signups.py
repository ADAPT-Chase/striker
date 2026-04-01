#!/usr/bin/env python3
"""Complete HF profile and retry Kaggle with scroll."""

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
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseMoved', 'x': x, 'y': y})
    time.sleep(0.1)
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})
    time.sleep(0.05)
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': x, 'y': y, 'button': 'left', 'clickCount': 1})

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

# ============ COMPLETE HF PROFILE ============
print("\n=== HuggingFace - Complete Profile ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    url = get_url(ws)
    print(f"  Current URL: {url}")
    
    if 'join' not in str(url):
        navigate(ws, 'https://huggingface.co/join')
        time.sleep(3)
    
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  Page: {(page_text or '')[:200]}")
    
    if 'Complete your profile' in str(page_text):
        # Fill username, full name
        result = evaluate(ws, """(function() {
            let inputs = document.querySelectorAll('input');
            let results = [];
            for (let input of inputs) {
                let n = (input.name || input.placeholder || '').toLowerCase();
                let label = '';
                // Try to find label
                let parent = input.closest('label') || input.parentElement;
                if (parent) label = parent.textContent.trim().substring(0, 30);
                
                if (n.includes('user') || label.toLowerCase().includes('username')) {
                    input.focus();
                    input.value = 'novacline602';
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    input.dispatchEvent(new Event('change', {bubbles: true}));
                    results.push('set username');
                }
                if (n.includes('full') || n.includes('name') || label.toLowerCase().includes('full name')) {
                    if (!n.includes('user')) {
                        input.focus();
                        input.value = 'Nova Cline';
                        input.dispatchEvent(new Event('input', {bubbles: true}));
                        input.dispatchEvent(new Event('change', {bubbles: true}));
                        results.push('set fullname');
                    }
                }
            }
            return JSON.stringify(results);
        })()""")
        print(f"  Fill result: {result}")
        
        # Get all input fields for debugging
        fields = evaluate(ws, """(function() {
            let inputs = document.querySelectorAll('input, textarea, select');
            return JSON.stringify(Array.from(inputs).map(i => {
                let parent = i.closest('label, .form-group, div');
                return {
                    type: i.type, name: i.name, id: i.id,
                    placeholder: i.placeholder,
                    value: i.value?.substring(0, 30),
                    label: parent?.textContent?.trim()?.substring(0, 40) || ''
                };
            }));
        })()""")
        print(f"  All fields: {fields}")
        
        # Accept terms of service checkbox
        result2 = evaluate(ws, """(function() {
            let checkboxes = document.querySelectorAll('input[type="checkbox"]');
            for (let cb of checkboxes) {
                if (!cb.checked) {
                    cb.click();
                }
            }
            return 'checked ' + checkboxes.length + ' checkboxes';
        })()""")
        print(f"  Checkbox: {result2}")
        time.sleep(1)
        
        screenshot(ws, 'hf_profile_filled')
        
        # Click submit/create account button
        result3 = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                let t = btn.textContent.trim().toLowerCase();
                if (t.includes('create') || t.includes('submit') || t.includes('join') || t.includes('sign up') || t.includes('next')) {
                    btn.click();
                    return 'clicked: ' + btn.textContent.trim();
                }
            }
            // Try submit button
            let submit = document.querySelector('button[type="submit"]');
            if (submit) {
                submit.click();
                return 'clicked submit';
            }
            return 'no button found';
        })()""")
        print(f"  Submit: {result3}")
        time.sleep(5)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  After submit URL: {url}")
        print(f"  After submit text: {(page_text or '')[:300]}")
        screenshot(ws, 'hf_after_profile')
        
        if 'join' not in str(url) and 'login' not in str(url):
            hf_status = f'SUCCESS - Account created, URL: {url}'
        elif 'verify' in str(page_text or '').lower() or 'confirm' in str(page_text or '').lower() or 'email' in str(page_text or '').lower():
            hf_status = 'PENDING - Email verification needed'
        else:
            hf_status = f'IN PROGRESS - {(page_text or "")[:100]}'
    else:
        hf_status = 'NEEDS REGISTRATION'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    hf_status = f'ERROR - {e}'

# ============ KAGGLE - with scroll for consent ============
print("\n=== KAGGLE - Retry with scroll ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    # Set larger viewport
    send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {
        'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False
    })
    time.sleep(1)
    
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
    
    # Click Register with Google
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
        screenshot(ws, 'kaggle_google_chooser')
        
        # Click the account
        coords = evaluate(ws, """(function() {
            let el = document.querySelector('[data-identifier="novacline602@gmail.com"]');
            if (el) {
                let rect = el.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2});
            }
            return null;
        })()""")
        
        if coords:
            data = json.loads(coords)
            print(f"  Clicking account at ({data['x']}, {data['y']})")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
        
        url = get_url(ws)
        print(f"  After account select: {url}")
        screenshot(ws, 'kaggle_consent_page')
        
        # Now we're on consent page - scroll down and click Continue
        if 'accounts.google.com' in str(url):
            # First scroll down
            evaluate(ws, 'window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(1)
            
            # Now look for Continue button
            page_text = evaluate(ws, 'document.body?.innerText')
            print(f"  Consent page full text: {(page_text or '')[:500]}")
            
            # Find ALL buttons and their positions after scroll
            btns = evaluate(ws, """(function() {
                let btns = document.querySelectorAll('button, div[role="button"], [jsname]');
                let items = [];
                for (let b of btns) {
                    let rect = b.getBoundingClientRect();
                    let text = b.textContent.trim();
                    if (rect.width > 0 && text.length > 0 && text.length < 100) {
                        items.push({
                            tag: b.tagName,
                            text: text.substring(0, 60),
                            jsname: b.getAttribute('jsname') || '',
                            rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
                        });
                    }
                }
                return JSON.stringify(items);
            })()""")
            print(f"  All buttons after scroll: {btns}")
            
            # The consent page "Continue" button might be rendered by Google's JS framework
            # Try finding it by looking for specific jsname attributes
            result = evaluate(ws, """(function() {
                // Google uses jsname="LgbsSe" for primary action buttons commonly
                let candidates = document.querySelectorAll('[jsname="Njthtb"], [jsname="LgbsSe"], [jsname="eBSUOb"], button[jsname]');
                let items = [];
                for (let c of candidates) {
                    let rect = c.getBoundingClientRect();
                    items.push({jsname: c.getAttribute('jsname'), text: c.textContent.trim().substring(0, 50), rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}});
                }
                return JSON.stringify(items);
            })()""")
            print(f"  JSname buttons: {result}")
            
            # The issue: The consent page doesn't have a visible Continue button
            # The page says "Sign in to Kaggle" and "Google will allow Kaggle to access..."
            # But data-is-consent="false" means the consent is automatic, we just need to wait
            # OR the page needs to render fully
            
            # Let's check if there's a hidden form we can submit
            forms = evaluate(ws, """(function() {
                let forms = document.querySelectorAll('form');
                return JSON.stringify(Array.from(forms).map(f => ({
                    action: f.action?.substring(0, 100),
                    method: f.method,
                    id: f.id,
                    hidden: f.style.display === 'none' || f.hidden
                })));
            })()""")
            print(f"  Forms: {forms}")
            
            # Check data-is-consent attribute
            consent_attr = evaluate(ws, """(function() {
                let el = document.querySelector('[data-is-consent]');
                if (el) return el.getAttribute('data-is-consent');
                return 'not found';
            })()""")
            print(f"  data-is-consent: {consent_attr}")
            
            # Check if there's a "Continue" text anywhere including rendered dynamically
            # Try to find it with a broad search
            all_text = evaluate(ws, """(function() {
                let el = document.querySelector('.JYXaTc');
                if (el) return el.innerHTML.substring(0, 500);
                return 'not found';
            })()""")
            print(f"  Action area HTML: {all_text}")
            
            screenshot(ws, 'kaggle_consent_scrolled')
            
            # The action area seems empty. On the Google consent page for Kaggle,
            # with data-is-consent="false", the page is the account chooser redirect
            # that should auto-redirect. Let's wait longer.
            time.sleep(10)
            url = get_url(ws)
            print(f"  After waiting: {url}")
            
            if 'accounts.google.com' in str(url):
                # Still stuck. Let's try a different approach - use keyboard
                # Tab to find the button and Enter
                for i in range(10):
                    send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
                    time.sleep(0.1)
                    send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Tab', 'code': 'Tab', 'windowsVirtualKeyCode': 9})
                    time.sleep(0.3)
                
                # Check what's focused
                focused = evaluate(ws, """(function() {
                    let el = document.activeElement;
                    return el ? el.tagName + ' ' + el.textContent?.trim()?.substring(0, 50) + ' jsname=' + (el.getAttribute('jsname') || '') : 'none';
                })()""")
                print(f"  Focused element: {focused}")
                
                # Press Enter
                send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})
                time.sleep(0.1)
                send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'Enter', 'code': 'Enter', 'windowsVirtualKeyCode': 13})
                time.sleep(5)
                
                url = get_url(ws)
                print(f"  After Enter: {url}")
    
    url = get_url(ws)
    if 'kaggle.com' in str(url) and 'login' not in str(url) and 'accounts.google' not in str(url):
        kaggle_status = 'SUCCESS'
    elif 'accounts.google.com' in str(url):
        # Still stuck on consent - this is the consent page that needs "Continue"
        # Let's try submitting via form manipulation
        kaggle_status = 'STUCK ON GOOGLE CONSENT - Continue button not clickable'
    else:
        navigate(ws, 'https://www.kaggle.com/me')
        time.sleep(3)
        url = get_url(ws)
        if 'login' not in str(url):
            kaggle_status = 'SUCCESS'
        else:
            kaggle_status = 'FAILED'
    
    screenshot(ws, 'kaggle_final2')
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

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
- **HuggingFace** does not offer Google OAuth - used email/password registration
- **Kaggle** supports Google OAuth - account chooser works but consent page Continue button issue
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
