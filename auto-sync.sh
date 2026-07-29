#!/bin/bash
# Auto-commit & push MASKAI changes to GitHub
cd /home/ubuntu/maskai || exit 1

# Use git credential from existing remote
if ! git remote -v 2>/dev/null | grep -q origin; then
    git remote add origin git@github.com:andiwahyu27/maskai.git
fi

if [[ -z "$(git status --porcelain)" ]]; then
    exit 0
fi

git add bot.py schema.sql docker-compose.yml .gitignore .env.example
git commit -m "auto-sync: $(date '+%Y-%m-%d %H:%M')"
git push origin main 2>&1
