#!/usr/bin/env python3
"""Temporary helper: initializes git, stages files, commits, and serves the result on port 19999."""
import http.server, json, os, subprocess, threading
from pathlib import Path

ROOT = "/home/pixl/Dev/AppartClaude"
OUTPUT = {}

def run(cmd, **kw):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=ROOT, **kw)
    return (r.stdout + r.stderr).strip()

def do_git():
    steps = {}

    # Init if needed
    steps["init"] = run("git init")

    # Config (needed for commits in some environments)
    run('git config user.email "appartclaude@local" || true')
    run('git config user.name "AppartClaude" || true')

    # Status before
    steps["status_before"] = run("git status")

    # Stage everything except what .gitignore covers
    steps["add"] = run("git add "
        "frontend/src "
        "frontend/public/index.html "
        "frontend/index.html "
        "frontend/vite.config.js "
        "frontend/package.json "
        "main.py requirements.txt "
        "export_data.py "
        ".gitignore "
        ".github "
        ".claude/launch.json "
        "|| true")

    steps["status_after"] = run("git status")

    # Commit
    steps["commit"] = run(
        'git commit -m "Fix map, add filters, GitHub Pages deployment support" '
        '--allow-empty-message || true'
    )

    steps["log"] = run("git log --oneline -5")
    steps["remote"] = run("git remote -v")

    OUTPUT.update(steps)

threading.Thread(target=do_git, daemon=True).start()

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps(OUTPUT, indent=2).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a): pass

print("Git helper running on :19999", flush=True)
http.server.HTTPServer(("0.0.0.0", 19999), Handler).serve_forever()
