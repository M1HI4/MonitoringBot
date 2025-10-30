import json
import os
import requests
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# === Конфигурация ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

BOT_TOKEN = CONFIG["BOT_TOKEN"]
PROMETHEUS_URL = CONFIG["PROMETHEUS_URL"]
ADMIN_CHAT_ID = CONFIG["ADMIN_CHAT_ID"]

SUBSCR_FILE = os.path.join(BASE_DIR, "subscribers.json")

def load_subscribers():
    try:
        with open(SUBSCR_FILE) as f:
            return json.load(f)
    except:
        return []

def save_subscribers(lst):
    with open(SUBSCR_FILE, "w") as f:
        json.dump(lst, f)

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=payload, timeout=5)

def prom_query(query):
    url = f"{PROMETHEUS_URL}/api/v1/query"
    r = requests.get(url, params={"query": query}, timeout=10)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data["data"]["result"]:
        return None
    return float(data["data"]["result"][0]["value"][1])

def build_status_text():
    metrics = {
        "CPU": '100 - (avg by (instance)(irate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
        "Memory": '(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
        "Disk": '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100',
        "Temperature": 'node_hwmon_temp_celsius'
    }

    lines = [f"*System Status — {datetime.utcnow().isoformat()} UTC*"]
    for name, query in metrics.items():
        val = prom_query(query)
        if val is not None:
            lines.append(f"{name}: `{val:.1f}`%")
        else:
            lines.append(f"{name}: `N/A`")
    return "\n".join(lines)

@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    msg = data.get("message", {})
    chat_id = msg["chat"]["id"]
    text = msg.get("text", "")

    if text.startswith("/status"):
        send_telegram(chat_id, build_status_text())
    elif text.startswith("/start"):
        subs = load_subscribers()
        if chat_id not in subs:
            subs.append(chat_id)
            save_subscribers(subs)
        send_telegram(chat_id, "Подписка активирована.")
    elif text.startswith("/stop"):
        subs = load_subscribers()
        if chat_id in subs:
            subs.remove(chat_id)
            save_subscribers(subs)
        send_telegram(chat_id, "Подписка отменена.")
    else:
        send_telegram(chat_id, "Доступные команды: /status, /start, /stop")

    return jsonify({"ok": True})

@app.route("/", methods=["GET"])
def index():
    return "Monitoring bot is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
