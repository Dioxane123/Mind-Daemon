"""
Environment State Management System
Manages global state for light, music, and curtain systems
"""

import json
import threading
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class LightState:
    """Light system state"""
    is_on: bool = True
    color_hex: str = "#FF5733"
    lightness: int = 50  # 0-100
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MusicState:
    """Music system state"""
    is_playing: bool = True
    name: str = "Aria De Capo"
    type: str = "Relaxing"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CurtainState:
    """Curtain system state"""
    state: int = 0  # 0: open, 1: close
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScoreState:
    """Score system state"""
    At: int = 50  # Attention
    Ex: int = 50  # Excitement
    Re: int = 50  # Relaxation
    St: int = 50  # Stress
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EnvironmentStateManager:
    """
    Global environment state manager
    Thread-safe singleton for managing environment states
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._state_lock = threading.Lock()
        self.light = LightState()
        self.music = MusicState()
        self.curtain = CurtainState()
        self.scores = ScoreState()
        self._initialized = True
    
    def update_light_state(self, is_on: Optional[bool] = None, color_hex: Optional[str] = None, lightness: Optional[int] = None):
        """Update light state"""
        with self._state_lock:
            if is_on is not None:
                self.light.is_on = is_on
            if color_hex is not None:
                self.light.color_hex = color_hex
            if lightness is not None:
                self.light.lightness = max(0, min(100, lightness))
    
    def update_music_state(self, is_playing: Optional[bool] = None, name: Optional[str] = None, type_: Optional[str] = None):
        """Update music state"""
        with self._state_lock:
            if is_playing is not None:
                self.music.is_playing = is_playing
            if name is not None:
                self.music.name = name
            if type_ is not None:
                self.music.type = type_
    
    def update_curtain_state(self, state: Optional[int] = None):
        """Update curtain state"""
        with self._state_lock:
            if state is not None:
                self.curtain.state = state
    
    def update_scores(self, At: Optional[int] = None, Ex: Optional[int] = None, Re: Optional[int] = None, St: Optional[int] = None):
        """Update score state"""
        with self._state_lock:
            if At is not None:
                self.scores.At = max(0, min(100, At))
            if Ex is not None:
                self.scores.Ex = max(0, min(100, Ex))
            if Re is not None:
                self.scores.Re = max(0, min(100, Re))
            if St is not None:
                self.scores.St = max(0, min(100, St))
    
    def get_basic_params(self) -> Dict[str, Any]:
        """Get current basic parameters for socket transmission"""
        with self._state_lock:
            return {
                "light": self.light.to_dict(),
                "music": self.music.to_dict(),
                "curtain": self.curtain.to_dict(),
                "Scores": self.scores.to_dict()
            }
    
    def get_json_params(self) -> str:
        """Get basic parameters as JSON string"""
        return json.dumps(self.get_basic_params(), indent=2)


# Global instance
env_state = EnvironmentStateManager()


if __name__ == "__main__":
    # Test the environment state manager
    env_state.update_light_state(is_on=True, color_hex="#00FF00", lightness=75)
    env_state.update_music_state(is_playing=False, name="Test Song", type_="Classical")
    env_state.update_curtain_state(state=1)
    env_state.update_scores(At=60, Ex=40, Re=70, St=30)
    
    print("Basic Parameters:")
    print(env_state.get_json_params())