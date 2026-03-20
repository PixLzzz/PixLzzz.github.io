#!/usr/bin/env python3
"""Commit and push changes. Serve result on :19999."""
import http.server, json, subprocess, threading

ROOT = "/home/pixl/Dev/AppartClaude"
OUTPUT = {"done": False}

def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT)
    return (r.stdout + r.stderr).strip()

def work():
    OUTPUT["stash"]  = run("git stash 2>&1")
    OUTPUT["pull"]   = run("git pull --rebase 2>&1")
    OUTPUT["pop"]    = run("git stash pop 2>&1 || echo 'nothing to pop'")
    OUTPUT["add"]    = run("git add scrape_and_export.py scrapers/centris.py frontend/src/App.jsx .github/workflows/scrape.yml")
    OUTPUT["diff"]   = run("git diff --cached --stat")
    OUTPUT["commit"] = run("""git commit -m "fix: stable first_seen, better stats, cleaner addresses

- Stale listings marked inactive instead of deleted (preserves first_seen)
- Inactive listings permanently removed after 3 days
- state.json tracks full history including inactive listings
- Stats computed from all listings before source filtering
- Centris addresses: strip tab characters
- Workflow commits state.json alongside data.json

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" 2>&1""")
    OUTPUT["push"]   = run("git push 2>&1")
    OUTPUT["log"]    = run("git log --oneline -5")
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
