"""Detection module for gesture recognition."""

from .gesture_detector import GestureDetector
from .socket_client import SocketClient

__all__ = ["GestureDetector", "SocketClient"]