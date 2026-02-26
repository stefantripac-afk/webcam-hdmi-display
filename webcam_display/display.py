"""Framebuffer display via mmap — no X11 required."""

import ctypes
import fcntl
import mmap
import os
import struct

import cv2
import numpy as np

from framebuffer_setup import ensure_framebuffer

# Linux framebuffer ioctl constants
FBIOGET_VSCREENINFO = 0x4600
FBIOGET_FSCREENINFO = 0x4602

# line_length offset in fb_fix_screeninfo depends on sizeof(unsigned long):
#   32-bit: id(16) + smem_start(4) + smem_len(4) + type(4) + type_aux(4)
#           + visual(4) + xpanstep(2) + ypanstep(2) + ywrapstep(2) + pad(2)
#           = offset 44
#   64-bit: id(16) + smem_start(8) + smem_len(4) + type(4) + type_aux(4)
#           + visual(4) + xpanstep(2) + ypanstep(2) + ywrapstep(2) + pad(2)
#           = offset 48
_ULONG_SIZE = ctypes.sizeof(ctypes.c_ulong)
_LINE_LENGTH_OFFSET = 44 if _ULONG_SIZE == 4 else 48


def _parse_vscreeninfo(buf):
    """Extract fields from fb_var_screeninfo (first 40 bytes are enough)."""
    fields = struct.unpack_from("8I", buf, 0)
    return {
        "xres": fields[0],
        "yres": fields[1],
        "xres_virtual": fields[2],
        "yres_virtual": fields[3],
        "xoffset": fields[4],
        "yoffset": fields[5],
        "bits_per_pixel": fields[6],
    }


def _read_sysfs_int(path):
    """Read an integer from a sysfs file, or return None."""
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def _read_sysfs_fb_info(fb_device):
    """Try to read framebuffer info from sysfs as a fallback."""
    fb_name = os.path.basename(fb_device)  # e.g. "fb0"
    sysfs = f"/sys/class/graphics/{fb_name}"
    info = {}

    vsize = None
    try:
        with open(f"{sysfs}/virtual_size") as f:
            parts = f.read().strip().split(",")
            if len(parts) == 2:
                info["xres"] = int(parts[0])
                info["yres"] = int(parts[1])
    except (OSError, ValueError):
        pass

    bpp = _read_sysfs_int(f"{sysfs}/bits_per_pixel")
    if bpp is not None:
        info["bits_per_pixel"] = bpp

    stride = _read_sysfs_int(f"{sysfs}/stride")
    if stride is not None:
        info["line_length"] = stride

    return info


def _parse_fscreeninfo(buf):
    """Extract line_length from fb_fix_screeninfo."""
    line_length = struct.unpack_from("I", buf, _LINE_LENGTH_OFFSET)[0]
    return {"line_length": line_length}


class FramebufferDisplay:
    """Writes frames directly to the Linux framebuffer (/dev/fb0)."""

    def __init__(self, fb_device="/dev/fb0"):
        self.fb_device = fb_device
        self.fd = None
        self.fbmap = None
        self.xres = 0
        self.yres = 0
        self.bpp = 0
        self.line_length = 0

    def open(self):
        ensure_framebuffer(self.fb_device)
        self.fd = os.open(self.fb_device, os.O_RDWR)

        # Read variable screen info
        vinfo_buf = bytearray(160)
        fcntl.ioctl(self.fd, FBIOGET_VSCREENINFO, vinfo_buf)
        vinfo = _parse_vscreeninfo(vinfo_buf)
        self.xres = vinfo["xres"]
        self.yres = vinfo["yres"]
        self.bpp = vinfo["bits_per_pixel"]

        # Read fixed screen info (buffer must be large enough for 64-bit)
        finfo_buf = bytearray(80)
        fcntl.ioctl(self.fd, FBIOGET_FSCREENINFO, finfo_buf)
        finfo = _parse_fscreeninfo(finfo_buf)
        self.line_length = finfo["line_length"]

        print(f"ioctl values: xres={self.xres} yres={self.yres} "
              f"bpp={self.bpp} line_length={self.line_length} "
              f"(ulong_size={_ULONG_SIZE}, ll_offset={_LINE_LENGTH_OFFSET})")

        # If ioctl returned zeros, try sysfs as fallback
        if self.xres == 0 or self.yres == 0 or self.line_length == 0:
            print("ioctl returned zero values, trying sysfs fallback...")
            sysfs = _read_sysfs_fb_info(self.fb_device)
            if sysfs:
                print(f"sysfs values: {sysfs}")
            if self.xres == 0 and "xres" in sysfs:
                self.xres = sysfs["xres"]
            if self.yres == 0 and "yres" in sysfs:
                self.yres = sysfs["yres"]
            if self.bpp == 0 and "bits_per_pixel" in sysfs:
                self.bpp = sysfs["bits_per_pixel"]
            if self.line_length == 0 and "line_length" in sysfs:
                self.line_length = sysfs["line_length"]

        # If line_length is still 0 but we have xres and bpp, compute it
        if self.line_length == 0 and self.xres > 0 and self.bpp > 0:
            self.line_length = self.xres * (self.bpp // 8)
            print(f"Computed line_length={self.line_length} from xres*bpp/8")

        fb_size = self.line_length * self.yres
        if fb_size == 0:
            os.close(self.fd)
            self.fd = None
            raise RuntimeError(
                f"Framebuffer size is 0 (xres={self.xres}, yres={self.yres}, "
                f"bpp={self.bpp}, line_length={self.line_length}).\n"
                "The display may not be connected or HDMI output is not active.\n"
                "Try:\n"
                "  1. Check HDMI cable is connected before boot\n"
                "  2. Add 'hdmi_force_hotplug=1' to /boot/config.txt and reboot\n"
                "  3. Set a resolution: 'hdmi_group=2' and 'hdmi_mode=87' "
                "with 'hdmi_cvt=800 480 60' in /boot/config.txt"
            )

        print(f"Framebuffer: {self.xres}x{self.yres} {self.bpp}bpp, "
              f"line_length={self.line_length}, size={fb_size}")
        self.fbmap = mmap.mmap(self.fd, fb_size,
                               mmap.MAP_SHARED,
                               mmap.PROT_WRITE | mmap.PROT_READ)

    def show(self, frame):
        """Resize and write a BGR frame to the framebuffer."""
        resized = cv2.resize(frame, (self.xres, self.yres),
                             interpolation=cv2.INTER_NEAREST)

        if self.bpp == 16:
            converted = self._bgr_to_rgb565(resized)
        elif self.bpp == 32:
            converted = cv2.cvtColor(resized, cv2.COLOR_BGR2BGRA)
            converted = converted.tobytes()
        else:
            raise RuntimeError(f"Unsupported framebuffer depth: {self.bpp}bpp")

        bytes_per_pixel = self.bpp // 8
        row_bytes = self.xres * bytes_per_pixel

        if self.line_length == row_bytes:
            # No padding — single bulk write (much faster)
            self.fbmap[:len(converted)] = converted
        else:
            # Row-by-row to handle line_length padding
            src_offset = 0
            dst_offset = 0
            for _ in range(self.yres):
                self.fbmap[dst_offset:dst_offset + row_bytes] = (
                    converted[src_offset:src_offset + row_bytes])
                src_offset += row_bytes
                dst_offset += self.line_length

    @staticmethod
    def _bgr_to_rgb565(frame):
        """Convert BGR888 numpy array to RGB565 bytes."""
        b = frame[:, :, 0].astype(np.uint16)
        g = frame[:, :, 1].astype(np.uint16)
        r = frame[:, :, 2].astype(np.uint16)
        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        return rgb565.tobytes()

    def close(self):
        if self.fbmap is not None:
            self.fbmap.close()
            self.fbmap = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
