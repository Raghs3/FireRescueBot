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
