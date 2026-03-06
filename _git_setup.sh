#!/usr/bin/env bash
set -e
cd /home/pixl/Dev/AppartClaude

echo "=== GIT STATUS ==="
git status 2>&1 || true

echo ""
echo "=== GIT LOG (last 5) ==="
git log --oneline -5 2>&1 || echo "(no commits yet)"

echo ""
echo "=== REMOTE ==="
git remote -v 2>&1 || echo "(no remote)"

# Keep the process alive so preview_logs can read it
sleep 5
