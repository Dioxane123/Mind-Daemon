"""
BCI Real-time Data Service

Integrates Emotiv Cortex API with real-time data processing and score calculation.
Provides a unified interface for BCI data collection and analysis.
"""

import asyncio
import json
import threading
import time
from typing import Dict, Any, Optional, Callable, List
from collections import deque
from datetime import datetime
import logging

from .cortex import Cortex
from .sub_data import Subcribe
from .data_store import AveragingLogger
from ..utils.config import config
# Note: Using env_state from data_process until state_manager is fully integrated
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data_process'))
try:
    from env_state import EnvironmentStateManager
except ImportError:
    # Fallback to a simple state manager
    class EnvironmentStateManager:
        def __init__(self):
            self.scores = {"At": 50, "Ex": 50, "Re": 50, "St": 50}
        def update_scores(self, **kwargs):
            self.scores.update({k: v for k, v in kwargs.items() if k in self.scores})
        def get_basic_params(self):
            return {
                "light": {"is_on": True, "color_hex": "#FFFFFF", "lightness": 50},
                "music": {"is_playing": True, "name": "Default", "type": "Relaxing"},
                "curtain": {"state": 0},
                "Scores": self.scores
            }

logger = logging.getLogger(__name__)

class ScoreCalculator:
    """
    Calculates cognitive scores from BCI performance metrics (met) data stream
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
                engagement = met_data[1] * 100  # 'eng' - relates to attention
                excitement = met_data[3] * 100  # 'exc' - excitement/arousal
                stress = met_data[6] * 100      # 'str' - stress level
                relaxation = met_data[8] * 100  # 'rel' - relaxation
                
                # Clamp values to 0-100 range
                self.latest_scores = {
                    "At": max(0, min(100, int(engagement))),      # Attention
                    "Ex": max(0, min(100, int(excitement))),      # Excitement  
                    "Re": max(0, min(100, int(relaxation))),      # Relaxation
                    "St": max(0, min(100, int(stress)))           # Stress
                }
        except (IndexError, TypeError) as e:
            logger.warning(f"Error processing met data: {e}")
    
    def get_current_scores(self) -> Dict[str, int]:
        """Get current cognitive scores"""
        with self.buffer_lock:
            return self.latest_scores.copy()

class BCIRealtimeService:
    """
    Real-time BCI data processing service
    
    Combines Emotiv Cortex API data collection with real-time score calculation
    and state management for the Mind Daemon system.
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        Initialize BCI service
        
        Args:
            client_id: Emotiv client ID (from config if None)
            client_secret: Emotiv client secret (from config if None)
        """
        # Configuration
        self.client_id = client_id or config.get('EMOTIV_CLIENT_ID')
        self.client_secret = client_secret or config.get('EMOTIV_CLIENT_SECRET')
        self.dev_mode = config.get('DEV_MODE')
        self.enable_logging = config.get('ENABLE_DATA_LOGGING')
        
        # Data processing components
        self.score_calculator = ScoreCalculator()
        self.environment_state = EnvironmentStateManager()
        
        # BCI components (initialized when needed)
        self.cortex_client: Optional[Cortex] = None
        self.data_logger: Optional[AveragingLogger] = None
        self.subscriber: Optional[Subcribe] = None
        
        # Service state
        self.is_running = False
        self.service_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        
        # Callbacks
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        logger.info(f"BCI实时服务初始化完成 - Dev模式: {self.dev_mode}")
    
    def add_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Add callback function for data updates"""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove data callback"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def _notify_callbacks(self, data: Dict[str, Any]):
        """Notify all registered callbacks with new data"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback notification error: {e}")
    
    def start_service(self):
        """Start the BCI data collection service"""
        if self.is_running:
            logger.warning("BCI服务已在运行")
            return
        
        if self.dev_mode:
            logger.info("开发模式：使用模拟BCI数据")
            self._start_dev_mode()
        else:
            logger.info("生产模式：连接Emotiv BCI设备")
            self._start_production_mode()
        
        self.is_running = True
        logger.info("BCI实时服务已启动")
    
    def stop_service(self):
        """Stop the BCI data collection service"""
        if not self.is_running:
            return
        
        self.stop_event.set()
        self.is_running = False
        
        # Clean up components
        if self.data_logger:
            try:
                self.data_logger.stop_event.set()
            except Exception as e:
                logger.error(f"停止数据记录器失败: {e}")
        
        if self.service_thread and self.service_thread.is_alive():
            self.service_thread.join(timeout=3)
        
        logger.info("BCI实时服务已停止")
    
    def _start_dev_mode(self):
        """Start service in development mode with simulated data"""
        self.service_thread = threading.Thread(target=self._dev_mode_loop, daemon=True)
        self.service_thread.start()
    
    def _start_production_mode(self):
        """Start service in production mode with real BCI data"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Emotiv API credentials not configured")
        
        try:
            # Initialize BCI components
            self.cortex_client = Cortex(self.client_id, self.client_secret)
            
            # Initialize data logger if enabled
            if self.enable_logging:
                rolling_window = config.get('ROLLING_WINDOW_SIZE') if config.get('ROLLING_WINDOW_SIZE') > 0 else None
                self.data_logger = AveragingLogger(
                    self.client_id, 
                    self.client_secret,
                    interval_sec=5,
                    rolling_window_size=rolling_window
                )
            
            # Start production mode service
            self.service_thread = threading.Thread(target=self._production_mode_loop, daemon=True)
            self.service_thread.start()
            
        except Exception as e:
            logger.error(f"初始化BCI组件失败: {e}")
            raise
    
    def _dev_mode_loop(self):
        """Development mode data generation loop"""
        import random
        
        while not self.stop_event.is_set():
            try:
                # Generate simulated BCI data
                simulated_met_data = [
                    1,  # eng.isActive
                    random.uniform(0.3, 0.8),  # eng (engagement/attention)
                    1,  # exc.isActive  
                    random.uniform(0.2, 0.7),  # exc (excitement)
                    random.uniform(0.0, 1.0),  # lex
                    1,  # str.isActive
                    random.uniform(0.1, 0.6),  # str (stress)
                    1,  # rel.isActive
                    random.uniform(0.4, 0.9),  # rel (relaxation)
                    1,  # int.isActive
                    random.uniform(0.3, 0.8),  # int (interest)
                    1,  # foc.isActive
                    random.uniform(0.4, 0.8),  # foc (focus)
                ]
                
                # Update score calculator
                self.score_calculator.add_met_data(simulated_met_data)
                scores = self.score_calculator.get_current_scores()
                
                # Update environment state
                self.environment_state.update_scores(**scores)
                
                # Create data package
                data_package = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'dev_mode',
                    'scores': scores,
                    'basic_params': self.environment_state.get_basic_params()
                }
                
                # Notify callbacks
                self._notify_callbacks(data_package)
                
                # Log data
                logger.debug(f"模拟BCI数据: At={scores['At']} Ex={scores['Ex']} Re={scores['Re']} St={scores['St']}")
                
                time.sleep(1)  # 1 Hz update rate
                
            except Exception as e:
                logger.error(f"开发模式数据生成错误: {e}")
                time.sleep(1)
    
    def _production_mode_loop(self):
        """Production mode BCI data processing loop"""
        # This would integrate with the actual Cortex API data streams
        # For now, we'll use the existing subscriber pattern
        try:
            if self.data_logger:
                # The data logger will handle the actual BCI data collection
                # We'll monitor its data and extract scores
                while not self.stop_event.is_set():
                    # In a real implementation, this would process actual BCI data
                    # For now, we'll periodically check for data updates
                    time.sleep(1)
            else:
                logger.warning("生产模式但未启用数据记录，使用开发模式")
                self._dev_mode_loop()
                
        except Exception as e:
            logger.error(f"生产模式错误: {e}")
            # Fallback to dev mode
            self._dev_mode_loop()
    
    def get_current_data(self) -> Dict[str, Any]:
        """Get current BCI data and scores"""
        scores = self.score_calculator.get_current_scores()
        basic_params = self.environment_state.get_basic_params()
        
        return {
            'timestamp': datetime.now().isoformat(),
            'is_running': self.is_running,
            'dev_mode': self.dev_mode,
            'scores': scores,
            'basic_params': basic_params
        }
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'is_running': self.is_running,
            'dev_mode': self.dev_mode,
            'has_credentials': bool(self.client_id and self.client_secret),
            'logging_enabled': self.enable_logging,
            'callbacks_registered': len(self.data_callbacks)
        }

# Global BCI service instance
_bci_service_instance: Optional[BCIRealtimeService] = None

def get_bci_service() -> BCIRealtimeService:
    """Get global BCI service instance"""
    global _bci_service_instance
    if _bci_service_instance is None:
        _bci_service_instance = BCIRealtimeService()
    return _bci_service_instance

if __name__ == "__main__":
    # Test the BCI service
    service = BCIRealtimeService()
    
    def data_callback(data):
        print(f"Received data: {data['scores']}")
    
    service.add_data_callback(data_callback)
    
    try:
        service.start_service()
        time.sleep(10)  # Run for 10 seconds
    except KeyboardInterrupt:
        print("Stopping service...")
    finally:
        service.stop_service()