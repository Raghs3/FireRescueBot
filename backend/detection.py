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

    # Flame only (no nearby person)
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
        self.fire_model = None
        if not fire_model_path.exists():
            print("[detection] Downloading fire detection model...")
            hf_token = os.getenv('HF_TOKEN') or None
            _HF_REPOS = [
                ('TommyNgx/YOLOv10-Fire-and-Smoke-Detection', 'best.pt'),
                ('pyronear/yolov8s', 'model.pt'),
                ('keremberke/yolov8n-fire-detection', 'best.pt'),
            ]
            downloaded = None
            for repo_id, filename in _HF_REPOS:
                try:
                    downloaded = hf_hub_download(repo_id=repo_id, filename=filename, token=hf_token)
                    break
                except Exception as e:
                    print(f"[detection] {repo_id} unavailable: {e}")
            if downloaded:
                import shutil
                shutil.copy(downloaded, fire_model_path)
            else:
                print("[detection] WARNING: fire model unavailable — fire detection disabled")

        if fire_model_path.exists():
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

        if self.fire_model is not None:
            fire_results = self.fire_model(frame, verbose=False)[0]
            for box in fire_results.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                detections.append(Detection('fire', x1, y1, x2, y2, float(box.conf[0])))

        alerts = classify_alerts(detections, w, h)
        annotated = _draw_boxes(frame, detections, alerts)
        return annotated, alerts
