#!/usr/bin/env python3
"""Sign into HuggingFace, Kaggle, and Replicate via Google OAuth using CDP."""

import json, subprocess, time, websocket, sys

def get_pages():
    return json.loads(subprocess.check_output(['curl', '-s', 'http://localhost:9222/json']).decode())

def get_main_page_ws():
    pages = get_pages()
    for p in pages:
        if p['type'] == 'page' and 'webSocketDebuggerUrl' in p:
            return p['webSocketDebuggerUrl']
    return pages[0]['webSocketDebuggerUrl']

cmd_id = 0
def send_cmd(ws, method, params=None):
    global cmd_id
    cmd_id += 1
    msg = {'id': cmd_id, 'method': method}
    if params:
        msg['params'] = params
    ws.send(json.dumps(msg))
    # Read responses until we get ours
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

def evaluate(ws, expr, timeout=10):
    resp = send_cmd(ws, 'Runtime.evaluate', {
        'expression': expr,
        'awaitPromise': True,
        'timeout': timeout * 1000
    })
    if resp and 'result' in resp:
        return resp['result'].get('result', {}).get('value')
    return None

def get_url(ws):
    return evaluate(ws, 'window.location.href')

def wait_for_url_change(ws, old_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        current = get_url(ws)
        if current and current != old_url:
            return current
        time.sleep(1)
    return get_url(ws)

def screenshot(ws, name="screenshot"):
    resp = send_cmd(ws, 'Page.captureScreenshot', {'format': 'png'})
    if resp and 'result' in resp:
        import base64
        data = base64.b64decode(resp['result']['data'])
        path = f'/home/x/striker/{name}.png'
        with open(path, 'wb') as f:
            f.write(data)
        print(f"  Screenshot saved: {path}")
        return path
    return None

def click_google_oauth(ws, site_name):
    """Try various strategies to find and click Google sign-in button."""
    strategies = [
        # Generic: buttons/links with "Google" text
        """(function() {
            let els = document.querySelectorAll('a, button, [role="button"]');
            for (let el of els) {
                let text = (el.textContent || '').toLowerCase();
                if (text.includes('google') && (text.includes('sign') || text.includes('log') || text.includes('continue') || text.includes('connect'))) {
                    el.click();
                    return 'clicked: ' + el.textContent.trim().substring(0, 80);
                }
            }
            return 'not found';
        })()""",
        # By class or data attributes common for Google OAuth
        """(function() {
            let el = document.querySelector('[data-provider="google"], .google-btn, [href*="google"], [href*="oauth/google"], [href*="auth/google"]');
            if (el) { el.click(); return 'clicked href/data match'; }
            return 'not found';
        })()""",
        # Any link containing 'google' in href
        """(function() {
            let els = document.querySelectorAll('a[href*="google"], a[href*="oauth"]');
            for (let el of els) {
                if (el.href.includes('google')) {
                    el.click();
                    return 'clicked: ' + el.href.substring(0, 100);
                }
            }
            return 'not found';
        })()""",
    ]
    
    for i, strategy in enumerate(strategies):
        result = evaluate(ws, strategy)
        print(f"  Strategy {i}: {result}")
        if result and 'not found' not in str(result):
            return True
        time.sleep(1)
    return False

def handle_google_account_chooser(ws, timeout=15):
    """If Google shows account chooser, pick the account."""
    start = time.time()
    while time.time() - start < timeout:
        url = get_url(ws)
        if not url:
            time.sleep(1)
            continue
        
        if 'accounts.google.com' in url:
            print(f"  On Google auth page: {url}")
            time.sleep(2)
            
            # Try to click the account email
            result = evaluate(ws, """(function() {
                // Look for account chooser
                let els = document.querySelectorAll('[data-email], [data-identifier]');
                for (let el of els) {
                    el.click();
                    return 'clicked account: ' + (el.getAttribute('data-email') || el.getAttribute('data-identifier'));
                }
                // Look for email in text
                let allEls = document.querySelectorAll('li, div[role="link"], div[tabindex]');
                for (let el of allEls) {
                    if (el.textContent.includes('novacline602') || el.textContent.includes('@gmail.com')) {
                        el.click();
                        return 'clicked text match';
                    }
                }
                // "Continue" or "Allow" button
                let btns = document.querySelectorAll('button, [role="button"]');
                for (let btn of btns) {
                    let t = btn.textContent.toLowerCase();
                    if (t.includes('continue') || t.includes('allow') || t.includes('next') || t.includes('confirm')) {
                        btn.click();
                        return 'clicked: ' + btn.textContent.trim();
                    }
                }
                return 'no action taken - page text: ' + document.body?.innerText?.substring(0, 300);
            })()""")
            print(f"  Google chooser result: {result}")
            time.sleep(3)
            
            # Check if still on Google
            new_url = get_url(ws)
            if new_url and 'accounts.google.com' not in new_url:
                return True
            
            # May need to click "Allow" on consent screen
            time.sleep(2)
            result2 = evaluate(ws, """(function() {
                let btns = document.querySelectorAll('button, [role="button"]');
                for (let btn of btns) {
                    let t = btn.textContent.toLowerCase();
                    if (t.includes('continue') || t.includes('allow') || t.includes('confirm') || t.includes('accept')) {
                        btn.click();
                        return 'clicked consent: ' + btn.textContent.trim();
                    }
                }
                // Try submit buttons
                let submits = document.querySelectorAll('input[type="submit"], button[type="submit"]');
                for (let s of submits) {
                    s.click();
                    return 'clicked submit';
                }
                return 'no consent button found';
            })()""")
            print(f"  Consent result: {result2}")
            time.sleep(3)
            return True
        else:
            # Not on Google anymore
            return True
        time.sleep(1)
    return False

results = {}

# ============ HUGGING FACE ============
print("\n=== HUGGING FACE ===")
try:
    ws_url = get_main_page_ws()
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    navigate(ws, 'https://huggingface.co/login')
    time.sleep(3)
    screenshot(ws, 'hf_login_page')
    
    # Look for sign in with Google
    result = evaluate(ws, """(function() {
        // HuggingFace has specific OAuth buttons
        let els = document.querySelectorAll('a, button');
        let found = [];
        for (let el of els) {
            let text = (el.textContent || '').trim();
            if (text.toLowerCase().includes('google')) {
                found.push(text);
            }
        }
        return JSON.stringify(found);
    })()""")
    print(f"  Google buttons found: {result}")
    
    clicked = click_google_oauth(ws, 'huggingface')
    time.sleep(5)
    
    if not clicked:
        # Try direct URL approach
        print("  Trying direct SSO URL...")
        # HF uses /login?sso=google
        navigate(ws, 'https://huggingface.co/login?next=%2F&sso=google')
        time.sleep(5)
    
    screenshot(ws, 'hf_after_click')
    url = get_url(ws)
    print(f"  Current URL after click: {url}")
    
    handle_google_account_chooser(ws)
    time.sleep(3)
    
    url = get_url(ws)
    print(f"  URL after Google auth: {url}")
    screenshot(ws, 'hf_after_google')
    
    # Check if we need to complete signup (username etc)
    if 'join' in str(url) or 'signup' in str(url):
        print("  Completing HF signup...")
        evaluate(ws, """(function() {
            let submit = document.querySelector('button[type="submit"]');
            if (submit) submit.click();
            return 'submitted';
        })()""")
        time.sleep(3)
    
    # Check login status
    time.sleep(2)
    navigate(ws, 'https://huggingface.co/settings/profile')
    time.sleep(3)
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  Profile URL: {url}")
    print(f"  Profile text: {page_text[:200] if page_text else 'none'}")
    screenshot(ws, 'hf_profile')
    
    if 'login' in str(url).lower():
        results['huggingface'] = 'FAILED - redirected to login'
    else:
        results['huggingface'] = 'SUCCESS - signed in'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    results['huggingface'] = f'ERROR - {e}'

# ============ KAGGLE ============
print("\n=== KAGGLE ===")
try:
    ws_url = get_main_page_ws()
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    navigate(ws, 'https://www.kaggle.com/account/login?phase=startRegisterTab')
    time.sleep(5)
    screenshot(ws, 'kaggle_login_page')
    
    # Check page content
    result = evaluate(ws, """(function() {
        let els = document.querySelectorAll('a, button, [role="button"], li');
        let items = [];
        for (let el of els) {
            let t = el.textContent.trim();
            if (t.toLowerCase().includes('google') || t.toLowerCase().includes('sign') || t.toLowerCase().includes('register')) {
                items.push(t.substring(0, 80));
            }
        }
        return JSON.stringify(items);
    })()""")
    print(f"  Relevant buttons: {result}")
    
    # Kaggle uses "Sign in with Google" or "Register with Google"
    clicked = click_google_oauth(ws, 'kaggle')
    time.sleep(5)
    
    if not clicked:
        # Try clicking via Google icon/image
        result = evaluate(ws, """(function() {
            let el = document.querySelector('[data-node-id*="google"], [class*="google"], img[alt*="Google"]');
            if (el) { el.click(); return 'clicked'; }
            // Try any sign-in related link
            let links = document.querySelectorAll('a');
            for (let l of links) {
                if (l.href && l.href.includes('google')) {
                    l.click();
                    return 'clicked link: ' + l.href.substring(0, 100);
                }
            }
            return 'not found';
        })()""")
        print(f"  Alt strategy: {result}")
        time.sleep(5)
    
    screenshot(ws, 'kaggle_after_click')
    url = get_url(ws)
    print(f"  Current URL: {url}")
    
    handle_google_account_chooser(ws)
    time.sleep(3)
    
    url = get_url(ws)
    print(f"  URL after Google auth: {url}")
    screenshot(ws, 'kaggle_after_google')
    
    # Check if we need to accept terms or set username
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    print(f"  Page text: {(page_text or '')[:200]}")
    
    # If there's a terms/privacy acceptance needed
    if page_text and ('accept' in page_text.lower() or 'agree' in page_text.lower() or 'terms' in page_text.lower()):
        evaluate(ws, """(function() {
            let checkboxes = document.querySelectorAll('input[type="checkbox"]');
            checkboxes.forEach(c => { if (!c.checked) c.click(); });
            let btns = document.querySelectorAll('button');
            for (let b of btns) {
                if (b.textContent.toLowerCase().includes('accept') || b.textContent.toLowerCase().includes('agree') || b.textContent.toLowerCase().includes('submit')) {
                    b.click();
                    return 'accepted';
                }
            }
            return 'no accept button';
        })()""")
        time.sleep(3)
    
    # Check login
    navigate(ws, 'https://www.kaggle.com/account')
    time.sleep(3)
    url = get_url(ws)
    page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
    screenshot(ws, 'kaggle_account')
    print(f"  Account URL: {url}")
    print(f"  Account text: {(page_text or '')[:200]}")
    
    if 'login' in str(url).lower() and 'account' not in str(url).lower().replace('login', ''):
        results['kaggle'] = 'FAILED - redirected to login'
    else:
        results['kaggle'] = 'SUCCESS - signed in'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    results['kaggle'] = f'ERROR - {e}'

# ============ REPLICATE ============
print("\n=== REPLICATE ===")
try:
    ws_url = get_main_page_ws()
    ws = websocket.create_connection(ws_url, timeout=10)
    send_cmd(ws, 'Page.enable')
    
    navigate(ws, 'https://replicate.com/signin')
    time.sleep(5)
    screenshot(ws, 'replicate_login_page')
    
    result = evaluate(ws, """(function() {
        let els = document.querySelectorAll('a, button, [role="button"]');
        let items = [];
        for (let el of els) {
            let t = el.textContent.trim();
            if (t.length > 0 && t.length < 100) {
                items.push(t);
            }
        }
        return JSON.stringify(items.slice(0, 20));
    })()""")
    print(f"  Page buttons: {result}")
    
    # Replicate typically uses GitHub, but may have Google
    clicked = click_google_oauth(ws, 'replicate')
    time.sleep(5)
    
    if not clicked:
        print("  No Google OAuth found on Replicate, trying GitHub or other...")
        # Replicate primarily uses GitHub - check what's available
        result = evaluate(ws, """(function() {
            let els = document.querySelectorAll('a, button');
            let items = [];
            for (let el of els) {
                items.push({text: el.textContent.trim().substring(0, 60), href: el.href || ''});
            }
            return JSON.stringify(items.slice(0, 30));
        })()""")
        print(f"  All buttons: {result}")
        screenshot(ws, 'replicate_buttons')
        results['replicate'] = 'FAILED - Google OAuth not available (GitHub only)'
    else:
        screenshot(ws, 'replicate_after_click')
        url = get_url(ws)
        print(f"  Current URL: {url}")
        
        handle_google_account_chooser(ws)
        time.sleep(3)
        
        url = get_url(ws)
        print(f"  URL after auth: {url}")
        screenshot(ws, 'replicate_after_auth')
        
        page_text = evaluate(ws, 'document.body?.innerText?.substring(0, 500)')
        print(f"  Page text: {(page_text or '')[:200]}")
        
        if 'signin' in str(url).lower() or 'login' in str(url).lower():
            results['replicate'] = 'FAILED - still on login page'
        else:
            results['replicate'] = 'SUCCESS - signed in'
    
    ws.close()
except Exception as e:
    print(f"  ERROR: {e}")
    import traceback; traceback.print_exc()
    results['replicate'] = f'ERROR - {e}'

# Write results
print("\n=== RESULTS ===")
for k, v in results.items():
    print(f"  {k}: {v}")

md = f"""# Striker - OAuth Account Status

| Service | Status | Account |
|---------|--------|---------|
| HuggingFace | {results.get('huggingface', 'UNKNOWN')} | novacline602@gmail.com |
| Kaggle | {results.get('kaggle', 'UNKNOWN')} | novacline602@gmail.com |
| Replicate | {results.get('replicate', 'UNKNOWN')} | novacline602@gmail.com |

Updated: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}
"""

with open('/home/x/striker/accounts.md', 'w') as f:
    f.write(md)

print("\nResults written to ~/striker/accounts.md")
