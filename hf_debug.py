#!/usr/bin/env python3
"""Debug HF form - check what's preventing submission."""

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

url = get_url(ws)
print(f"Current: {url}")

# Check if we're on the profile page
page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
print(f"Text: {(page_text or '')[:200]}")

if 'Complete your profile' in str(page_text):
    # Check all field values
    vals = evaluate(ws, """(function() {
        let inputs = document.querySelectorAll('input[name], textarea[name]');
        return JSON.stringify(Array.from(inputs).map(i => ({name: i.name, value: i.value, type: i.type, checked: i.checked})));
    })()""")
    print(f"Field values: {vals}")
    
    # Check for hidden validation errors
    errors = evaluate(ws, """(function() {
        let all = document.querySelectorAll('*');
        let errs = [];
        for (let el of all) {
            let text = el.textContent?.trim();
            let style = window.getComputedStyle(el);
            if (style.color === 'rgb(239, 68, 68)' || style.color === 'rgb(220, 38, 38)' || 
                el.classList?.contains('text-red-500') || el.classList?.contains('text-danger') ||
                el.classList?.contains('error') || el.className?.includes?.('error') || el.className?.includes?.('invalid')) {
                if (text && text.length < 100 && text.length > 0) {
                    errs.push({text: text, class: el.className?.substring?.(0, 50) || ''});
                }
            }
        }
        return JSON.stringify(errs);
    })()""")
    print(f"Styled errors: {errors}")
    
    # Check button state
    btn_state = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button');
        for (let btn of btns) {
            if (btn.textContent.includes('Create Account')) {
                return JSON.stringify({
                    disabled: btn.disabled,
                    text: btn.textContent.trim(),
                    class: btn.className?.substring(0, 100),
                    ariaDisabled: btn.getAttribute('aria-disabled'),
                    type: btn.type
                });
            }
        }
        return null;
    })()""")
    print(f"Button state: {btn_state}")
    
    # Check if the form uses fetch/XHR for submission
    # Listen for network requests when clicking
    send_cmd(ws, 'Network.enable')
    
    # Check if there's a form element
    form_info = evaluate(ws, """(function() {
        let forms = document.querySelectorAll('form');
        return JSON.stringify(Array.from(forms).map(f => ({
            action: f.action?.substring(0, 100),
            method: f.method,
            id: f.id,
            class: f.className?.substring(0, 50),
            inputCount: f.querySelectorAll('input').length
        })));
    })()""")
    print(f"Forms: {form_info}")
    
    # The issue might be that the form is a Svelte/React component
    # Let's try submitting the form directly
    result = evaluate(ws, """(function() {
        let form = document.querySelector('form');
        if (form) {
            // Get form data
            let fd = new FormData(form);
            let data = {};
            for (let [k, v] of fd.entries()) {
                data[k] = v;
            }
            return JSON.stringify({action: form.action, method: form.method, data: data});
        }
        return null;
    })()""")
    print(f"Form data: {result}")
    
    # Maybe try submitting via fetch
    result2 = evaluate(ws, """(function() {
        let form = document.querySelector('form');
        if (form) {
            form.submit();
            return 'submitted';
        }
        return 'no form';
    })()""")
    print(f"Form submit: {result2}")
    time.sleep(5)
    
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"After form submit: {url}")
    print(f"Text: {(page_text or '')[:300]}")
    screenshot(ws, 'hf_after_form_submit')

elif 'Email Address' in str(page_text):
    print("On email page, need to restart registration")
    # Just go to the join page and redo
    navigate(ws, 'https://huggingface.co/join')
    time.sleep(3)
    
    # Use insertText for email
    coords = evaluate(ws, """(function() {
        let input = document.querySelector('input[type="email"], input[name="email"]');
        if (input) { let r = input.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
        return null;
    })()""")
    if coords:
        data = json.loads(coords)
        mouse_click(ws, data['x'], data['y'])
        time.sleep(0.3)
        send_cmd(ws, 'Input.insertText', {'text': 'novacline602@gmail.com'})
        time.sleep(0.3)
    
    coords = evaluate(ws, """(function() {
        let input = document.querySelector('input[type="password"], input[name="password"]');
        if (input) { let r = input.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); }
        return null;
    })()""")
    if coords:
        data = json.loads(coords)
        mouse_click(ws, data['x'], data['y'])
        time.sleep(0.3)
        send_cmd(ws, 'Input.insertText', {'text': 'NovaCline2026!Sec'})
        time.sleep(0.3)
    
    # Click Next
    coords = evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button');
        for (let btn of btns) { if (btn.textContent.trim() === 'Next') { let r = btn.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); } }
        return null;
    })()""")
    if coords:
        data = json.loads(coords)
        mouse_click(ws, data['x'], data['y'])
        time.sleep(3)
    
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 300)')
    print(f"After Next: {(page_text or '')[:200]}")
    
    if 'Complete your profile' in str(page_text):
        # Fill username
        coords = evaluate(ws, """(function() { let i = document.querySelector('input[name="username"]'); if (i) { let r = i.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); } return null; })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.2)
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'modifiers': 2})
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'modifiers': 2})
            send_cmd(ws, 'Input.insertText', {'text': 'novacline602'})
            time.sleep(0.5)
        
        # Full name
        coords = evaluate(ws, """(function() { let i = document.querySelector('input[name="fullname"]'); if (i) { let r = i.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); } return null; })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.2)
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyDown', 'key': 'a', 'modifiers': 2})
            send_cmd(ws, 'Input.dispatchKeyEvent', {'type': 'keyUp', 'key': 'a', 'modifiers': 2})
            send_cmd(ws, 'Input.insertText', {'text': 'Nova Cline'})
            time.sleep(0.5)
        
        # TOS
        coords = evaluate(ws, """(function() { let cb = document.querySelector('input[type="checkbox"]'); if (cb && !cb.checked) { let r = cb.getBoundingClientRect(); return JSON.stringify({x: r.x+r.width/2, y: r.y+r.height/2}); } return null; })()""")
        if coords:
            data = json.loads(coords)
            mouse_click(ws, data['x'], data['y'])
            time.sleep(0.3)
        
        # Try form.submit() instead of button click
        result = evaluate(ws, """(function() {
            let form = document.querySelector('form');
            if (form) {
                form.submit();
                return 'submitted';
            }
            return 'no form';
        })()""")
        print(f"Form submit: {result}")
        time.sleep(5)
        
        url = get_url(ws)
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"After submit: {url}")
        print(f"Text: {(page_text or '')[:300]}")
        screenshot(ws, 'hf_debug_final')

ws.close()
