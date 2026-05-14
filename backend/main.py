import asyncio
import cv2
import threading
import numpy as np
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Set

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from stream import make_stream
from detection import Detector
from car_control import make_car_control

# Shared state — written by background thread, read by async routes
latest_frame: np.ndarray | None = None
_frame_lock = threading.Lock()
connected_ws: Set[WebSocket] = set()
_alert_queue: asyncio.Queue = None


def _frame_worker(detector: Detector, stream_obj, alert_queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
    """Background thread: pull frames, detect, push results."""
    global latest_frame
    for frame in stream_obj.frames():
        annotated, alerts = detector.process(frame)
        with _frame_lock:
            latest_frame = annotated
        for alert in alerts:
            asyncio.run_coroutine_threadsafe(
                alert_queue.put(alert), loop
            )


async def _alert_broadcaster(alert_queue: asyncio.Queue):
    """Async task: drain alert queue and broadcast to WebSocket clients."""
    while True:
        alert = await alert_queue.get()
        await _broadcast({'event': 'alert', 'type': alert['type'], 'conf': round(alert['conf'], 2)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _alert_queue
    detector = Detector()
    stream_obj = make_stream()
    car = make_car_control()
    app.state.car = car
    app.state.detector = detector

    loop = asyncio.get_event_loop()
    _alert_queue = asyncio.Queue()

    worker = threading.Thread(target=_frame_worker, args=(detector, stream_obj, _alert_queue, loop), daemon=True)
    worker.start()

    broadcaster_task = asyncio.create_task(_alert_broadcaster(_alert_queue))
    yield
    broadcaster_task.cancel()
    car.disconnect()


app = FastAPI(lifespan=lifespan)
_FRONTEND = Path(__file__).parent.parent / 'frontend'
app.mount("/static", StaticFiles(directory=str(_FRONTEND)), name="static")


async def _broadcast(data: dict):
    dead = set()
    for ws in list(connected_ws):
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    connected_ws.difference_update(dead)


async def _mjpeg_generator():
    while True:
        with _frame_lock:
            frame = latest_frame

        if frame is None:
            await asyncio.sleep(0.05)
            continue

        _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' +
            buf.tobytes() +
            b'\r\n'
        )
        await asyncio.sleep(0.033)  # ~30fps cap


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(_FRONTEND / 'index.html') as f:
        return f.read()


@app.get("/video_feed")
async def video_feed():
    return StreamingResponse(
        _mjpeg_generator(),
        media_type='multipart/x-mixed-replace; boundary=frame'
    )


@app.get("/status")
async def status():
    return {
        'camera': latest_frame is not None,
        'bluetooth': app.state.car.is_connected,
        'gpu': app.state.detector.device == 'cuda',
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_ws.add(websocket)
    await websocket.send_json({
        'event': 'status',
        'camera': latest_frame is not None,
        'bluetooth': app.state.car.is_connected,
        'gpu': app.state.detector.device == 'cuda',
    })
    try:
        while True:
            data = await websocket.receive_json()
            if 'cmd' in data:
                app.state.car.send(data['cmd'])
    except WebSocketDisconnect:
        connected_ws.discard(websocket)


if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=8000, reload=False)
