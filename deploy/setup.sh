#!/usr/bin/env bash
# One-time bootstrap for running the Survival Agent 24/7 on a fresh Ubuntu VM
# (e.g. an Oracle Cloud Always Free instance). Idempotent — safe to re-run.
#
# Usage: ./setup.sh <git-repo-url>
set -euo pipefail

REPO_URL="${1:?Usage: setup.sh <git-repo-url>}"
APP_DIR="$HOME/survival-agent"
SERVICE_NAME="survival-agent"

echo "==> Installing system dependencies"
sudo apt-get update -y
sudo apt-get install -y python3-venv python3-pip git

echo "==> Fetching $REPO_URL into $APP_DIR"
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull
else
  git clone "$REPO_URL" "$APP_DIR"
fi

cd "$APP_DIR"

echo "==> Creating virtualenv and installing Python dependencies"
python3 -m venv agent/venv
agent/venv/bin/pip install --upgrade pip
agent/venv/bin/pip install -r agent/requirements.txt

if [ ! -f .env ]; then
  echo "==> No .env found — copying .env.example. YOU MUST edit it with real keys before starting."
  cp .env.example .env
fi

mkdir -p state logs

echo "==> Installing systemd service ($SERVICE_NAME)"
sed \
  -e "s#__USER__#$(whoami)#g" \
  -e "s#__APP_DIR__#$APP_DIR#g" \
  deploy/survival-agent.service | sudo tee "/etc/systemd/system/${SERVICE_NAME}.service" > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"

cat <<EOF

==> Setup complete. Before starting the agent:
    1. Edit $APP_DIR/.env with your real API keys (at minimum: an LLM key + GITHUB_TOKEN/GITHUB_REPO)
    2. sudo systemctl start $SERVICE_NAME
    3. journalctl -u $SERVICE_NAME -f      # watch it run
    4. systemctl status $SERVICE_NAME      # check it's alive / see why it died
EOF
