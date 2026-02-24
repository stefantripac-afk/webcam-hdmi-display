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


def _parse_fscreeninfo(buf):
    """Extract line_length from fb_fix_screeninfo."""
    # fb_fix_screeninfo: 16 bytes id, then unsigned long smem_start,
    # __u32 smem_len, __u32 type, ...  line_length is at a fixed offset.
    # On 32-bit ARM: offset 48 for line_length (__u32).
    # Struct layout (32-bit): id[16] + smem_start(4) + smem_len(4) +
    #   type(4) + type_aux(4) + visual(4) + xpanstep(2) + ypanstep(2) +
    #   ywrapstep(2) + pad(2) + line_length(4)
    # Total offset to line_length = 16+4+4+4+4+4+2+2+2+2 = 44
    # But on some systems it may differ; use a safer approach.
    # We'll try the standard 32-bit ARM layout (offset 48).
    line_length = struct.unpack_from("I", buf, 48)[0]
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

        # Read fixed screen info
        finfo_buf = bytearray(68)
        fcntl.ioctl(self.fd, FBIOGET_FSCREENINFO, finfo_buf)
        finfo = _parse_fscreeninfo(finfo_buf)
        self.line_length = finfo["line_length"]

        fb_size = self.line_length * self.yres
        self.fbmap = mmap.mmap(self.fd, fb_size,
                               mmap.MAP_SHARED,
                               mmap.PROT_WRITE | mmap.PROT_READ)

        print(f"Framebuffer opened: {self.xres}x{self.yres} "
              f"{self.bpp}bpp, line_length={self.line_length}")

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

        # Write row by row to handle line_length padding
        bytes_per_pixel = self.bpp // 8
        row_bytes = self.xres * bytes_per_pixel
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
