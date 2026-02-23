#!/bin/bash
# Install webcam-display as a systemd service on Raspberry Pi OS.
# Run as: sudo bash install.sh

set -e

SERVICE_NAME="webcam-display"
SERVICE_FILE="$(dirname "$0")/${SERVICE_NAME}.service"
APP_DIR="/home/pi/webcam_display"
SYSTEMD_DIR="/etc/systemd/system"

# Copy application files
echo "Copying application to ${APP_DIR}..."
mkdir -p "$APP_DIR"
cp "$(dirname "$0")/main.py" "$APP_DIR/"
cp "$(dirname "$0")/config.py" "$APP_DIR/"

# Install systemd unit
echo "Installing systemd service..."
cp "$SERVICE_FILE" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "Done. Service status:"
systemctl status "$SERVICE_NAME" --no-pager
