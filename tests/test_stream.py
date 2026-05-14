import numpy as np
import pytest
from unittest.mock import patch, MagicMock
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from stream import FrameStream


def make_mock_jpeg():
    """Return minimal valid JPEG bytes (1x1 white pixel)."""
    import cv2
    frame = np.ones((10, 10, 3), dtype=np.uint8) * 255
    _, buf = cv2.imencode('.jpg', frame)
    return buf.tobytes()


def test_frame_stream_yields_numpy_array():
    """FrameStream should yield numpy arrays from MJPEG stream via SOI/EOI marker extraction."""
    jpeg = make_mock_jpeg()
    mock_content = jpeg  # raw JPEG bytes — implementation finds SOI/EOI markers directly

    mock_resp = MagicMock()
    mock_resp.iter_content.return_value = [mock_content]
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)

    with patch('stream.requests.get', return_value=mock_resp):
        fs = FrameStream('http://fake-ip/stream', webcam_fallback=False)
        frames = list(fs._iter_esp32_frames())

    assert len(frames) >= 1
    assert isinstance(frames[0], np.ndarray)
    assert frames[0].shape[2] == 3  # BGR channels


def test_frame_stream_handles_connection_error(capsys):
    """FrameStream should print warning on connection error (not crash)."""
    import requests
    with patch('stream.requests.get', side_effect=requests.exceptions.ConnectionError):
        fs = FrameStream('http://fake-ip/stream', webcam_fallback=False)
        frames = list(fs._iter_esp32_frames())
    assert frames == []
