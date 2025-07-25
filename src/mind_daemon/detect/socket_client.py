"""Socket communication with main system - placeholder."""

import socket

class SocketClient:
    """Handles socket communication between detection module and main system."""
    
    def __init__(self, host: str = "localhost", port: int = 8080):
        self.host = host
        self.port = port
        self.socket = None
        
    def connect(self):
        """Connect to main system via socket."""
        pass
        
    def send_gesture(self, gesture: str):
        """Send detected gesture to main system."""
        pass
        
    def disconnect(self):
        """Disconnect from main system."""
        pass