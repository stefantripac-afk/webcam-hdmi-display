# webcam-hdmi-display

Capture video from a Logitech C270 HD webcam and display it fullscreen on the HDMI output of a Raspberry Pi Zero W.

## Hardware

- Raspberry Pi Zero W
- Logitech C270 HD webcam (connected via micro-USB OTG adapter)
- HDMI display (connected via mini-HDMI to HDMI adapter)
- Raspberry Pi OS (Desktop)

## Prerequisites

```bash
sudo apt update
sudo apt install -y python3-opencv
```

## Usage

```bash
cd webcam_display
python3 main.py
```

Press **ESC** to quit.

## Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEVICE_INDEX` | `0` | Video device index (`/dev/video0`) |
| `CAPTURE_WIDTH` | `640` | Capture width in pixels |
| `CAPTURE_HEIGHT` | `480` | Capture height in pixels |
| `USE_MJPEG` | `True` | Use MJPEG codec for better performance |
| `BUFFER_SIZE` | `1` | Frame buffer size (lower = less latency) |

## Install as a systemd service

Auto-start on boot:

```bash
sudo bash install.sh
```

Manage the service:

```bash
sudo systemctl stop webcam-display
sudo systemctl start webcam-display
sudo systemctl status webcam-display
sudo journalctl -u webcam-display -f
```

## Uninstall

```bash
sudo bash uninstall.sh
```
