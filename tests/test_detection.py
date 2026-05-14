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
