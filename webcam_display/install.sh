#!/bin/bash
# Install webcam-display as a systemd service on Raspberry Pi OS.
# Run as: sudo bash install.sh

set -e

SERVICE_NAME="webcam-display"
APP_DIR="/home/pi/webcam_display"
SYSTEMD_DIR="/etc/systemd/system"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Copy application files
echo "Copying application to ${APP_DIR}..."
mkdir -p "$APP_DIR"
cp "$SCRIPT_DIR/main.py" "$APP_DIR/"
cp "$SCRIPT_DIR/config.py" "$APP_DIR/"
cp "$SCRIPT_DIR/capture.py" "$APP_DIR/"
cp "$SCRIPT_DIR/display.py" "$APP_DIR/"
cp "$SCRIPT_DIR/framebuffer_setup.py" "$APP_DIR/"

# Quick framebuffer sanity check
if [ ! -e /dev/fb0 ]; then
    echo "WARNING: /dev/fb0 not found. The app will attempt to load it at runtime."
    echo "If that fails, ensure a vc4 overlay is enabled in /boot/config.txt and reboot."
fi

# Create systemd unit
echo "Creating systemd service..."
cat > "${SYSTEMD_DIR}/${SERVICE_NAME}.service" <<EOF
[Unit]
Description=Webcam to HDMI Display
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 ${APP_DIR}/main.py
WorkingDirectory=${APP_DIR}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SupplementaryGroups=video

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo "Done. Service status:"
systemctl status "$SERVICE_NAME" --no-pager
