#!/usr/bin/env python3
"""Capture from Logitech C270 webcam and display fullscreen on HDMI via framebuffer."""

import argparse
import signal
import sys
import time

import config
from capture import WebcamCapture
from display import FramebufferDisplay

running = True


def stop(signum, frame):
    global running
    running = False


def main():
    parser = argparse.ArgumentParser(
        description="Webcam to HDMI framebuffer display")
    parser.add_argument("-d", "--device", type=int,
                        default=config.DEVICE_INDEX,
                        help="Video device index")
    parser.add_argument("-f", "--fb", default=config.FB_DEVICE,
                        help="Framebuffer device path")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    with WebcamCapture(
        device_index=args.device,
        width=config.CAPTURE_WIDTH,
        height=config.CAPTURE_HEIGHT,
        use_mjpeg=config.USE_MJPEG,
        buffer_size=config.BUFFER_SIZE,
    ) as cam, FramebufferDisplay(fb_device=args.fb) as fb:

        frame_interval = 1.0 / config.TARGET_FPS
        frame_count = 0
        fps_start = time.monotonic()

        print(f"Streaming at target {config.TARGET_FPS} FPS. "
              "Press Ctrl+C to stop.")

        while running:
            loop_start = time.monotonic()

            frame = cam.read()
            if frame is None:
                print("Warning: failed to grab frame, retrying...")
                time.sleep(0.1)
                continue

            fb.show(frame)
            frame_count += 1

            # Print FPS every 5 seconds
            elapsed = time.monotonic() - fps_start
            if elapsed >= 5.0:
                print(f"FPS: {frame_count / elapsed:.1f}")
                frame_count = 0
                fps_start = time.monotonic()

            # Throttle to target FPS
            spent = time.monotonic() - loop_start
            if spent < frame_interval:
                time.sleep(frame_interval - spent)

    print("Shutdown complete.")


if __name__ == "__main__":
    main()
