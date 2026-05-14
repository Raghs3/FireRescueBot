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
    mock_serial.is_open = True
    with patch('car_control.serial.Serial', return_value=mock_serial):
        ctrl = CarControl(port='COM99')
        ctrl.connect()
    assert ctrl.is_connected is True
