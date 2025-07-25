"""
Socket Interface for Real-time Basic Parameters Transmission
Integrates with sub_data_store to get score data and sends basic_params via socket
"""

import socket
import json
import threading
import time
from typing import Dict, Any
from collections import deque

from env_state import env_state
from sub_data_store import AveragingLogger


class ScoreCalculator:
    """
    Calculates scores from BCI performance metrics (met) data stream
    Directly uses the met data which contains performance metrics
    """
    
    def __init__(self):
        self.met_buffer = deque(maxlen=10)  # Store last 10 met data points for averaging
        self.pow_buffer = deque(maxlen=10)  # Store last 10 power data points 
        self.buffer_lock = threading.Lock()
        self.latest_scores = {"At": 50, "Ex": 50, "Re": 50, "St": 50}
    
    def add_met_data(self, met_data):
        """Add performance metrics data point"""
        with self.buffer_lock:
            self.met_buffer.append(met_data)
            # Update scores immediately when new met data arrives
            self._update_scores_from_met(met_data)
    
    def add_pow_data(self, pow_data):
        """Add power data point"""
        with self.buffer_lock:
            self.pow_buffer.append(pow_data)
    
    def _update_scores_from_met(self, met_data):
        """
        Update scores from met data
        met labels: ['eng.isActive', 'eng', 'exc.isActive', 'exc', 'lex', 'str.isActive', 'str', 'rel.isActive', 'rel', 'int.isActive', 'int', 'foc.isActive', 'foc']
        """
        try:
            if len(met_data) >= 13:
                # Extract values from met data (convert 0-1 to 0-100)
                # Index mapping based on met labels:
                # 1: eng (engagement/attention), 3: exc (excitement), 6: str (stress), 8: rel (relaxation), 12: foc (focus)
                
                attention = int(met_data[12] * 100) if len(met_data) > 12 else 50  # foc (focus)
                excitement = int(met_data[3] * 100) if len(met_data) > 3 else 50   # exc (excitement)  
                relaxation = int(met_data[8] * 100) if len(met_data) > 8 else 50  # rel (relaxation)
                stress = int(met_data[6] * 100) if len(met_data) > 6 else 50      # str (stress)
                
                self.latest_scores = {
                    "At": max(0, min(100, attention)),
                    "Ex": max(0, min(100, excitement)),
                    "Re": max(0, min(100, relaxation)), 
                    "St": max(0, min(100, stress))
                }
        except (IndexError, TypeError, ValueError) as e:
            print(f"Error processing met data: {e}")
    
    def get_current_scores(self) -> Dict[str, int]:
        """
        Get current scores from latest met data
        Returns scores for At, Ex, Re, St (0-100)
        """
        with self.buffer_lock:
            return self.latest_scores.copy()


class SocketBasicParamsLogger(AveragingLogger):
    """
    Enhanced logger that integrates score calculation and socket transmission
    """
    
    def __init__(self, app_client_id, app_client_secret, 
                 socket_host="localhost", socket_port=8888, 
                 transmission_interval=1.0, **kwargs):
        # Initialize with 1-second interval for score calculation
        super().__init__(app_client_id, app_client_secret, 
                        interval_sec=int(transmission_interval), 
                        rolling_window_size=3, **kwargs)
        
        self.socket_host = socket_host
        self.socket_port = socket_port
        self.transmission_interval = transmission_interval
        
        # Score calculator
        self.score_calculator = ScoreCalculator()
        
        # Socket setup
        self.socket = None
        self.socket_connected = False
        self.socket_lock = threading.Lock()
        
        # Transmission thread
        self.transmission_stop_event = threading.Event()
        self.transmission_thread = threading.Thread(target=self._transmission_loop)
        self.transmission_thread.daemon = True
        
        # Initialize socket connection
        self._init_socket()
        
        # Start transmission
        self.transmission_thread.start()
    
    def _init_socket(self):
        """Initialize socket connection"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.socket_host, self.socket_port))
            self.socket_connected = True
            print(f"Socket connected to {self.socket_host}:{self.socket_port}")
        except Exception as e:
            print(f"Socket connection failed: {e}")
            self.socket_connected = False
    
    def _reconnect_socket(self):
        """Attempt to reconnect socket"""
        try:
            if self.socket:
                self.socket.close()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.socket_host, self.socket_port))
            self.socket_connected = True
            print("Socket reconnected successfully")
        except Exception as e:
            print(f"Socket reconnection failed: {e}")
            self.socket_connected = False
    
    def on_new_met_data(self, *args, **kwargs):
        """Override to add score calculation from performance metrics"""
        super().on_new_met_data(*args, **kwargs)
        # Add to score calculator
        data = kwargs.get('data')
        if data and 'met' in data:
            self.score_calculator.add_met_data(data['met'])
    
    def on_new_pow_data(self, *args, **kwargs):
        """Override to add power data"""
        super().on_new_pow_data(*args, **kwargs)
        # Add to score calculator
        data = kwargs.get('data')
        if data and 'pow' in data:
            self.score_calculator.add_pow_data(data['pow'])
    
    def _transmission_loop(self):
        """Main transmission loop - sends basic_params every second"""
        while not self.transmission_stop_event.is_set():
            try:
                # Get current scores from met data
                scores = self.score_calculator.get_current_scores()
                
                # Update environment state with new scores
                env_state.update_scores(**scores)
                
                # Get basic parameters
                basic_params = env_state.get_basic_params()
                
                # Send via socket
                self._send_basic_params(basic_params)
                
                # Wait for next transmission
                self.transmission_stop_event.wait(self.transmission_interval)
                
            except Exception as e:
                print(f"Error in transmission loop: {e}")
                time.sleep(1)
    
    def _send_basic_params(self, params: Dict[str, Any]):
        """Send basic parameters via socket"""
        with self.socket_lock:
            if not self.socket_connected:
                self._reconnect_socket()
            
            if self.socket_connected and self.socket:
                try:
                    # Convert to JSON and send
                    json_data = json.dumps(params)
                    message = f"{json_data}\n"
                    self.socket.sendall(message.encode('utf-8'))
                    print(f"Sent: {json_data}")
                except Exception as e:
                    print(f"Socket send error: {e}")
                    self.socket_connected = False
    
    def close(self):
        """Override close to handle socket and transmission thread"""
        print("Closing socket interface...")
        
        # Stop transmission thread
        self.transmission_stop_event.set()
        if self.transmission_thread.is_alive():
            self.transmission_thread.join(timeout=2)
        
        # Close socket
        with self.socket_lock:
            if self.socket:
                try:
                    self.socket.close()
                except:
                    pass
                self.socket = None
                self.socket_connected = False
        
        # Call parent close
        super().close()
        print("Socket interface closed.")


def main():
    """Main function to start the socket interface"""
    your_app_client_id = '0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO'
    your_app_client_secret = 'ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860'
    
    # Create socket interface with 1-second transmission interval
    socket_logger = SocketBasicParamsLogger(
        your_app_client_id, 
        your_app_client_secret,
        socket_host="localhost",
        socket_port=8888,
        transmission_interval=1.0
    )
    
    # Start data streams  
    streams = ['met', 'pow']
    socket_logger.start(streams)
    
    try:
        print("Socket interface running. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        socket_logger.close()


if __name__ == "__main__":
    main()