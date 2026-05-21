import cv2
import numpy as np
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()

BOUNDARY = b'--frame'


class FrameStream:
    def __init__(self, url: str, webcam_fallback: bool = False):
        self.url = url
        self.webcam_fallback = webcam_fallback

    def _iter_esp32_frames(self):
        try:
            with requests.get(self.url, stream=True, timeout=(10, 30)) as resp:
                buf = b''
                for chunk in resp.iter_content(chunk_size=4096):
                    buf += chunk
                    while True:
                        # Find Content-Length header to read exact frame bytes
                        cl_start = buf.find(b'Content-Length:')
                        if cl_start == -1:
                            break
                        nl = buf.find(b'\r\n\r\n', cl_start)
                        if nl == -1:
                            break
                        try:
                            length = int(buf[cl_start + 15:nl].strip())
                        except ValueError:
                            buf = buf[cl_start + 15:]
                            break
                        frame_start = nl + 4
                        frame_end = frame_start + length
                        if len(buf) < frame_end:
                            break  # wait for more chunks
                        jpeg = buf[frame_start:frame_end]
                        buf = buf[frame_end:]
                        arr = np.frombuffer(jpeg, dtype=np.uint8)
                        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            yield frame
        except requests.exceptions.RequestException as e:
            print(f"[stream] ESP32 connection error: {e}")

    def _iter_webcam_frames(self):
        cap = cv2.VideoCapture(0)
        try:
            while cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    yield frame
        finally:
            cap.release()

    def frames(self):
        while True:
            for frame in self._iter_esp32_frames():
                yield frame
            if self.webcam_fallback:
                print("[stream] Falling back to webcam")
                for frame in self._iter_webcam_frames():
                    yield frame
                return
            print("[stream] Retrying ESP32 in 2s...")
            time.sleep(2)


def make_stream() -> FrameStream:
    ip = os.getenv('ESP32_IP', '192.168.1.100')
    fallback = os.getenv('WEBCAM_FALLBACK', 'false').lower() == 'true'
    return FrameStream(f'http://{ip}/stream', webcam_fallback=fallback)
