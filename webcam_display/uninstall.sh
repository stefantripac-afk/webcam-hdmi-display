#!/bin/bash
# Uninstall webcam-display systemd service from Raspberry Pi OS.
# Run as: sudo bash uninstall.sh

set -e

SERVICE_NAME="webcam-display"
APP_DIR="/home/pi/webcam_display"

echo "Stopping and disabling service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

echo "Removing systemd unit..."
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

echo "Removing application files..."
rm -rf "$APP_DIR"

echo "Done. ${SERVICE_NAME} has been uninstalled."
