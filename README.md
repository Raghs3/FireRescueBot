# Fire Rescue RC Car

An RC car with an ESP32-Cam that streams live video to a laptop. YOLOv8 detects flames and humans in real time. A web dashboard shows the annotated feed, logs alerts, and lets you drive the car via WASD over Bluetooth.

---

## Demo

```
[ESP32-Cam] --WiFi MJPEG--> [Laptop: YOLOv8 detection]
                                      |
                              Web Dashboard (localhost:8000)
                              - Live annotated video
                              - Alert log (fire / human / obstruction)
                              - WASD car controls
                                      |
                    [BT Serial] --> [Arduino + HW-130] --> Motors
```

---

## Hardware Required

| Part | Role |
|------|------|
| Arduino Uno | Motor controller |
| HW-130 Motor Driver Shield | Drives 4x DC motors |
| HC-05 Bluetooth Module | Receives drive commands from laptop |
| HC-SR04 Ultrasonic Sensor | Emergency stop (<12 cm) |
| ESP32-Cam (AI-Thinker) | WiFi video stream |
| Laptop | Runs detection + dashboard |

No additional hardware purchases needed beyond what's listed above.

---

## Detection

| Target | Method | Training needed? |
|--------|--------|-----------------|
| Human | YOLOv8 COCO pretrained (`person` class) | None |
| Fire/Flame | YOLOv8 fine-tuned on fire dataset (auto-downloaded) | None |
| Obstruction | Box size + position heuristic | None |

Models download automatically on first run (~30 MB total, cached in `backend/models/`).

---

## Project Structure

```
fire-rescue-rc/
├── arduino/
│   └── rc_car/rc_car.ino           # Flash to Arduino Uno
├── esp32cam/
│   └── esp32cam_stream/
│       ├── esp32cam_stream.ino     # Flash to ESP32-Cam
│       └── config.h                # WiFi credentials (you create this)
├── backend/
│   ├── main.py                     # FastAPI server
│   ├── stream.py                   # ESP32 frame consumer
│   ├── detection.py                # YOLOv8 inference + alerts
│   ├── car_control.py              # Bluetooth serial
│   ├── requirements.txt
│   └── .env.example                # Copy to .env and fill in
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── tests/                          # 13 unit tests
```

---

## Setup

### 1. Arduino

Install [AFMotor library](https://github.com/adafruit/Adafruit-Motor-Shield-library) in Arduino IDE:
> Sketch → Include Library → Manage Libraries → search "AFMotor"

Flash `arduino/rc_car/rc_car.ino`:
- Board: Arduino Uno
- Port: your Arduino COM port

Test via Serial Monitor (9600 baud): send `F` → forward, `S` → stop.

### 2. ESP32-Cam

Add ESP32 board package to Arduino IDE:
> File → Preferences → Additional Board URLs:
> `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
> Then: Tools → Board Manager → search "esp32" → install

Create `esp32cam/esp32cam_stream/config.h`:
```cpp
#define WIFI_SSID "YourNetworkName"
#define WIFI_PASSWORD "YourPassword"
```

Flash `esp32cam_stream.ino`:
- Board: AI Thinker ESP32-CAM
- **Hold IO0 to GND during upload, release when upload starts**
- After upload: press RST, open Serial Monitor at 115200 baud
- Note the printed IP: `Stream URL: http://192.168.X.X/stream`

### 3. Bluetooth (HC-05)

Pair HC-05 in Windows Bluetooth settings — PIN: `1234` (or `0000`).
Note the COM port assigned (e.g. COM5).

### 4. Python Backend

```bash
cd fire-rescue-rc/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy and edit `.env`:
```bash
copy .env.example .env
```

```env
ESP32_IP=192.168.X.X      # from ESP32 Serial Monitor
BT_PORT=COM5              # HC-05 COM port (leave blank to auto-detect)
MODEL_SIZE=auto           # auto / nano / small
WEBCAM_FALLBACK=false     # set true to test without ESP32
```

### 5. Run

```bash
cd fire-rescue-rc/backend
.venv\Scripts\activate
python main.py
```

Open **http://localhost:8000**

---

## Dashboard

```
┌─────────────────────────────────────────────────────┐
│  CAM: OK   BT: OK   MODE: CPU          Fire Rescue RC│
├──────────────────────────────┬──────────────────────┤
│                              │  ALERTS              │
│   [Live video feed]          │  ─────────────────── │
│                              │  ⚠ Human in fire     │
│  ┌──────────┐  ┌──────────┐  │  🔥 Flame detected   │
│  │  Person  │  │  Fire    │  │  🟡 Obstruction      │
│  │  94%     │  │  87%     │  │                      │
│  └──────────┘  └──────────┘  │                      │
├──────────────────────────────┴──────────────────────┤
│      [▲]   [◄] [■] [►]   [▼]    WASD / arrows      │
└─────────────────────────────────────────────────────┘
```

**Car controls:** WASD or arrow keys. Release to stop. On-screen buttons also work.

**Alerts:**
- Red pulsing border + beep (1200 Hz) → human detected in fire zone
- Orange border + beep (880 Hz) → flame detected
- Yellow border, silent → obstruction ahead

---

## Car Commands

| Key | Action |
|-----|--------|
| W / ↑ | Forward |
| S / ↓ | Backward |
| A / ← | Left |
| D / → | Right |
| Space | Stop |

---

## Testing (no hardware needed)

Set `WEBCAM_FALLBACK=true` in `.env`, then run the backend. Your laptop webcam acts as the video source.

Run unit tests:
```bash
"backend/.venv/Scripts/python.exe" -m pytest tests/ -v
```

Expected: **13 passed**

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ESP32_IP` | `192.168.1.100` | IP of ESP32-Cam (from Serial Monitor) |
| `BT_PORT` | auto-detect | HC-05 COM port (e.g. `COM5`) |
| `MODEL_SIZE` | `auto` | `auto` (GPU→small, CPU→nano), `nano`, `small` |
| `WEBCAM_FALLBACK` | `false` | Use laptop webcam if ESP32 unavailable |

---

## Troubleshooting

**Stream not loading:**
- Check ESP32 is on same WiFi network as laptop
- Verify IP in `.env` matches Serial Monitor output
- Try opening `http://<ESP32_IP>/stream` directly in browser

**BT not connecting:**
- Pair HC-05 first in Windows Bluetooth (Settings → Add Device)
- Set `BT_PORT=COMx` explicitly if auto-detect fails
- Check Arduino is powered and HC-05 LED is blinking

**Detection slow:**
- On CPU: expected ~8–12 FPS with yolov8n — normal
- Set `MODEL_SIZE=nano` to force lightest model
- Close other heavy applications

**Models not downloading:**
- Ensure internet connection on first run
- Check `backend/models/` is writable
- Fire model: `keremberke/yolov8n-fire-detection` on HuggingFace
