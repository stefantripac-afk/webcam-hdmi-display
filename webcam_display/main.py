#!/usr/bin/env python3
"""Capture from Logitech C270 webcam and display on HDMI via OpenCV."""

import sys
import cv2
import config


def main():
    cap = cv2.VideoCapture(config.DEVICE_INDEX)
    if not cap.isOpened():
        print(f"Error: cannot open video device {config.DEVICE_INDEX}")
        sys.exit(1)

    if config.USE_MJPEG:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAPTURE_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAPTURE_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, config.BUFFER_SIZE)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Capturing at {actual_w}x{actual_h}")

    cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(
        config.WINDOW_NAME, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
    )

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: failed to grab frame")
                break

            cv2.imshow(config.WINDOW_NAME, frame)

            if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
