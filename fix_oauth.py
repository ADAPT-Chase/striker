#!/usr/bin/env python3
"""Fix OAuth logins - HuggingFace needs direct approach, Kaggle needs proper click."""

import json, subprocess, time, websocket

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

def navigate(ws, url):
    print(f"  Navigating to {url}")
    resp = send_cmd(ws, 'Page.navigate', {'url': url})
    time.sleep(4)
    return resp

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
        import base64
        data = base64.b64decode(resp['result']['data'])
        path = f'/home/x/striker/{name}.png'
        with open(path, 'wb') as f:
            f.write(data)
        print(f"  Screenshot: {path}")

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

def handle_google_consent(ws, max_attempts=5):
    """Handle Google account chooser and consent screens."""
    for attempt in range(max_attempts):
        time.sleep(2)
        url = get_url(ws)
        print(f"  [Google] URL: {url}")
        
        if not url or 'accounts.google.com' not in url:
            print("  [Google] No longer on Google - done")
            return True
        
        screenshot(ws, f'google_consent_{attempt}')
        
        # Get page text for debugging
        text = evaluate(ws, 'document.body?.innerText?.substring(0, 1000)')
        print(f"  [Google] Page text: {(text or '')[:300]}")
        
        # Try clicking account
        result = evaluate(ws, """(function() {
            // Account chooser - click the account
            let accounts = document.querySelectorAll('[data-email], [data-identifier], div[data-authuser]');
            if (accounts.length > 0) {
                accounts[0].click();
                return 'clicked account element';
            }
            
            // Try li elements that contain email
            let lis = document.querySelectorAll('li');
            for (let li of lis) {
                if (li.textContent.includes('@gmail.com') || li.textContent.includes('novacline')) {
                    li.click();
                    return 'clicked li with email';
                }
            }
            
            // Try any clickable div with email
            let divs = document.querySelectorAll('div[role="link"], div[tabindex="0"], div[data-profileindex]');
            for (let d of divs) {
                if (d.textContent.includes('@') || d.textContent.includes('novacline')) {
                    d.click();
                    return 'clicked div with email';
                }
            }
            
            // "Continue" / "Allow" / "Confirm" buttons
            let btns = document.querySelectorAll('button, [role="button"], input[type="submit"]');
            for (let btn of btns) {
                let t = (btn.textContent || btn.value || '').toLowerCase();
                if (t.includes('continue') || t.includes('allow') || t.includes('next') || t.includes('confirm') || t.includes('agree')) {
                    btn.click();
                    return 'clicked button: ' + t.trim();
                }
            }
            
            return 'nothing clickable found';
        })()""")
        print(f"  [Google] Action: {result}")
        time.sleep(3)
    
    return False

# ============ HUGGING FACE (retry) ============
print("\n=== HUGGING FACE (retry) ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    # Go to HF login page
    navigate(ws, 'https://huggingface.co/login')
    time.sleep(3)
    
    # Get full page HTML to find the Google button
    html = evaluate(ws, 'document.body?.innerHTML?.substring(0, 5000)')
    print(f"  Page HTML snippet: {(html or '')[:500]}")
    
    # HuggingFace login page - look for all links
    links = evaluate(ws, """(function() {
        let all = document.querySelectorAll('a');
        return JSON.stringify(Array.from(all).map(a => ({text: a.textContent.trim().substring(0,50), href: a.href})).filter(x => x.href.length > 0));
    })()""")
    print(f"  All links: {links}")
    
    # The HF login page might not have Google OAuth on the main page
    # Try going to the signup page which might have OAuth
    navigate(ws, 'https://huggingface.co/join')
    time.sleep(3)
    screenshot(ws, 'hf_join')
    
    links2 = evaluate(ws, """(function() {
        let all = document.querySelectorAll('a, button');
        return JSON.stringify(Array.from(all).map(a => ({text: a.textContent.trim().substring(0,50), href: a.href || '', tag: a.tagName})).filter(x => x.text.length > 0));
    })()""")
    print(f"  Join page elements: {links2}")
    
    # HuggingFace might use SSO login - try the SSO endpoint
    # Actually, let me check if there's a "Sign in with Google" specifically
    # HF requires org SSO or specific login methods
    # Let me try to create account with email/password instead
    
    # Actually, let me try the OAuth URL pattern directly
    navigate(ws, 'https://huggingface.co/oauth/google/authorize')
    time.sleep(3)
    url = get_url(ws)
    print(f"  Direct OAuth URL result: {url}")
    screenshot(ws, 'hf_direct_oauth')
    
    if 'accounts.google.com' in str(url):
        handle_google_consent(ws)
        time.sleep(3)
        url = get_url(ws)
        print(f"  After Google: {url}")
        screenshot(ws, 'hf_after_google2')
    
    # Check if HF has Google OAuth at all or just email-based
    # Let's try logging in with email/password approach instead
    # For now, let's check the current state
    navigate(ws, 'https://huggingface.co/settings/profile')
    time.sleep(3)
    url = get_url(ws)
    screenshot(ws, 'hf_final')
    
    if 'login' in str(url):
        print("  HF: Still not logged in - Google OAuth may not be available as a public option")
        hf_status = 'FAILED - Google OAuth not available as public login option'
    else:
        hf_status = 'SUCCESS'

    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    hf_status = f'ERROR - {e}'

# ============ KAGGLE (retry) ============
print("\n=== KAGGLE (retry) ===")
try:
    ws_url = get_pages()[0]['webSocketDebuggerUrl']
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    # First dismiss cookie banner
    navigate(ws, 'https://www.kaggle.com/account/login?phase=startRegisterTab')
    time.sleep(5)
    
    # Dismiss cookies
    evaluate(ws, """(function() {
        let btns = document.querySelectorAll('button, a');
        for (let b of btns) {
            if (b.textContent.includes('OK, Got it') || b.textContent.includes('Accept')) {
                b.click();
                return 'dismissed cookies';
            }
        }
        return 'no cookie banner';
    })()""")
    time.sleep(2)
    
    screenshot(ws, 'kaggle_retry_page')
    
    # Get all visible elements
    result = evaluate(ws, """(function() {
        let all = document.querySelectorAll('*');
        let clickable = [];
        for (let el of all) {
            let rect = el.getBoundingClientRect();
            if (rect.width > 0 && rect.height > 0) {
                let text = el.textContent?.trim();
                if (text && text.includes('Google') && text.length < 100) {
                    clickable.push({
                        tag: el.tagName, 
                        text: text.substring(0, 60),
                        class: el.className?.substring?.(0, 60) || '',
                        rect: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}
                    });
                }
            }
        }
        return JSON.stringify(clickable);
    })()""")
    print(f"  Google elements: {result}")
    
    # Try clicking "Register with Google" using mouse click at coordinates
    coords = evaluate(ws, """(function() {
        let all = document.querySelectorAll('li, div, button, a, span');
        for (let el of all) {
            let text = el.textContent?.trim();
            if (text === 'Register with Google' || text === 'Sign in with Google') {
                let rect = el.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: text});
            }
        }
        // Try partial match
        for (let el of all) {
            let text = el.textContent?.trim();
            if (text && text.includes('with Google') && !text.includes('\\n') && text.length < 30) {
                let rect = el.getBoundingClientRect();
                return JSON.stringify({x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: text});
            }
        }
        return null;
    })()""")
    print(f"  Google button coords: {coords}")
    
    if coords:
        coords_data = json.loads(coords)
        x, y = coords_data['x'], coords_data['y']
        print(f"  Clicking at ({x}, {y})")
        
        # Use CDP Input.dispatchMouseEvent
        send_cmd(ws, 'Input.dispatchMouseEvent', {
            'type': 'mousePressed',
            'x': x, 'y': y,
            'button': 'left',
            'clickCount': 1
        })
        time.sleep(0.1)
        send_cmd(ws, 'Input.dispatchMouseEvent', {
            'type': 'mouseReleased',
            'x': x, 'y': y,
            'button': 'left',
            'clickCount': 1
        })
        time.sleep(5)
    
    url = get_url(ws)
    print(f"  After click URL: {url}")
    screenshot(ws, 'kaggle_after_mouseclick')
    
    if 'accounts.google.com' in str(url):
        handle_google_consent(ws)
        time.sleep(3)
    
    # Maybe Kaggle opens a popup - check for new windows
    pages = get_pages()
    print(f"  Open pages: {len(pages)}")
    for p in pages:
        if p['type'] == 'page':
            print(f"    - {p.get('title', '')}: {p.get('url', '')}")
            if 'accounts.google.com' in p.get('url', ''):
                print(f"  Found Google popup!")
                popup_ws = websocket.create_connection(p['webSocketDebuggerUrl'], timeout=10)
                send_cmd_popup = lambda m, p=None: send_cmd.__func__(popup_ws, m, p) if False else None
                # Use same send_cmd but with popup ws
                old_ws = ws
                ws = popup_ws
                handle_google_consent(ws)
                ws = old_ws
                popup_ws.close()
                time.sleep(5)
    
    url = get_url(ws)
    print(f"  Final URL: {url}")
    screenshot(ws, 'kaggle_final')
    
    # Check if logged in
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  Page text: {(page_text or '')[:200]}")
    
    # Navigate to account page
    navigate(ws, 'https://www.kaggle.com/me')
    time.sleep(3)
    url = get_url(ws)
    print(f"  /me URL: {url}")
    screenshot(ws, 'kaggle_me')
    
    if 'login' in str(url).lower():
        kaggle_status = 'FAILED - not logged in'
    else:
        kaggle_status = 'SUCCESS - logged in'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    kaggle_status = f'ERROR - {e}'

# Update accounts.md
results = {
    'huggingface': hf_status,
    'kaggle': kaggle_status,
    'replicate': 'SKIPPED - Google OAuth not available (GitHub only)'
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
- Replicate only supports GitHub OAuth, not Google
- HuggingFace may not offer Google OAuth as a public login method
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)
print("\nUpdated ~/striker/accounts.md")
