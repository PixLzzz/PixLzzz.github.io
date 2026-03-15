#!/usr/bin/env python3
"""Commit and push Rosemont changes. Serve result on :19999."""
import http.server, json, subprocess, threading

ROOT = "/home/pixl/Dev/AppartClaude"
OUTPUT = {"done": False}

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).strip()

def work():
    OUTPUT["stash"]  = run("git stash 2>&1")
    OUTPUT["pull"]   = run("git pull --rebase 2>&1")
    OUTPUT["pop"]    = run("git stash pop 2>&1")
    OUTPUT["add"]    = run("git add config.py scrapers/centris.py scrapers/duproprio.py frontend/src/components/Header.jsx")
    OUTPUT["diff"]   = run("git diff --cached --stat")
    OUTPUT["commit"] = run('git commit -m "feat: add Rosemont & Beaubien neighborhoods to scrapers" || true')
    OUTPUT["push"]   = run("git push 2>&1")
    OUTPUT["log"]    = run("git log --oneline -3")
    OUTPUT["done"]   = True

threading.Thread(target=work, daemon=True).start()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(OUTPUT, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

print("Push helper on :19999", flush=True)
http.server.HTTPServer(("0.0.0.0", 19999), Handler).serve_forever()
