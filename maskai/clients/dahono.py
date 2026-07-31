"""Dahono AI client"""
import logging, requests
log = logging.getLogger("maskai.dahono")
def claude(messages, max_tokens=500):
    """Claude via Dahono — safe JSON/HTTP handling"""
    try:
        r = requests.post(f"{DAHONO_URL}/chat/completions",
            json={"model": "dahono/claude-sonnet-4.5-free", "messages": messages, "max_tokens": max_tokens},
            headers={"Authorization": f"Bearer {DAHONO_KEY}", "Content-Type": "application/json"}, timeout=config.HTTP_TIMEOUT_LONG)
        if r.status_code != 200 or not r.text:
            log.warning(f"Claude HTTP {r.status_code}: {r.text[:100]}")
            return None
        body = r.json()
        return body["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, requests.Timeout, requests.ConnectionError, requests.RequestException) as e:
        log.error(f"Claude error: {e}")
        return None
