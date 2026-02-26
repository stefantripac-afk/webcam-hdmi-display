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

# Configure boot config for low-resolution HDMI output
BOOT_CONFIG=""
for cfg in /boot/firmware/config.txt /boot/config.txt; do
    if [ -f "$cfg" ]; then
        BOOT_CONFIG="$cfg"
        break
    fi
done

if [ -n "$BOOT_CONFIG" ]; then
    echo "Configuring HDMI output in ${BOOT_CONFIG}..."
    NEEDS_REBOOT=0

    apply_setting() {
        local key="$1" value="$2"
        if grep -q "^${key}=" "$BOOT_CONFIG"; then
            if ! grep -q "^${key}=${value}$" "$BOOT_CONFIG"; then
                sed -i "s/^${key}=.*/${key}=${value}/" "$BOOT_CONFIG"
                NEEDS_REBOOT=1
            fi
        elif grep -q "^#\s*${key}=" "$BOOT_CONFIG"; then
            sed -i "s/^#\s*${key}=.*/${key}=${value}/" "$BOOT_CONFIG"
            NEEDS_REBOOT=1
        else
            echo "${key}=${value}" >> "$BOOT_CONFIG"
            NEEDS_REBOOT=1
        fi
    }

    apply_setting hdmi_force_hotplug 1
    apply_setting hdmi_group 2
    apply_setting hdmi_mode 87
    apply_setting hdmi_cvt "480 320 30"
    apply_setting framebuffer_width 480
    apply_setting framebuffer_height 320
else
    echo "WARNING: Could not find /boot/config.txt or /boot/firmware/config.txt"
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

if [ "${NEEDS_REBOOT:-0}" -eq 1 ]; then
    echo ""
    echo "*** HDMI settings were changed in ${BOOT_CONFIG}. A reboot is required. ***"
    read -rp "Reboot now? [y/N] " answer
    if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
        reboot
    fi
fi
