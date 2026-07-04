#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/review-analyzer"
REPO_URL="https://github.com/Sayan-Adhikary-23/review-analyzer.git"
SERVICE_NAME="review-analyzer"

echo "==> Installing system packages"
if command -v yum &>/dev/null; then
  sudo yum update -y
  sudo yum install -y python3 python3-pip git
elif command -v apt-get &>/dev/null; then
  sudo apt-get update -y
  sudo apt-get install -y python3 python3-pip python3-venv git
fi

echo "==> Cloning or updating repository"
if [ -d "$APP_DIR/.git" ]; then
  cd "$APP_DIR"
  git pull origin main
else
  sudo mkdir -p "$APP_DIR"
  sudo chown "$(whoami):$(whoami)" "$APP_DIR"
  git clone "$REPO_URL" "$APP_DIR"
  cd "$APP_DIR"
fi

echo "==> Ensuring swap space for low-memory instances"
if [ "$(swapon --show | wc -l)" -eq 0 ]; then
  sudo fallocate -l 2G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=2048
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi

echo "==> Setting up Python virtual environment"
cd "$APP_DIR/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install --no-cache-dir -r requirements-ec2.txt

if [ ! -f .env ]; then
  echo "==> Creating .env from example — set OPENAI_API_KEY before use"
  cp .env.example .env
fi

echo "==> Running ingestion (if ChromaDB empty)"
DOC_COUNT=$(python -c "
from app.config import get_settings
from app.db.chroma_client import ChromaReviewStore
print(ChromaReviewStore(get_settings()).get_document_count())
" 2>/dev/null || echo "0")

if [ "$DOC_COUNT" = "0" ]; then
  python scripts/run_ingestion.py --all || echo "Ingestion failed — run manually later"
fi

echo "==> Installing systemd service"
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Review Discovery Engine
After=network.target

[Service]
Type=simple
User=$(whoami)
WorkingDirectory=${APP_DIR}/backend
Environment=PATH=${APP_DIR}/backend/.venv/bin
ExecStart=${APP_DIR}/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}

echo "==> Deployment complete"
sudo systemctl status ${SERVICE_NAME} --no-pager
echo "App available at http://$(curl -s http://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}'):8000"
