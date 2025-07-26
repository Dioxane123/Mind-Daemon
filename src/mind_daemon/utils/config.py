"""
Mind Daemon Configuration Management

Handles loading and managing configuration from .env files and environment variables.
"""

import os
from typing import Dict, Any, Optional, Union
from pathlib import Path
import logging

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False
    logging.warning("python-dotenv not installed. Environment variables will only be read from system.")

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for Mind Daemon"""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            env_file: Path to .env file. If None, searches for .env in project root.
        """
        self._config: Dict[str, Any] = {}
        self._load_env_file(env_file)
        self._setup_defaults()
    
    def _load_env_file(self, env_file: Optional[str] = None):
        """Load environment variables from .env file"""
        if not HAS_DOTENV:
            logger.warning("python-dotenv not available, skipping .env file loading")
            return
        
        if env_file is None:
            # Search for .env file in project root
            project_root = Path(__file__).parent.parent.parent.parent
            env_file = project_root / ".env"
        
        env_path = Path(env_file)
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded environment from {env_path}")
        else:
            logger.info(f".env file not found at {env_path}, using system environment variables only")
    
    def _setup_defaults(self):
        """Setup default configuration values"""
        # Get project root directory
        project_root = Path(__file__).parent.parent.parent.parent
        
        self._defaults = {
            # BCI Configuration
            'EMOTIV_CLIENT_ID': '',
            'EMOTIV_CLIENT_SECRET': '',
            'BCI_DEVICE_TYPE': 'emotiv',
            'BCI_SAMPLING_RATE': 128,
            'BCI_CHANNELS': 14,
            
            # LLM Configuration
            'MINIMAX_API_KEY': '',
            'MINIMAX_BASE_URL': 'https://api.minimaxi.com/v1/text/chatcompletion_v2',
            'MINIMAX_MODEL': 'MiniMax-Text-01',
            'MINIMAX_GROUP_ID': '',
            'OPENAI_API_KEY': '',
            'OPENAI_MODEL': 'gpt-3.5-turbo',
            
            # System Paths
            'MUSIC_DIR': str(project_root / 'music'),
            'WINDOW_PY_PATH': str(project_root / 'src' / 'mind_daemon' / 'peripheral' / 'window.py'),
            'DATA_DIR': str(project_root / 'data'),
            
            # Server Configuration
            'WEBSOCKET_HOST': 'localhost',
            'WEBSOCKET_PORT': 8889,
            'TCP_HOST': 'localhost',
            'TCP_PORT': 8888,
            
            # System Behavior
            'STATE_ANALYSIS_INTERVAL': 1.0,
            'LLM_ANALYSIS_INTERVAL': 300.0,
            'ENVIRONMENT_CONTROL_INTERVAL': 10.0,
            
            # Thresholds
            'ATTENTION_THRESHOLD': 0.6,
            'STRESS_THRESHOLD': 0.7,
            'FATIGUE_THRESHOLD': 0.8,
            'RELAXATION_THRESHOLD': 0.5,
            
            # Music Player
            'MUSIC_VOLUME': 0.6,
            'MUSIC_SWITCH_COOLDOWN': 60,
            
            # Halo Controller
            'HALO_ACTIVATION_COOLDOWN': 30,
            'HALO_COLOR_CHANGE_COOLDOWN': 15,
            
            # Development
            'LOG_LEVEL': 'INFO',
            'DEV_MODE': False,
            'VERBOSE': False,
            'ENABLE_DATA_LOGGING': True,
            'ROLLING_WINDOW_SIZE': 100
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        # First check if already cached
        if key in self._config:
            return self._config[key]
        
        # Then check environment variables
        env_value = os.getenv(key)
        if env_value is not None:
            # Convert string values to appropriate types
            value = self._convert_type(env_value, key)
            self._config[key] = value
            return value
        
        # Then check defaults
        if key in self._defaults:
            value = self._defaults[key]
            self._config[key] = value
            return value
        
        # Finally return provided default
        return default
    
    def _convert_type(self, value: str, key: str) -> Any:
        """Convert string environment variable to appropriate type"""
        # Boolean values
        if key in ['DEV_MODE', 'VERBOSE', 'ENABLE_DATA_LOGGING']:
            return value.lower() in ('true', '1', 'yes', 'on')
        
        # Integer values
        if key in ['BCI_SAMPLING_RATE', 'BCI_CHANNELS', 'WEBSOCKET_PORT', 'TCP_PORT', 
                   'MUSIC_SWITCH_COOLDOWN', 'HALO_ACTIVATION_COOLDOWN', 'HALO_COLOR_CHANGE_COOLDOWN',
                   'ROLLING_WINDOW_SIZE']:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {key}: {value}")
                return self._defaults.get(key, 0)
        
        # Float values
        if key in ['STATE_ANALYSIS_INTERVAL', 'LLM_ANALYSIS_INTERVAL', 'ENVIRONMENT_CONTROL_INTERVAL',
                   'ATTENTION_THRESHOLD', 'STRESS_THRESHOLD', 'FATIGUE_THRESHOLD', 'RELAXATION_THRESHOLD',
                   'MUSIC_VOLUME']:
            try:
                return float(value)
            except ValueError:
                logger.warning(f"Invalid float value for {key}: {value}")
                return self._defaults.get(key, 0.0)
        
        # String values (default)
        return value
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration values"""
        result = self._defaults.copy()
        result.update(self._config)
        return result

# Global configuration instance
config = Config()