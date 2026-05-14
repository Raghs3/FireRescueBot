# Fire Rescue RC Car Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a fire rescue RC car system: ESP32-Cam streams live video to a laptop, YOLOv8 detects flames and humans, a web dashboard shows annotated feed + alerts, and the user drives the car via WASD over Bluetooth serial.

**Architecture:** ESP32-Cam streams MJPEG over WiFi → Python FastAPI backend pulls frames, runs dual YOLOv8 detection, annotates frames, broadcasts via MJPEG + WebSocket → Browser dashboard shows live feed with bounding boxes, scrollable alert log, and car control buttons. WASD commands travel WebSocket → backend → pyserial → HC-05 Bluetooth → Arduino + HW-130 motors.

**Tech Stack:** Python 3.11+, FastAPI, ultralytics (YOLOv8), OpenCV, pyserial, huggingface_hub, pytest; Arduino C++ (AFMotor lib); ESP32-Cam Arduino SDK; Vanilla HTML/CSS/JS frontend.

---

## File Map

```
fire-rescue-rc/
├── .gitignore
├── arduino/
│   └── rc_car/
│       └── rc_car.ino                 # Arduino BT motor controller
├── esp32cam/
│   └── esp32cam_stream/
│       ├── esp32cam_stream.ino        # MJPEG WiFi streamer
│       └── config.h                   # WiFi credentials (gitignored)
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── .env                           # gitignored
│   ├── main.py                        # FastAPI app: routes, WS, frame loop
│   ├── stream.py                      # ESP32 MJPEG consumer + webcam fallback
│   ├── detection.py                   # YOLOv8 inference + alert classification
│   ├── car_control.py                 # BT serial wrapper
│   └── models/                        # downloaded .pt weights (gitignored)
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── tests/
    ├── test_stream.py
    ├── test_detection.py
    └── test_car_control.py
```

---

## Task 1: Project Scaffold

**Files:**
- Create: `fire-rescue-rc/.gitignore`
- Create: `fire-rescue-rc/backend/requirements.txt`
- Create: `fire-rescue-rc/backend/.env.example`

- [ ] **Step 1: Create .gitignore**

Create `fire-rescue-rc/.gitignore`:
```
# Python
.venv/
__pycache__/
*.pyc
.env

# Models (large binary weights)
backend/models/*.pt

# ESP32 WiFi credentials
esp32cam/esp32cam_stream/config.h

# IDE
.vscode/
*.swp
```

- [ ] **Step 2: Create requirements.txt**

Create `fire-rescue-rc/backend/requirements.txt`:
```
fastapi>=0.110.0
uvicorn[standard]>=0.27.0
ultralytics>=8.1.0
opencv-python>=4.9.0
requests>=2.31.0
pyserial>=3.5
python-dotenv>=1.0.0
huggingface_hub>=0.21.0
numpy>=1.26.0
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.27.0
```

- [ ] **Step 3: Create .env.example**

Create `fire-rescue-rc/backend/.env.example`:
```
# IP shown in Arduino Serial Monitor when ESP32-Cam boots
ESP32_IP=192.168.1.100

# COM port for HC-05 Bluetooth (e.g. COM5 on Windows, /dev/rfcomm0 on Linux)
# Leave blank to auto-detect
BT_PORT=

# auto = detect GPU; nano = force CPU model; small = force GPU model
MODEL_SIZE=auto

# Set true to use laptop webcam if ESP32 stream unavailable
WEBCAM_FALLBACK=false
```

- [ ] **Step 4: Create venv and install dependencies**

```bash
cd fire-rescue-rc/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Expected: packages install without errors. `ultralytics` will be ~200 MB.

- [ ] **Step 5: Create models directory**

```bash
mkdir fire-rescue-rc/backend/models
```

- [ ] **Step 6: Create tests directory**

```bash
mkdir fire-rescue-rc/tests
```

- [ ] **Step 7: Commit scaffold**

```bash
cd fire-rescue-rc
git init
git add .gitignore backend/requirements.txt backend/.env.example
git commit -m "chore: project scaffold, requirements, gitignore"
```

---

## Task 2: Arduino Firmware

**Files:**
- Create: `arduino/rc_car/rc_car.ino`

No automated tests possible (hardware). Manual test steps provided.

**Prerequisites:** Arduino IDE installed, AFMotor library installed (Sketch → Include Library → Manage Libraries → search "AFMotor" → install Adafruit Motor Shield library).

- [ ] **Step 1: Write rc_car.ino**

Create `arduino/rc_car/rc_car.ino`:
```cpp
#include <AFMotor.h>

#define ECHO_PIN A0
#define TRIG_PIN A1
#define MOTOR_SPEED 170
#define SAFE_DISTANCE_CM 12

AF_DCMotor M1(1);
AF_DCMotor M2(2);
AF_DCMotor M3(3);
AF_DCMotor M4(4);

char cmd = 'S';

void setup() {
  Serial.begin(9600);
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  M1.setSpeed(MOTOR_SPEED);
  M2.setSpeed(MOTOR_SPEED);
  M3.setSpeed(MOTOR_SPEED);
  M4.setSpeed(MOTOR_SPEED);
  stopMotors();
}

void loop() {
  if (Serial.available() > 0) {
    cmd = Serial.read();
  }

  if (getDistance() <= SAFE_DISTANCE_CM && cmd == 'F') {
    stopMotors();
    return;
  }

  switch (cmd) {
    case 'F': forward();     break;
    case 'B': backward();    break;
    case 'L': turnLeft();    break;
    case 'R': turnRight();   break;
    case 'S': stopMotors();  break;
  }
}

int getDistance() {
  digitalWrite(TRIG_PIN, LOW);
  delayMicroseconds(4);
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long t = pulseIn(ECHO_PIN, HIGH);
  return (int)(t / 29 / 2);
}

void forward() {
  M1.run(FORWARD); M2.run(FORWARD);
  M3.run(FORWARD); M4.run(FORWARD);
}

void backward() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}

void turnLeft() {
  M1.run(FORWARD);  M2.run(FORWARD);
  M3.run(BACKWARD); M4.run(BACKWARD);
}

void turnRight() {
  M1.run(BACKWARD); M2.run(BACKWARD);
  M3.run(FORWARD);  M4.run(FORWARD);
}

void stopMotors() {
  M1.run(RELEASE); M2.run(RELEASE);
  M3.run(RELEASE); M4.run(RELEASE);
}
```

- [ ] **Step 2: Flash to Arduino**

1. Open `arduino/rc_car/rc_car.ino` in Arduino IDE
2. Tools → Board → Arduino Uno
3. Tools → Port → select your Arduino COM port
4. Click Upload

- [ ] **Step 3: Manual test via Serial Monitor**

1. Open Serial Monitor (115200 baud display, but device runs at 9600 — set dropdown to 9600)
2. Send `F` → wheels spin forward
3. Send `S` → wheels stop
4. Send `B` → wheels spin backward
5. Send `L` / `R` → car turns
6. Hold hand in front of ultrasonic sensor, send `F` → car should NOT move (emergency stop)

- [ ] **Step 4: Commit**

```bash
git add arduino/
git commit -m "feat: arduino BT motor controller with ultrasonic safety stop"
```

---

## Task 3: ESP32-Cam Firmware

**Files:**
- Create: `esp32cam/esp32cam_stream/config.h`
- Create: `esp32cam/esp32cam_stream/esp32cam_stream.ino`

**Prerequisites:**
- Arduino IDE with ESP32 board package installed
- Board package URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
- Add via: File → Preferences → Additional Board URLs
- Then: Tools → Board Manager → search "esp32" → install "esp32 by Espressif"

- [ ] **Step 1: Create config.h with WiFi credentials**

Create `esp32cam/esp32cam_stream/config.h`:
```cpp
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"
```

Replace with your actual WiFi network name and password. This file is gitignored.

- [ ] **Step 2: Write esp32cam_stream.ino**

Create `esp32cam/esp32cam_stream/esp32cam_stream.ino`:
```cpp
#include "esp_camera.h"
#include <WiFi.h>
#include "esp_http_server.h"
#include "config.h"

// AI-Thinker ESP32-Cam pin mapping
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

static const char STREAM_CONTENT_TYPE[] = "multipart/x-mixed-replace;boundary=frame";
static const char STREAM_BOUNDARY[] = "\r\n--frame\r\n";
static const char STREAM_PART[] = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

httpd_handle_t stream_httpd = NULL;

static esp_err_t stream_handler(httpd_req_t *req) {
  camera_fb_t *fb = NULL;
  esp_err_t res = ESP_OK;
  char part_buf[64];

  res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) return res;

  while (true) {
    fb = esp_camera_fb_get();
    if (!fb) {
      res = ESP_FAIL;
      break;
    }

    httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY));
    size_t hlen = snprintf(part_buf, sizeof(part_buf), STREAM_PART, fb->len);
    httpd_resp_send_chunk(req, part_buf, hlen);
    httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len);

    esp_camera_fb_return(fb);

    if (res != ESP_OK) break;
  }
  return res;
}

void startCameraServer() {
  httpd_config_t config = HTTPD_DEFAULT_CONFIG();
  config.server_port = 80;
  httpd_uri_t stream_uri = {
    .uri       = "/stream",
    .method    = HTTP_GET,
    .handler   = stream_handler,
    .user_ctx  = NULL
  };
  if (httpd_start(&stream_httpd, &config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }
}

void setup() {
  Serial.begin(115200);

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_VGA;   // 640x480
  config.jpeg_quality = 12;
  config.fb_count     = 2;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x\n", err);
    return;
  }

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.print("Stream URL: http://");
  Serial.print(WiFi.localIP());
  Serial.println("/stream");

  startCameraServer();
}

void loop() {
  delay(1);
}
```

- [ ] **Step 3: Flash to ESP32-Cam**

1. Open `esp32cam/esp32cam_stream/esp32cam_stream.ino` in Arduino IDE
2. Tools → Board → "AI Thinker ESP32-CAM"
3. Tools → Port → select ESP32 port
4. **Important:** Hold IO0 button to GND during upload, release after upload starts
5. Click Upload
6. After upload: press RST button, open Serial Monitor at 115200 baud

- [ ] **Step 4: Note the IP address**

Serial Monitor will print:
```
WiFi connected
Stream URL: http://192.168.X.X/stream
```

Copy this IP — you'll need it for `.env`.

- [ ] **Step 5: Manual test**

Open `http://192.168.X.X/stream` in a browser. Should see live MJPEG video feed.

- [ ] **Step 6: Commit**

```bash
git add esp32cam/
git commit -m "feat: esp32cam MJPEG WiFi stream on /stream endpoint"
```

---

## Task 4: stream.py — Frame Consumer

**Files:**
- Create: `backend/stream.py`
- Create: `tests/test_stream.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_stream.py`:
```python
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
    """FrameStream should yield numpy arrays from MJPEG chunks."""
    jpeg = make_mock_jpeg()
    boundary = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n'
    mock_content = boundary + jpeg + b'\r\n'

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
```

- [ ] **Step 2: Run test — expect failure**

```bash
cd fire-rescue-rc/backend
.venv\Scripts\activate
cd ..
pytest tests/test_stream.py -v
```

Expected: `ModuleNotFoundError: No module named 'stream'`

- [ ] **Step 3: Write stream.py**

Create `backend/stream.py`:
```python
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
            with requests.get(self.url, stream=True, timeout=5) as resp:
                buf = b''
                for chunk in resp.iter_content(chunk_size=4096):
                    buf += chunk
                    while True:
                        start = buf.find(b'\xff\xd8')  # JPEG SOI
                        end = buf.find(b'\xff\xd9')    # JPEG EOI
                        if start == -1 or end == -1:
                            break
                        jpeg = buf[start:end + 2]
                        buf = buf[end + 2:]
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
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_stream.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/stream.py tests/test_stream.py
git commit -m "feat: esp32 mjpeg frame consumer with webcam fallback"
```

---

## Task 5: detection.py — YOLOv8 Inference + Alert Classification

**Files:**
- Create: `backend/detection.py`
- Create: `tests/test_detection.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_detection.py`:
```python
import numpy as np
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from detection import classify_alerts, Detection, AlertType


def make_detection(cls: str, x1: int, y1: int, x2: int, y2: int, conf: float = 0.9) -> Detection:
    return Detection(cls=cls, x1=x1, y1=y1, x2=x2, y2=y2, conf=conf)


FRAME_W, FRAME_H = 640, 480


def test_no_detections_returns_no_alerts():
    alerts = classify_alerts([], FRAME_W, FRAME_H)
    assert alerts == []


def test_fire_only_returns_flame_alert():
    dets = [make_detection('fire', 100, 100, 200, 200)]
    alerts = classify_alerts(dets, FRAME_W, FRAME_H)
    types = [a['type'] for a in alerts]
    assert AlertType.FLAME in types
    assert AlertType.HUMAN_IN_FIRE not in types


def test_person_only_returns_no_fire_alert():
    dets = [make_detection('person', 100, 100, 200, 200)]
    alerts = classify_alerts(dets, FRAME_W, FRAME_H)
    types = [a['type'] for a in alerts]
    assert AlertType.FLAME not in types
    assert AlertType.HUMAN_IN_FIRE not in types


def test_person_near_fire_returns_human_in_fire():
    # Person and fire boxes overlap
    dets = [
        make_detection('person', 100, 100, 200, 200),
        make_detection('fire',   150, 150, 250, 250),
    ]
    alerts = classify_alerts(dets, FRAME_W, FRAME_H)
    types = [a['type'] for a in alerts]
    assert AlertType.HUMAN_IN_FIRE in types


def test_obstruction_large_centered_box():
    # Box covering center 40% horizontally, wider than 25% of frame
    cx = FRAME_W // 2  # 320
    w = int(FRAME_W * 0.3)  # 192px — more than 25%
    dets = [make_detection('person', cx - w//2, 50, cx + w//2, 400)]
    alerts = classify_alerts(dets, FRAME_W, FRAME_H)
    types = [a['type'] for a in alerts]
    assert AlertType.OBSTRUCTION in types


def test_obstruction_small_box_not_flagged():
    # Box too small to be obstruction
    dets = [make_detection('person', 300, 200, 340, 240)]
    alerts = classify_alerts(dets, FRAME_W, FRAME_H)
    types = [a['type'] for a in alerts]
    assert AlertType.OBSTRUCTION not in types
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_detection.py -v
```

Expected: `ModuleNotFoundError: No module named 'detection'`

- [ ] **Step 3: Write detection.py**

Create `backend/detection.py`:
```python
import cv2
import numpy as np
import os
import torch
from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Any
from pathlib import Path
from ultralytics import YOLO
from huggingface_hub import hf_hub_download
from dotenv import load_dotenv

load_dotenv()

MODELS_DIR = Path(__file__).parent / 'models'
MODELS_DIR.mkdir(exist_ok=True)


class AlertType(str, Enum):
    HUMAN_IN_FIRE = 'human_in_fire'
    FLAME = 'flame'
    OBSTRUCTION = 'obstruction'


@dataclass
class Detection:
    cls: str
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float

    @property
    def cx(self) -> int:
        return (self.x1 + self.x2) // 2

    @property
    def cy(self) -> int:
        return (self.y1 + self.y2) // 2

    @property
    def width(self) -> int:
        return self.x2 - self.x1


BOX_COLORS = {
    'person': (0, 0, 255),    # red
    'fire':   (0, 128, 255),  # orange
}
LABEL_BG = (0, 0, 0)


def _iou(a: Detection, b: Detection) -> float:
    ix1 = max(a.x1, b.x1)
    iy1 = max(a.y1, b.y1)
    ix2 = min(a.x2, b.x2)
    iy2 = min(a.y2, b.y2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0
    inter = (ix2 - ix1) * (iy2 - iy1)
    area_a = (a.x2 - a.x1) * (a.y2 - a.y1)
    area_b = (b.x2 - b.x1) * (b.y2 - b.y1)
    return inter / float(area_a + area_b - inter)


def _center_dist(a: Detection, b: Detection) -> float:
    return ((a.cx - b.cx) ** 2 + (a.cy - b.cy) ** 2) ** 0.5


def classify_alerts(detections: List[Detection], frame_w: int, frame_h: int) -> List[Dict[str, Any]]:
    alerts = []
    persons = [d for d in detections if d.cls == 'person']
    fires   = [d for d in detections if d.cls == 'fire']

    # Human in fire: person overlaps or within 100px of fire
    for p in persons:
        for f in fires:
            if _iou(p, f) > 0 or _center_dist(p, f) <= 100:
                alerts.append({'type': AlertType.HUMAN_IN_FIRE, 'conf': min(p.conf, f.conf)})
                break

    # Flame only (no nearby person already flagged)
    human_in_fire_persons = set()
    for alert in alerts:
        if alert['type'] == AlertType.HUMAN_IN_FIRE:
            human_in_fire_persons.update(persons)

    for f in fires:
        nearby_person = any(_iou(p, f) > 0 or _center_dist(p, f) <= 100 for p in persons)
        if not nearby_person:
            alerts.append({'type': AlertType.FLAME, 'conf': f.conf})

    # Obstruction: large box centered in frame
    center_zone_x1 = frame_w * 0.3
    center_zone_x2 = frame_w * 0.7
    min_width = frame_w * 0.25

    for d in detections:
        if center_zone_x1 <= d.cx <= center_zone_x2 and d.width >= min_width:
            alerts.append({'type': AlertType.OBSTRUCTION, 'conf': d.conf})
            break  # one obstruction alert max

    return alerts


def _draw_boxes(frame: np.ndarray, detections: List[Detection], alerts: List[Dict]) -> np.ndarray:
    annotated = frame.copy()
    human_in_fire = any(a['type'] == AlertType.HUMAN_IN_FIRE for a in alerts)

    if human_in_fire:
        # Red pulsing border effect (solid red border)
        cv2.rectangle(annotated, (0, 0), (annotated.shape[1]-1, annotated.shape[0]-1),
                      (0, 0, 255), 8)

    for d in detections:
        color = BOX_COLORS.get(d.cls, (128, 128, 128))
        cv2.rectangle(annotated, (d.x1, d.y1), (d.x2, d.y2), color, 2)
        label = f"{d.cls} {d.conf:.0%}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(annotated, (d.x1, d.y1 - th - 4), (d.x1 + tw, d.y1), color, -1)
        cv2.putText(annotated, label, (d.x1, d.y1 - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

    return annotated


class Detector:
    def __init__(self):
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        model_size = os.getenv('MODEL_SIZE', 'auto')

        if model_size == 'auto':
            size = 'yolov8s' if device == 'cuda' else 'yolov8n'
        elif model_size == 'small':
            size = 'yolov8s'
        else:
            size = 'yolov8n'

        print(f"[detection] Device: {device}, model: {size}")
        self.person_model = YOLO(f'{size}.pt')
        self.person_model.to(device)

        fire_model_path = MODELS_DIR / 'fire_model.pt'
        if not fire_model_path.exists():
            print("[detection] Downloading fire detection model...")
            downloaded = hf_hub_download(
                repo_id='keremberke/yolov8n-fire-detection',
                filename='best.pt'
            )
            import shutil
            shutil.copy(downloaded, fire_model_path)

        self.fire_model = YOLO(str(fire_model_path))
        self.fire_model.to(device)
        self.device = device

    def process(self, frame: np.ndarray):
        h, w = frame.shape[:2]
        detections: List[Detection] = []

        person_results = self.person_model(frame, classes=[0], verbose=False)[0]
        for box in person_results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append(Detection('person', x1, y1, x2, y2, float(box.conf[0])))

        fire_results = self.fire_model(frame, verbose=False)[0]
        for box in fire_results.boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            detections.append(Detection('fire', x1, y1, x2, y2, float(box.conf[0])))

        alerts = classify_alerts(detections, w, h)
        annotated = _draw_boxes(frame, detections, alerts)
        return annotated, alerts
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_detection.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Smoke test model download**

```bash
cd backend
python -c "from detection import Detector; d = Detector(); print('Models loaded OK')"
```

Expected: downloads fire model (~6 MB first time), prints `Models loaded OK`.

- [ ] **Step 6: Commit**

```bash
git add backend/detection.py tests/test_detection.py
git commit -m "feat: yolov8 dual-model detection with alert classification"
```

---

## Task 6: car_control.py — Bluetooth Serial

**Files:**
- Create: `backend/car_control.py`
- Create: `tests/test_car_control.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_car_control.py`:
```python
import pytest
from unittest.mock import patch, MagicMock, call
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from car_control import CarControl


def test_send_writes_bytes_to_serial():
    mock_serial = MagicMock()
    with patch('car_control.serial.Serial', return_value=mock_serial):
        ctrl = CarControl(port='COM99')
        ctrl.connect()
        ctrl.send('F')
    mock_serial.write.assert_called_once_with(b'F')


def test_send_only_valid_commands():
    mock_serial = MagicMock()
    with patch('car_control.serial.Serial', return_value=mock_serial):
        ctrl = CarControl(port='COM99')
        ctrl.connect()
        ctrl.send('X')  # invalid
    mock_serial.write.assert_not_called()


def test_send_without_connect_does_not_crash():
    ctrl = CarControl(port='COM99')
    ctrl.send('F')  # should silently do nothing


def test_is_connected_false_before_connect():
    ctrl = CarControl(port='COM99')
    assert ctrl.is_connected is False


def test_is_connected_true_after_connect():
    mock_serial = MagicMock()
    with patch('car_control.serial.Serial', return_value=mock_serial):
        ctrl = CarControl(port='COM99')
        ctrl.connect()
    assert ctrl.is_connected is True
```

- [ ] **Step 2: Run tests — expect failure**

```bash
pytest tests/test_car_control.py -v
```

Expected: `ModuleNotFoundError: No module named 'car_control'`

- [ ] **Step 3: Write car_control.py**

Create `backend/car_control.py`:
```python
import serial
import serial.tools.list_ports
import os
import threading
from dotenv import load_dotenv

load_dotenv()

VALID_COMMANDS = frozenset('FBLRS')


class CarControl:
    def __init__(self, port: str | None = None):
        self._port = port or os.getenv('BT_PORT') or self._auto_detect_port()
        self._serial: serial.Serial | None = None
        self._lock = threading.Lock()

    def _auto_detect_port(self) -> str | None:
        for p in serial.tools.list_ports.comports():
            desc = (p.description or '').lower()
            if 'bluetooth' in desc or 'hc-05' in desc or 'rfcomm' in desc:
                return p.device
        return None

    def connect(self) -> bool:
        if not self._port:
            print("[car_control] No BT port found. Car controls disabled.")
            return False
        try:
            self._serial = serial.Serial(self._port, 9600, timeout=1)
            print(f"[car_control] Connected to {self._port}")
            return True
        except serial.SerialException as e:
            print(f"[car_control] Failed to connect: {e}")
            self._serial = None
            return False

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    def send(self, cmd: str) -> None:
        if cmd not in VALID_COMMANDS:
            return
        if not self.is_connected:
            return
        with self._lock:
            try:
                self._serial.write(cmd.encode())
            except serial.SerialException as e:
                print(f"[car_control] Write error: {e}")
                self._serial = None

    def disconnect(self) -> None:
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None


def make_car_control() -> CarControl:
    ctrl = CarControl()
    ctrl.connect()
    return ctrl
```

- [ ] **Step 4: Run tests — expect pass**

```bash
pytest tests/test_car_control.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add backend/car_control.py tests/test_car_control.py
git commit -m "feat: bluetooth serial car controller with auto port detection"
```

---

## Task 7: main.py — FastAPI Application

**Files:**
- Create: `backend/main.py`

- [ ] **Step 1: Write main.py**

Create `backend/main.py`:
```python
import asyncio
import cv2
import threading
import numpy as np
from contextlib import asynccontextmanager
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
app.mount("/static", StaticFiles(directory="../frontend"), name="static")


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
    with open('../frontend/index.html') as f:
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
```

- [ ] **Step 2: Create .env from example**

```bash
cd fire-rescue-rc/backend
copy .env.example .env
```

Edit `.env` — set `ESP32_IP` to the IP from Task 3 Step 4. Set `WEBCAM_FALLBACK=true` for testing without ESP32.

- [ ] **Step 3: Smoke test startup**

```bash
cd fire-rescue-rc/backend
.venv\Scripts\activate
python main.py
```

Expected: server starts on `http://0.0.0.0:8000`. No crash. If WEBCAM_FALLBACK=true, webcam opens.

- [ ] **Step 4: Commit**

```bash
git add backend/main.py backend/.env.example
git commit -m "feat: fastapi server with mjpeg stream, websocket alerts, car control endpoint"
```

---

## Task 8: Frontend — Dashboard

**Files:**
- Create: `frontend/index.html`
- Create: `frontend/style.css`
- Create: `frontend/app.js`

- [ ] **Step 1: Write index.html**

Create `frontend/index.html`:
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Fire Rescue RC</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header id="status-bar">
    <span id="status-cam" class="status-badge">CAM: --</span>
    <span id="status-bt"  class="status-badge">BT: --</span>
    <span id="status-gpu" class="status-badge">MODE: --</span>
    <span class="title">Fire Rescue RC</span>
  </header>

  <main>
    <section id="video-panel">
      <div id="video-wrapper">
        <img id="feed" src="/video_feed" alt="Camera Feed">
      </div>
    </section>

    <aside id="side-panel">
      <h2>Alerts</h2>
      <ul id="alert-log"></ul>
    </aside>
  </main>

  <footer id="controls">
    <div id="dpad">
      <button data-cmd="F" title="Forward (W)">▲</button>
      <div class="dpad-row">
        <button data-cmd="L" title="Left (A)">◄</button>
        <button data-cmd="S" title="Stop (Space)">■</button>
        <button data-cmd="R" title="Right (D)">►</button>
      </div>
      <button data-cmd="B" title="Backward (S)">▼</button>
    </div>
    <p class="hint">WASD / Arrow keys also work. Release key to stop.</p>
  </footer>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Write style.css**

Create `frontend/style.css`:
```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  background: #0d0d0d;
  color: #e0e0e0;
  font-family: 'Segoe UI', sans-serif;
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

#status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  background: #1a1a1a;
  border-bottom: 1px solid #333;
  font-size: 0.8rem;
}

.title { margin-left: auto; font-weight: bold; letter-spacing: 1px; }

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  background: #333;
  font-family: monospace;
}
.status-badge.ok   { background: #1a4a1a; color: #6f6; }
.status-badge.fail { background: #4a1a1a; color: #f66; }

main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

#video-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
}

#video-wrapper {
  position: relative;
  border: 2px solid #333;
  border-radius: 4px;
  overflow: hidden;
}

#video-wrapper.alert-fire    { border-color: #ff4400; animation: pulse 0.6s infinite alternate; }
#video-wrapper.alert-human   { border-color: #ff0000; border-width: 6px; animation: pulse 0.3s infinite alternate; }

@keyframes pulse {
  from { box-shadow: 0 0 0 0 rgba(255,0,0,0.7); }
  to   { box-shadow: 0 0 20px 10px rgba(255,0,0,0); }
}

#feed { display: block; max-width: 100%; max-height: 60vh; }

#side-panel {
  width: 260px;
  background: #111;
  border-left: 1px solid #333;
  display: flex;
  flex-direction: column;
  padding: 12px;
}

#side-panel h2 { font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; color: #888; }

#alert-log {
  list-style: none;
  overflow-y: auto;
  flex: 1;
  font-size: 0.82rem;
  display: flex;
  flex-direction: column-reverse;
}

#alert-log li {
  padding: 6px 8px;
  margin-bottom: 4px;
  border-radius: 4px;
  border-left: 3px solid;
}

.alert-human_in_fire { background: #2a0000; border-color: #f00; color: #faa; }
.alert-flame         { background: #1a0d00; border-color: #f80; color: #fca; }
.alert-obstruction   { background: #1a1a00; border-color: #ff0; color: #ff8; }

#controls {
  background: #111;
  border-top: 1px solid #333;
  padding: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

#dpad { display: grid; grid-template-rows: auto auto auto; gap: 4px; align-items: center; justify-items: center; }
.dpad-row { display: flex; gap: 4px; }

#dpad button {
  width: 52px; height: 52px;
  background: #222;
  border: 1px solid #444;
  color: #ccc;
  font-size: 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}

#dpad button:active,
#dpad button.pressed { background: #444; }

.hint { font-size: 0.7rem; color: #555; }
```

- [ ] **Step 3: Write app.js**

Create `frontend/app.js`:
```javascript
const ws = new WebSocket(`ws://${location.host}/ws`);
const alertLog = document.getElementById('alert-log');
const videoWrapper = document.getElementById('video-wrapper');
const statusCam = document.getElementById('status-cam');
const statusBt  = document.getElementById('status-bt');
const statusGpu = document.getElementById('status-gpu');

const ALERT_ICONS = {
  human_in_fire: '⚠ Human in fire zone',
  flame:         '🔥 Flame detected',
  obstruction:   '🟡 Obstruction ahead',
};

let audioCtx = null;
let userInteracted = false;
document.addEventListener('click', () => { userInteracted = true; }, { once: true });

function beep(freq = 880, duration = 0.2) {
  if (!userInteracted) return;
  if (!audioCtx) audioCtx = new AudioContext();
  const osc = audioCtx.createOscillator();
  const gain = audioCtx.createGain();
  osc.connect(gain);
  gain.connect(audioCtx.destination);
  osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.3, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + duration);
  osc.start();
  osc.stop(audioCtx.currentTime + duration);
}

function addAlert(type, conf) {
  const li = document.createElement('li');
  li.className = `alert-${type}`;
  const text = ALERT_ICONS[type] || type;
  const time = new Date().toLocaleTimeString();
  li.textContent = `${text} (${Math.round(conf * 100)}%) — ${time}`;
  alertLog.prepend(li);

  // Cap log at 50 entries
  while (alertLog.children.length > 50) alertLog.removeChild(alertLog.lastChild);

  // Visual border effect
  videoWrapper.className = type === 'human_in_fire' ? 'alert-human' : type === 'flame' ? 'alert-fire' : '';
  if (type !== 'obstruction') beep(type === 'human_in_fire' ? 1200 : 880);
  setTimeout(() => { videoWrapper.className = ''; }, 2000);
}

function updateStatus(data) {
  setStatus(statusCam, data.camera, 'CAM');
  setStatus(statusBt,  data.bluetooth, 'BT');
  statusGpu.textContent = `MODE: ${data.gpu ? 'GPU' : 'CPU'}`;
  statusGpu.className = 'status-badge ok';
}

function setStatus(el, ok, label) {
  el.textContent = `${label}: ${ok ? 'OK' : 'OFF'}`;
  el.className = `status-badge ${ok ? 'ok' : 'fail'}`;
}

ws.onmessage = (ev) => {
  const data = JSON.parse(ev.data);
  if (data.event === 'alert') addAlert(data.type, data.conf);
  if (data.event === 'status') updateStatus(data);
};

ws.onclose = () => setStatus(statusCam, false, 'CAM');

function sendCmd(cmd) { if (ws.readyState === 1) ws.send(JSON.stringify({ cmd })); }

// Button controls
document.querySelectorAll('#dpad button').forEach(btn => {
  btn.addEventListener('mousedown', () => { btn.classList.add('pressed'); sendCmd(btn.dataset.cmd); });
  btn.addEventListener('mouseup',   () => { btn.classList.remove('pressed'); sendCmd('S'); });
  btn.addEventListener('mouseleave',() => { btn.classList.remove('pressed'); sendCmd('S'); });
});

// Keyboard controls
const KEY_MAP = { KeyW: 'F', ArrowUp: 'F', KeyS: 'B', ArrowDown: 'B',
                  KeyA: 'L', ArrowLeft: 'L', KeyD: 'R', ArrowRight: 'R', Space: 'S' };
const held = new Set();
document.addEventListener('keydown', e => {
  const cmd = KEY_MAP[e.code];
  if (cmd && !held.has(e.code)) { held.add(e.code); sendCmd(cmd); e.preventDefault(); }
});
document.addEventListener('keyup', e => {
  if (KEY_MAP[e.code]) { held.delete(e.code); sendCmd('S'); }
});
```

- [ ] **Step 4: Run full stack and verify dashboard**

```bash
cd fire-rescue-rc/backend
.venv\Scripts\activate
python main.py
```

Open `http://localhost:8000` in browser. Verify:
- Video feed shows (webcam or ESP32)
- Status bar shows camera/BT/mode
- WASD keys send commands (check terminal for `[car_control]` logs)
- Buttons work on click
- Move something in front of camera — alerts appear in panel

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: web dashboard with live feed, alert panel, WASD car controls"
```

---

## Task 9: Integration Smoke Test

- [ ] **Step 1: Run all unit tests**

```bash
cd fire-rescue-rc
backend\.venv\Scripts\activate
pytest tests/ -v
```

Expected: all tests pass (`test_stream`, `test_detection`, `test_car_control`).

- [ ] **Step 2: Test with webcam (no hardware needed)**

In `backend/.env`, set `WEBCAM_FALLBACK=true`.

```bash
python backend/main.py
```

Open `http://localhost:8000`. Verify:
- Webcam stream shows in browser
- Detection boxes appear when person/fire detected
- Alert log populates
- WASD sends commands (BT may show disconnected — that's fine)

- [ ] **Step 3: Test with ESP32-Cam (hardware required)**

Set `ESP32_IP` in `.env` to your ESP32's IP from Task 3.
Set `WEBCAM_FALLBACK=false`.

```bash
python backend/main.py
```

Verify ESP32 stream replaces webcam in dashboard.

- [ ] **Step 4: Test car control (hardware required)**

Pair HC-05 in Windows Bluetooth settings (PIN: 1234).
Note COM port assigned. Set `BT_PORT=COMx` in `.env`.

```bash
python backend/main.py
```

Status bar should show `BT: OK`. Press W — car should move forward. Press S — car stops.

- [ ] **Step 5: Final commit**

```bash
git add tests/
git commit -m "test: integration smoke test instructions"
```

---

## Quick Reference

### Run backend
```bash
cd fire-rescue-rc/backend
.venv\Scripts\activate
python main.py
# Dashboard: http://localhost:8000
```

### Run tests
```bash
pytest tests/ -v
```

### Car commands
| Key | Command | Action |
|-----|---------|--------|
| W / ↑ | F | Forward |
| S / ↓ | B | Backward |
| A / ← | L | Left |
| D / → | R | Right |
| Space | S | Stop |

### .env variables
| Variable | Default | Description |
|----------|---------|-------------|
| `ESP32_IP` | `192.168.1.100` | ESP32-Cam IP from Serial Monitor |
| `BT_PORT` | auto-detect | HC-05 COM port (e.g. `COM5`) |
| `MODEL_SIZE` | `auto` | `auto` / `nano` / `small` |
| `WEBCAM_FALLBACK` | `false` | Use laptop webcam if ESP32 unavailable |
