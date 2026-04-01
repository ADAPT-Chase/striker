#!/usr/bin/env python3
"""Fix the Google consent screen - need to click Continue button."""

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

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

# ============ KAGGLE - Fix consent ============
print("\n=== KAGGLE - Fix Google Consent ===")

pages = get_pages()
for p in pages:
    print(f"  Page: {p.get('title', '')} - {p.get('url', '')[:100]}")

# Find the Google consent page
ws_url = None
for p in pages:
    if p['type'] == 'page' and 'accounts.google.com' in p.get('url', ''):
        ws_url = p['webSocketDebuggerUrl']
        break

if not ws_url:
    # Use main page, navigate to Kaggle login again
    ws_url = [p for p in pages if p['type'] == 'page' and 'webSocketDebuggerUrl' in p][0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    navigate(ws, 'https://www.kaggle.com/account/login?phase=startRegisterTab')
    time.sleep(5)
    
    # Click Register with Google
    evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button');
        for (let b of btns) {
            if (b.textContent.includes('Register with Google')) {
                b.click();
                return 'clicked';
            }
        }
        return 'not found';
    })()""")
    time.sleep(5)
    url = get_url(ws)
    print(f"  After click: {url}")
else:
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')

url = get_url(ws)
print(f"  Current URL: {url}")

if 'accounts.google.com' in str(url):
    screenshot(ws, 'consent_debug')
    
    # Get ALL elements on the page to find the Continue button
    result = evaluate(ws, """(function() {
        let allEls = document.querySelectorAll('button, input[type="submit"], [role="button"], a');
        let items = [];
        for (let el of allEls) {
            let rect = el.getBoundingClientRect();
            let text = (el.textContent || el.value || '').trim();
            let id = el.id || '';
            let cls = el.className || '';
            let name = el.name || '';
            items.push({
                tag: el.tagName,
                text: text.substring(0, 80),
                id: id,
                name: name,
                cls: (typeof cls === 'string' ? cls : '').substring(0, 80),
                rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)},
                visible: rect.width > 0 && rect.height > 0
            });
        }
        return JSON.stringify(items);
    })()""")
    print(f"  All clickable elements: {result}")
    
    # Try to find and click "Continue" button specifically
    result2 = evaluate(ws, """(function() {
        // Look for button with id or specific attributes
        let el = document.querySelector('#submit_approve_access, #submit, button[name="submit"], [data-idom-class*="continue"], [jsname]');
        if (el) {
            return 'Found: ' + el.tagName + ' id=' + el.id + ' text=' + el.textContent.trim().substring(0, 50);
        }
        return 'not found by selector';
    })()""")
    print(f"  Submit button search: {result2}")
    
    # Try to find the Continue button by jsname or other Google-specific attributes
    result3 = evaluate(ws, """(function() {
        let els = document.querySelectorAll('[jsname], [data-idom-class]');
        let items = [];
        for (let el of els) {
            if (el.getBoundingClientRect().width > 0) {
                items.push({
                    tag: el.tagName,
                    jsname: el.getAttribute('jsname') || '',
                    text: el.textContent.trim().substring(0, 50),
                    class: (el.className || '').substring(0, 50)
                });
            }
        }
        return JSON.stringify(items.slice(0, 30));
    })()""")
    print(f"  JSname elements: {result3}")
    
    # The Google consent page typically has a "Continue" button at the bottom
    # Let's try clicking it by looking for specific patterns
    result4 = evaluate(ws, """(function() {
        // Google consent uses specific button patterns
        // Try finding by text content
        let walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
        let candidates = [];
        while (walker.nextNode()) {
            let node = walker.currentNode;
            let text = node.textContent?.trim();
            let ownText = '';
            for (let child of node.childNodes) {
                if (child.nodeType === 3) ownText += child.textContent;
            }
            ownText = ownText.trim();
            if (ownText && (ownText.toLowerCase() === 'continue' || ownText.toLowerCase() === 'sign in' || ownText.toLowerCase() === 'allow')) {
                let rect = node.getBoundingClientRect();
                if (rect.width > 0) {
                    candidates.push({
                        tag: node.tagName,
                        ownText: ownText,
                        rect: {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)}
                    });
                    node.click();
                    return 'CLICKED: ' + JSON.stringify(candidates[candidates.length-1]);
                }
            }
        }
        return 'Not found. Candidates: ' + JSON.stringify(candidates);
    })()""")
    print(f"  Continue button click: {result4}")
    time.sleep(5)
    
    url = get_url(ws)
    print(f"  After Continue: {url}")
    screenshot(ws, 'after_continue')
    
    if 'accounts.google.com' in str(url):
        # Still on Google - try mouse click approach
        # Find the button coordinates and use Input.dispatchMouseEvent
        coords = evaluate(ws, """(function() {
            // Look for bottom-right area buttons (typically where Continue is)
            let btns = document.querySelectorAll('button, div[role="button"]');
            for (let btn of btns) {
                let rect = btn.getBoundingClientRect();
                // Continue button is usually in the bottom portion
                if (rect.y > 300 && rect.width > 50 && rect.height > 20) {
                    return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim().substring(0, 50)});
                }
            }
            // Just try scrolling down and looking
            window.scrollTo(0, document.body.scrollHeight);
            return null;
        })()""")
        print(f"  Bottom button: {coords}")
        
        if coords:
            data = json.loads(coords)
            print(f"  Mouse clicking at ({data['x']}, {data['y']}) - '{data['text']}'")
            send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mousePressed', 'x': data['x'], 'y': data['y'], 'button': 'left', 'clickCount': 1})
            time.sleep(0.1)
            send_cmd(ws, 'Input.dispatchMouseEvent', {'type': 'mouseReleased', 'x': data['x'], 'y': data['y'], 'button': 'left', 'clickCount': 1})
            time.sleep(5)
            
            url = get_url(ws)
            print(f"  After mouse click: {url}")
            screenshot(ws, 'after_mouseclick_consent')

# Now check the full HTML of the consent page
if 'accounts.google.com' in str(get_url(ws)):
    html = evaluate(ws, 'document.body?.innerHTML')
    with open('/home/x/striker/consent_page.html', 'w') as f:
        f.write(html or '')
    print("  Saved consent page HTML for analysis")
    
    # Try form submission approach
    result5 = evaluate(ws, """(function() {
        let forms = document.querySelectorAll('form');
        let formInfo = [];
        for (let f of forms) {
            formInfo.push({
                action: f.action,
                method: f.method,
                id: f.id,
                inputs: Array.from(f.querySelectorAll('input, button')).map(i => ({
                    type: i.type, name: i.name, value: (i.value || '').substring(0, 30), id: i.id
                }))
            });
        }
        return JSON.stringify(formInfo);
    })()""")
    print(f"  Forms on page: {result5}")

ws.close()
