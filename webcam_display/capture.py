"""Webcam capture using OpenCV with V4L2 backend."""

import cv2


class WebcamCapture:
    """Captures frames from a USB webcam via OpenCV."""

    def __init__(self, device_index=0, width=640, height=480,
                 use_mjpeg=True, buffer_size=1):
        self.device_index = device_index
        self.width = width
        self.height = height
        self.use_mjpeg = use_mjpeg
        self.buffer_size = buffer_size
        self.cap = None

    def open(self):
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            raise RuntimeError(
                f"Cannot open video device {self.device_index}")

        if self.use_mjpeg:
            self.cap.set(cv2.CAP_PROP_FOURCC,
                         cv2.VideoWriter_fourcc(*"MJPG"))

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, self.buffer_size)

        actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        print(f"Webcam opened: {actual_w}x{actual_h}")

    def read(self):
        """Read a frame. Returns the frame (BGR numpy array) or None on failure."""
        ret, frame = self.cap.read()
        if not ret:
            return None
        return frame

    def close(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
