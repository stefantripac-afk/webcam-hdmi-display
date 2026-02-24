"""Auto-create / enable the Linux framebuffer device if it is missing."""

import os
import subprocess
import time

# Modules to try, in order of likelihood on Raspberry Pi
_FB_MODULES = ("bcm2708_fb", "vc4", "drm_fbdev_generic")

# Possible locations for config.txt (Bullseye vs Bookworm)
_BOOT_CONFIGS = ("/boot/config.txt", "/boot/firmware/config.txt")


def _device_exists(fb_device):
    return os.path.exists(fb_device)


def _try_modprobe(module, fb_device, timeout=2.0):
    """Load *module* via modprobe and wait up to *timeout* seconds for the device."""
    try:
        subprocess.run(
            ["sudo", "modprobe", module],
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return False

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _device_exists(fb_device):
            return True
        time.sleep(0.2)
    return False


def _check_boot_config():
    """Return diagnostic hints based on /boot/config.txt contents."""
    for path in _BOOT_CONFIGS:
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as f:
                text = f.read()
        except PermissionError:
            continue

        has_overlay = ("dtoverlay=vc4-kms-v3d" in text or
                       "dtoverlay=vc4-fkms-v3d" in text)
        if has_overlay:
            return (
                f"Found a vc4 overlay in {path}, but the framebuffer device "
                "still did not appear. A reboot may be required."
            )
        return (
            f"No vc4 overlay found in {path}. Add one of the following "
            "lines and reboot:\n"
            "  dtoverlay=vc4-kms-v3d\n"
            "  dtoverlay=vc4-fkms-v3d"
        )
    return "Could not locate /boot/config.txt to check for display overlays."


def ensure_framebuffer(fb_device="/dev/fb0"):
    """Make sure *fb_device* exists, attempting modprobe if it does not.

    Raises ``RuntimeError`` with actionable diagnostics on failure.
    """
    if _device_exists(fb_device):
        return

    print(f"{fb_device} not found — attempting to load framebuffer modules...")

    for module in _FB_MODULES:
        print(f"  Trying modprobe {module} ...")
        if _try_modprobe(module, fb_device):
            print(f"  {fb_device} appeared after loading {module}.")
            return

    hint = _check_boot_config()
    raise RuntimeError(
        f"Framebuffer device {fb_device} could not be created.\n"
        f"Tried modprobe for: {', '.join(_FB_MODULES)}\n\n"
        f"{hint}"
    )
