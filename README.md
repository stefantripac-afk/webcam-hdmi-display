# webcam-hdmi-display

Capture video from a Logitech C270 HD webcam and display it fullscreen on the HDMI output of a Raspberry Pi Zero W. Writes directly to the Linux framebuffer (`/dev/fb0`) — no X11 or desktop environment required.

## Hardware

- Raspberry Pi Zero W
- Logitech C270 HD webcam (connected via micro-USB OTG adapter)
- HDMI display (connected via mini-HDMI to HDMI adapter)
- Raspberry Pi OS Lite (no desktop needed)

## Prerequisites

```bash
sudo apt update
sudo apt install -y python3-opencv
```

No pip packages required — uses only stdlib + OpenCV.

## Usage

```bash
cd webcam_display
python3 main.py
```

Press **Ctrl+C** to stop.

### CLI options

```
python3 main.py -d 1        # use /dev/video1
python3 main.py -f /dev/fb1 # use alternate framebuffer
```

## Configuration

Edit `config.py` to change:

| Setting | Default | Description |
|---------|---------|-------------|
| `DEVICE_INDEX` | `0` | Video device index (`/dev/video0`) |
| `CAPTURE_WIDTH` | `640` | Capture width in pixels |
| `CAPTURE_HEIGHT` | `480` | Capture height in pixels |
| `USE_MJPEG` | `True` | Use MJPEG codec (hardware-decoded by C270) |
| `BUFFER_SIZE` | `1` | Frame buffer size (lower = less latency) |
| `TARGET_FPS` | `15` | Target frame rate |
| `FB_DEVICE` | `/dev/fb0` | Framebuffer device path |

## Architecture

```
Logitech C270 --> /dev/video0 --> OpenCV (V4L2+MJPEG) --> resize --> /dev/fb0 (HDMI)
```

- **capture.py** — `WebcamCapture` class wrapping OpenCV `VideoCapture` with V4L2 backend
- **display.py** — `FramebufferDisplay` class using `mmap` + `ioctl` to write directly to `/dev/fb0`
- **main.py** — Main loop with FPS throttling and signal handling
- **config.py** — All settings in one place

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
journalctl -u webcam-display -f
```

## Uninstall

```bash
sudo bash uninstall.sh
```
