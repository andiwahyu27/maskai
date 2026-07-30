#!/bin/bash
# MASKAI Telegram Poller - polling Telegram and sending to n8n webhook
BOT_TOKEN="8984371648:AAHXnXIX0M9FLHbauRNmKYLYcbBx8XBebrg"
OFFSET_FILE="/tmp/maskai-offset.txt"
N8N_WEBHOOK="http://localhost:5678/webhook/maskai-bot"

# Read last offset
OFFSET=$(cat "$OFFSET_FILE" 2>/dev/null || echo "0")

# Get updates from Telegram
UPDATES=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates?offset=${OFFSET}&timeout=10")

# Check if there are updates
RESULT=$(echo "$UPDATES" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    updates = data.get('result', [])
    if not updates:
        print('EMPTY')
        sys.exit(0)
    max_id = max(u['update_id'] for u in updates)
    print(f'COUNT:{len(updates)} MAXID:{max_id}')
    # Forward each update to n8n
    for u in updates:
        payload = json.dumps(u)
        import urllib.request
        req = urllib.request.Request('$N8N_WEBHOOK', data=payload.encode(), headers={'Content-Type':'application/json'})
        try:
            urllib.request.urlopen(req, timeout=5)
        except:
            pass
except Exception as e:
    print(f'ERROR:{e}')
")

if [[ "$RESULT" == EMPTY ]]; then
    exit 0
fi

echo "$RESULT"
# Save offset
if [[ "$RESULT" =~ MAXID:([0-9]+) ]]; then
    echo "${BASH_REMATCH[1]}" > "$OFFSET_FILE"
fi
