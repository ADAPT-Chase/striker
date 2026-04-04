#!/usr/bin/env python3
import json, os, sys, subprocess

PROMPT = sys.argv[1] if len(sys.argv) > 1 else "Say hi in five words."
TASK = sys.argv[2] if len(sys.argv) > 2 else "general"

def load_exported_key(name):
    val = os.getenv(name)
    if val:
        return val
    for path in [os.path.expanduser('~/.bashrc'), os.path.expanduser('~/.hermes/.env')]:
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f'export {name}='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
                    if line.startswith(f'{name}='):
                        return line.split('=', 1)[1].strip().strip('"').strip("'")
        except FileNotFoundError:
            pass
    return None

OPENROUTER_KEY = load_exported_key("OPENROUTER_API_KEY")
GROQ_KEY = load_exported_key("GROQ_API_KEY")
CEREBRAS_KEY = load_exported_key("CEREBRAS_API_KEY")

PROVIDERS = {
    "fast": [
        ("groq", "llama-3.1-8b-instant"),
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "llama3.1-8b"),
    ],
    "reasoning": [
        ("cerebras", "gpt-oss-120b"),
        ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "long": [
        ("openrouter", "qwen/qwen3.6-plus:free"),
        ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
        ("cerebras", "gpt-oss-120b"),
    ],
    "code": [
        ("openrouter", "qwen/qwen3-coder:free"),
        ("cerebras", "gpt-oss-120b"),
        ("groq", "llama-3.3-70b-versatile"),
    ],
    "general": [
        ("openrouter", "nvidia/nemotron-3-super-120b-a12b:free"),
        ("groq", "llama-3.3-70b-versatile"),
        ("cerebras", "gpt-oss-120b"),
    ],
}

def post_json(url, payload, headers):
    cmd = ["curl", "-s", url]
    for k, v in headers.items():
        cmd += ["-H", f"{k}: {v}"]
    cmd += ["-d", json.dumps(payload)]
    out = subprocess.check_output(cmd, timeout=45).decode()
    data = json.loads(out)
    if "error" in data:
        raise RuntimeError(str(data["error"]))
    return data

def try_openrouter(model, prompt):
    if not OPENROUTER_KEY:
        raise RuntimeError("missing OPENROUTER_API_KEY")
    return post_json(
        "https://openrouter.ai/api/v1/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 600},
        {"Authorization": f"Bearer {OPENROUTER_KEY}", "Content-Type": "application/json"},
    )["choices"][0]["message"]["content"].strip()

def try_groq(model, prompt):
    if not GROQ_KEY:
        raise RuntimeError("missing GROQ_API_KEY")
    return post_json(
        "https://api.groq.com/openai/v1/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 600},
        {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
    )["choices"][0]["message"]["content"].strip()

def try_cerebras(model, prompt):
    if not CEREBRAS_KEY:
        raise RuntimeError("missing CEREBRAS_API_KEY")
    return post_json(
        "https://api.cerebras.ai/v1/chat/completions",
        {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 600},
        {"Authorization": f"Bearer {CEREBRAS_KEY}", "Content-Type": "application/json"},
    )["choices"][0]["message"]["content"].strip()

handlers = {"openrouter": try_openrouter, "groq": try_groq, "cerebras": try_cerebras}

tried = []
for provider, model in PROVIDERS.get(TASK, PROVIDERS["general"]):
    try:
        out = handlers[provider](model, PROMPT)
        print(json.dumps({"ok": True, "provider": provider, "model": model, "output": out}, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:
        tried.append({"provider": provider, "model": model, "error": str(e)[:300]})

print(json.dumps({"ok": False, "task": TASK, "tried": tried}, ensure_ascii=False))
sys.exit(1)
