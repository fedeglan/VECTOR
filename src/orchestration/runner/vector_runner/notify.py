"""Optional one-way Telegram ping (POLICY §12). No-op unless configured:
TELEGRAM_BOT_TOKEN in the environment AND notification.recipients non-empty.
Failures are swallowed — notification is never allowed to break the loop.
"""
import json
import os
import urllib.request


def send(policy, event, text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    conf = policy.get("notification", {}) or {}
    recipients = conf.get("recipients") or []
    events = conf.get("events") or []
    if not token or not recipients or (events and event not in events):
        return False
    ok = True
    for chat in recipients if isinstance(recipients, list) else [recipients]:
        try:
            data = json.dumps({"chat_id": chat, "text": text[:3900]}).encode()
            req = urllib.request.Request(
                f"https://api.telegram.org/bot{token}/sendMessage",
                data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
        except Exception:
            ok = False  # one-way, best-effort; the loop never depends on this
    return ok
