#!/bin/bash

# === Настройки ===
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROM_DIR="$PROJECT_ROOT/prometheus"
NODE_DIR="$PROJECT_ROOT/node_exporter"
BOT_DIR="$PROJECT_ROOT/bot"

# === Проверка Docker ===
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установи Docker и повтори попытку."
    exit 1
fi

# === 1. Остановка старых контейнеров ===
echo "🧹 Останавливаю старые контейнеры..."
docker stop prometheus node_exporter 2>/dev/null || true
docker rm prometheus node_exporter 2>/dev/null || true

# === 2. Сборка и запуск Prometheus ===
echo "🚀 Запускаю Prometheus..."
docker build -t custom-prometheus "$PROM_DIR"
docker run -d --name prometheus -p 9090:9090 \
  -v "$PROM_DIR/prometheus.yml:/etc/prometheus/prometheus.yml" \
  -v "$PROM_DIR/rules:/etc/prometheus/rules" \
  custom-prometheus

# === 3. Сборка и запуск Node Exporter ===
echo "🚀 Запускаю Node Exporter..."
docker build -t custom-node-exporter "$NODE_DIR"
docker run -d --name node_exporter -p 9100:9100 custom-node-exporter

# === 4. Проверка Grafana ===
echo "🔍 Проверяю доступность Grafana на http://10.11.1.5:9091 ..."
if curl -s --head --request GET "http://10.11.1.5:9091" | grep "200 OK" > /dev/null; then
  echo "✅ Grafana работает!"
else
  echo "⚠️  Grafana недоступна. Убедись, что она запущена на 10.11.1.5:9091"
fi

# === 5. Запуск Telegram-бота ===
echo "🤖 Запускаю Telegram-бота..."
cd "$BOT_DIR" || exit 1

# Проверка зависимостей
if [ ! -d "venv" ]; then
    echo "📦 Создаю виртуальное окружение..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

# Запуск бота
python3 bot.py &
BOT_PID=$!

echo "✅ Telegram-бот запущен (PID: $BOT_PID)"
echo "🔗 Prometheus: http://localhost:9090"
echo "🔗 Grafana:    http://10.11.1.5:9091"
echo "📊 Node Exporter: http://localhost:9100/metrics"
