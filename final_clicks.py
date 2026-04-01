#!/usr/bin/env python3
"""Final clicks - Click Continue on Google consent, fix HF profile."""

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
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': int(x), 'y': int(y), 'button': 'left', 'clickCount': 1})
    time.sleep(0.05)
    send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': int(x), 'y': int(y), 'button': 'left', 'clickCount': 1})

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

# ============ KAGGLE - Click Continue on consent page ============
print("\n=== KAGGLE - Click Continue ===")
try:
    pages = get_pages()
    # Find the Google consent page
    ws_url = None
    for p in pages:
        if p['type'] == 'page' and 'accounts.google.com' in p.get('url', ''):
            ws_url = p['webSocketDebuggerUrl']
            print(f"  Found Google page: {p['url'][:100]}")
            break
    
    if not ws_url:
        # Use first page tab
        for p in pages:
            if p['type'] == 'page' and 'webSocketDebuggerUrl' in p:
                ws_url = p['webSocketDebuggerUrl']
                break
    
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    url = get_url(ws)
    print(f"  Current URL: {url}")
    
    if 'accounts.google.com' not in str(url):
        # Need to start Kaggle OAuth flow again
        send_cmd(ws, 'Emulation.setDeviceMetricsOverride', {
            'width': 1280, 'height': 1024, 'deviceScaleFactor': 1, 'mobile': False
        })
        navigate(ws, 'https://www.kaggle.com/account/login?phase=startRegisterTab')
        time.sleep(5)
        evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button, a');
            for (let b of btns) {
                if (b.textContent.includes('OK, Got it')) { b.click(); break; }
            }
        })()""")
        time.sleep(1)
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.includes('Register with Google') || btn.textContent.includes('Sign in with Google')) {
                    let rect = btn.getBoundingClientRect();
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2});
                }
            }
            return null;
        })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
        url = get_url(ws)
        print(f"  After OAuth start: {url}")
    
    if 'accounts.google.com' in str(url) and 'accountchooser' in str(url):
        # Click account
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
        print(f"  After account: {url}")
    
    # Now on consent page - find and click Continue button
    if 'accounts.google.com' in str(url):
        screenshot(ws, 'kaggle_precontinue')
        
        # Get the Continue button position
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.trim() === 'Continue') {
                    let rect = btn.getBoundingClientRect();
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, w: rect.width, h: rect.height});
                }
            }
            return null;
        })()""")
        print(f"  Continue button coords: {coords}")
        
        if coords:
            data = json.loads(coords)
            print(f"  Clicking Continue at ({data['x']}, {data['y']})")
            mouse_click(ws, data['x'], data['y'])
            time.sleep(8)
            
            url = get_url(ws)
            print(f"  After Continue click: {url}")
            screenshot(ws, 'kaggle_after_continue')
            
            if 'accounts.google.com' in str(url):
                # Try DOM click instead
                result = evaluate(ws, """(function() {
                    let btns = document.querySelectorAll('button');
                    for (let btn of btns) {
                        if (btn.textContent.trim() === 'Continue') {
                            // Try dispatchEvent
                            btn.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
                            return 'dispatched click';
                        }
                    }
                    return 'not found';
                })()""")
                print(f"  DOM click: {result}")
                time.sleep(5)
                url = get_url(ws)
                print(f"  After DOM click: {url}")
                
                if 'accounts.google.com' in str(url):
                    # Try the parent div click with jsname
                    result2 = evaluate(ws, """(function() {
                        let el = document.querySelector('[jsname="uRHG6"]');
                        if (el) {
                            el.click();
                            return 'clicked uRHG6';
                        }
                        el = document.querySelector('[jsname="Njthtb"]');
                        if (el) {
                            el.click();
                            return 'clicked Njthtb';
                        }
                        return 'not found';
                    })()""")
                    print(f"  JSname click: {result2}")
                    time.sleep(5)
                    url = get_url(ws)
                    print(f"  After jsname click: {url}")
        
        # Final attempt: form submit or direct navigation
        if 'accounts.google.com' in str(get_url(ws)):
            # Try using CDP DOM methods to find and interact with the button
            # Use DOM.querySelector to get the node
            result = send_cmd(ws, 'DOM.getDocument')
            if result and 'result' in result:
                root_id = result['result']['root']['nodeId']
                # Find the Continue button
                qresult = send_cmd(ws, 'DOM.querySelector', {
                    'nodeId': root_id,
                    'selector': 'button[jsname="LgbsSe"]'
                })
                if qresult and 'result' in qresult:
                    node_id = qresult['result']['nodeId']
                    print(f"  Found button node: {node_id}")
                    # Focus and click via DOM
                    send_cmd(ws, 'DOM.focus', {'nodeId': node_id})
                    time.sleep(0.5)
                    # Get box model for exact coordinates
                    box = send_cmd(ws, 'DOM.getBoxModel', {'nodeId': node_id})
                    if box and 'result' in box:
                        content = box['result']['model']['content']
                        # content is [x1,y1, x2,y2, x3,y3, x4,y4]
                        cx = (content[0] + content[2]) / 2
                        cy = (content[1] + content[5]) / 2
                        print(f"  Box model center: ({cx}, {cy})")
                
                # Find the second button (Continue, not Cancel)
                qresult_all = send_cmd(ws, 'DOM.querySelectorAll', {
                    'nodeId': root_id,
                    'selector': 'button[jsname="LgbsSe"]'
                })
                if qresult_all and 'result' in qresult_all:
                    nodes = qresult_all['result']['nodeIds']
                    print(f"  Found {len(nodes)} buttons with jsname=LgbsSe")
                    if len(nodes) >= 2:
                        # Second one should be Continue
                        continue_node = nodes[1]
                        send_cmd(ws, 'DOM.focus', {'nodeId': continue_node})
                        time.sleep(0.5)
                        box = send_cmd(ws, 'DOM.getBoxModel', {'nodeId': continue_node})
                        if box and 'result' in box:
                            content = box['result']['model']['content']
                            cx = (content[0] + content[2]) / 2
                            cy = (content[1] + content[5]) / 2
                            print(f"  Continue button center: ({cx}, {cy})")
                            mouse_click(ws, cx, cy)
                            time.sleep(8)
                            url = get_url(ws)
                            print(f"  After precise click: {url}")
                            screenshot(ws, 'kaggle_after_precise')
    
    # Check final state
    url = get_url(ws)
    if 'kaggle.com' in str(url) and 'login' not in str(url) and 'accounts.google' not in str(url):
        print("  SUCCESS - Redirected to Kaggle!")
        # Check if there's a registration form to complete
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  Page: {(page_text or '')[:200]}")
        kaggle_status = 'SUCCESS - Signed in via Google OAuth'
    elif 'accounts.google.com' in str(url):
        kaggle_status = 'STUCK - Google consent page not responding to clicks'
    else:
        navigate(ws, 'https://www.kaggle.com/me')
        time.sleep(3)
        url = get_url(ws)
        if 'login' not in str(url):
            kaggle_status = 'SUCCESS'
        else:
            kaggle_status = 'FAILED'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

# ============ HF - Fix profile form ============
print("\n=== HuggingFace - Fix Profile ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    url = get_url(ws)
    if 'join' not in str(url):
        navigate(ws, 'https://huggingface.co/join')
        time.sleep(3)
    
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
    print(f"  Page: {(page_text or '')[:200]}")
    
    if 'Complete your profile' in str(page_text):
        # Clear twitter/github fields that got incorrectly set, set fields properly
        result = evaluate(ws, """(function() {
            let results = [];
            let inputs = document.querySelectorAll('input[name]');
            for (let input of inputs) {
                if (input.name === 'username') {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, 'novacline602');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('username=novacline602');
                }
                if (input.name === 'fullname') {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, 'Nova Cline');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('fullname=Nova Cline');
                }
                if (input.name === 'twitter') {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, '');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('twitter cleared');
                }
                if (input.name === 'github') {
                    let nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                    nativeInputValueSetter.call(input, '');
                    input.dispatchEvent(new Event('input', {bubbles: true}));
                    results.push('github cleared');
                }
            }
            // Check TOS checkbox
            let cbs = document.querySelectorAll('input[type="checkbox"]');
            for (let cb of cbs) {
                if (!cb.checked) cb.click();
                results.push('checkbox checked');
            }
            return JSON.stringify(results);
        })()""")
        print(f"  Fields set: {result}")
        time.sleep(1)
        screenshot(ws, 'hf_form_fixed')
        
        # Now use mouse click on Create Account button
        coords = evaluate(ws, """(function() {
            let btns = document.querySelectorAll('button');
            for (let btn of btns) {
                if (btn.textContent.trim().includes('Create Account')) {
                    let rect = btn.getBoundingClientRect();
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim()});
                }
            }
            return null;
        })()""")
        print(f"  Create button: {coords}")
        
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(5)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  After submit: {url}")
        print(f"  Text: {(page_text or '')[:300]}")
        screenshot(ws, 'hf_after_create')
        
        if 'join' not in str(url):
            hf_status = f'SUCCESS - Account created'
        elif 'error' in str(page_text or '').lower() or 'already' in str(page_text or '').lower():
            hf_status = f'FAILED - {(page_text or "")[:100]}'
        elif 'verify' in str(page_text or '').lower() or 'email' in str(page_text or '').lower():
            hf_status = 'PENDING EMAIL VERIFICATION'
        else:
            hf_status = f'IN PROGRESS - still on join page'
    else:
        # Check if already logged in
        navigate(ws, 'https://huggingface.co/settings/profile')
        time.sleep(3)
        url = get_url(ws)
        if 'login' not in str(url):
            hf_status = 'SUCCESS - Already logged in'
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

## Notes
- **Replicate** only supports GitHub OAuth, not Google OAuth
- **HuggingFace** does not offer Google OAuth as public login - used email/password registration
- **Kaggle** supports Google OAuth (Register with Google button)
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
