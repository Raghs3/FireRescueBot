# Fire Rescue RC Car — Design Spec
**Date:** 2026-05-14  
**Status:** Draft

---

## Overview

An RC car equipped with an ESP32-Cam streams live video to a laptop. A Python backend runs YOLOv8-based detection for flames, humans, and obstructions. A web dashboard displays the annotated feed, shows alerts, and lets the operator drive the car via WASD/buttons. The car is driven over Bluetooth serial (HC-05) to an existing Arduino + HW-130 motor shield.

---

## Hardware

| Component | Role |
|-----------|------|
| ESP32-Cam (AI-Thinker) | WiFi MJPEG video stream |
| Arduino Uno | Motor controller |
| HW-130 Motor Driver Shield | Drives 4x DC motors |
| HC-05 Bluetooth Module | Receives serial commands from laptop |
| Ultrasonic sensor (HC-SR04) | Physical emergency stop (<12 cm) |
| Laptop (any) | Detection, dashboard, BT serial host |

No additional hardware purchases required.

---

## Architecture

```
[ESP32-Cam]
    | WiFi MJPEG (http://<ip>/stream)
    ▼
[Python Backend — FastAPI]
    ├── stream.py       pulls frames from ESP32
    ├── detection.py    YOLOv8 inference per frame
    ├── car_control.py  BT serial to HC-05
    └── main.py         serves dashboard + WebSocket alerts
    |
    ├── annotated MJPEG → browser video element
    └── WebSocket alerts → dashboard alert panel
    |
[Web Dashboard — index.html]
    ├── Live annotated video feed
    ├── Alert log panel
    ├── Car control buttons (F/B/L/R/Stop)
    └── Status bar (cam / BT / GPU mode)
    |
    [WASD keydown] → WebSocket → backend → BT serial
    ▼
[HC-05] → [Arduino Uno + HW-130]
    └── 4x DC Motors
```

---

## Components

### 1. ESP32-Cam Firmware (`esp32cam/`)

- Connects to WiFi using credentials in firmware (SSID/password hardcoded or via `config.h`)
- Streams MJPEG at `/stream` endpoint on port 80
- Resolution: SVGA (800×600) default, configurable down to VGA (640×480) for lower latency
- Uses AI-Thinker pin mapping
- Backend hits `http://<ESP32_IP>/stream` — IP printed to serial on boot

### 2. Arduino Firmware (`arduino/`)

- Always-on Bluetooth control mode (Serial at 9600 baud)
- Commands: `F` forward, `B` backward, `L` left, `R` right, `S` stop
- Ultrasonic emergency stop: if distance < 12 cm, override any command and stop
- Uses `AFMotor` library (compatible with HW-130)
- Motor speed: 170 (configurable constant)
- Servo removed from active use (not needed for BT-only mode)

### 3. Python Backend (`backend/`)

**`stream.py`**
- Opens ESP32-Cam MJPEG stream via `requests` (multipart boundary parsing)
- Yields raw frames as numpy arrays
- Reconnects on drop with 2s backoff

**`detection.py`**
- Loads two models at startup:
  - `yolov8n.pt` (CPU) or `yolov8s.pt` (GPU) — human detection, COCO `person` class
  - Fire detection `.pt` — fine-tuned YOLOv8, `fire`/`flame` classes
- Auto-detects CUDA on startup, selects model size accordingly
- Per-frame: run both models, merge results
- Obstruction logic: any bounding box whose center falls within the horizontal middle 40% of the frame AND whose width exceeds 25% of frame width → obstruction alert
- Returns: annotated frame (BGR) + list of active alerts `[{type, confidence, bbox}]`

**`car_control.py`**
- Finds HC-05 COM port: reads `BT_PORT` from `.env` if set; otherwise auto-scans available COM ports and picks the first Bluetooth-named port (e.g., contains "Bluetooth" or "HC-05" in description)
- Opens `pyserial` connection at 9600 baud
- Exposes `send(cmd: str)` — sends single byte (`F`/`B`/`L`/`R`/`S`)
- Thread-safe; last command wins (no queue)

**`main.py`** (FastAPI)
- `GET /` — serves `frontend/index.html`
- `GET /video_feed` — MJPEG stream of annotated frames
- `WS /ws` — WebSocket for:
  - Server → client: alert events `{type, confidence, timestamp}`
  - Client → server: car commands `{cmd: "F"|"B"|"L"|"R"|"S"}`
- Background task: frame loop (pull → detect → encode → push to `/video_feed` + emit alerts)
- Config via `.env`: `ESP32_IP`, `BT_PORT` (optional override), `MODEL_SIZE` (optional override)

### 4. Web Dashboard (`frontend/`)

**Video panel:** `<img>` tag pointed at `/video_feed` MJPEG stream. Detection bounding boxes drawn server-side on frame before streaming.

**Alert panel:** Scrollable log. Color-coded:
- 🔴 Human detected in fire zone
- 🟠 Flame detected
- 🟡 Obstruction ahead

Alert sound: Web Audio API — short beep on new alert (respects browser autoplay policy via user interaction gate).

**Car controls:**
- On-screen buttons: Forward / Back / Left / Right / Stop
- WASD keyboard: keydown sends command, keyup sends `S` (stop)
- Sends via WebSocket to backend

**Status bar:** Camera connected (green/red), BT connected (green/red), detection mode (GPU/CPU).

---

## Detection Models

| Target | Model | Source | Classes used |
|--------|-------|--------|-------------|
| Human | YOLOv8n/s (COCO) | Auto-download via `ultralytics` | `person` (class 0) |
| Fire/Flame | Fire-YOLOv8 | HuggingFace `keremberke/yolov8n-fire-detection` | `fire` |
| Obstruction | Rule-based on above detections | — | Any large centered box |

No training required. Models download once (~6–30 MB total), cached in `backend/models/`.

### Alert Priority

1. **Human in fire zone** — person box and fire box overlap (IoU > 0) OR their centers are within 100px of each other
2. **Flame detected** — fire box present, no person overlap
3. **Obstruction ahead** — large centered box, no fire

---

## Folder Structure

```
fire-rescue-rc/
├── arduino/
│   └── rc_car/
│       └── rc_car.ino
├── esp32cam/
│   └── esp32cam_stream/
│       ├── esp32cam_stream.ino
│       └── config.h               # WiFi credentials (gitignored)
├── backend/
│   ├── main.py
│   ├── stream.py
│   ├── detection.py
│   ├── car_control.py
│   ├── requirements.txt
│   ├── .env.example
│   └── models/                    # downloaded weights land here
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-14-fire-rescue-rc-design.md
```

---

## Setup Flow

### ESP32-Cam
1. Install Arduino IDE + ESP32 board package
2. Edit `config.h` with WiFi credentials
3. Flash `esp32cam_stream.ino`
4. Note IP from Serial Monitor

### Arduino
1. Install `AFMotor` library
2. Flash `rc_car.ino`
3. Pair HC-05 with laptop (PIN: 1234 or 0000)
4. Note COM port assigned to HC-05

### Laptop
```bash
cd fire-rescue-rc/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# Edit .env: set ESP32_IP and BT_PORT
python main.py
# Open http://localhost:8000
```

---

## Error Handling

| Failure | Behavior |
|---------|----------|
| ESP32 stream drops | Backend retries every 2s, dashboard shows "Camera disconnected" |
| HC-05 not found | Backend starts without BT, dashboard shows "BT disconnected", controls disabled |
| Model load fails | Fatal error at startup with clear message |
| Frame detection too slow | Drop frames (process latest available, skip queued frames) |

---

## Out of Scope (MVP)

- Recording/saving video
- Mobile app
- Multiple cameras
- Autonomous driving mode
- Remote access over internet (LAN only)
