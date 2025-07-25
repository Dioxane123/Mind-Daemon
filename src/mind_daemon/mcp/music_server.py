#!/usr/bin/env python3
"""Enhanced MCP Server for Music Control with improved error handling and functionality."""

import asyncio
import json
import os
import sys
import subprocess
import random
import threading
import time
from typing import Dict, Any, Optional, List

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Resource, Tool, TextContent
import mcp.server.stdio
import mcp.types as types

class EnhancedMusicPlayer:
    """Enhanced music player with pause/resume and better error handling."""
    
    def __init__(self, music_dir: str = "music"):
        # Handle different working directory scenarios
        if not os.path.isabs(music_dir):
            # Try different relative paths based on where we might be running from
            possible_paths = [
                music_dir,  # Direct relative path
                os.path.join("..", music_dir),  # Up one level
                os.path.join("..", "..", music_dir),  # Up two levels
                os.path.join(os.path.dirname(__file__), "..", "..", "..", music_dir),  # From mcp directory
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    music_dir = os.path.abspath(path)
                    break
            else:
                # Create default music directory if none exists
                music_dir = os.path.abspath(music_dir)
                os.makedirs(music_dir, exist_ok=True)
                print(f"📁 Created music directory: {music_dir}")
        
        self.music_dir = music_dir
        self.current_process = None
        self.current_track = None
        self.paused_track = None  # Track that was paused
        self.paused_position = 0  # Position where playback was paused
        
        # Default settings
        self.volume = 0.5
        self.is_playing = False
        self.is_paused = False
        self.fade_task = None
        self.current_track_type = None  # "focus" or "relax"
        
        # Find music files with better error handling
        try:
            self.relaxation_tracks = self._find_tracks("relax")
            self.focus_tracks = self._find_tracks("focus")
        except Exception as e:
            print(f"⚠️  Error finding tracks: {e}")
            self.relaxation_tracks = []
            self.focus_tracks = []
        
        print(f"🎵 Enhanced music player initialized:")
        print(f"  Music directory: {self.music_dir}")
        print(f"  Relaxation tracks: {len(self.relaxation_tracks)}")
        print(f"  Focus tracks: {len(self.focus_tracks)}")
        
    def _find_tracks(self, mode: str) -> List[str]:
        """Find music tracks for specific mode with better error handling."""
        tracks = []
        
        if not os.path.exists(self.music_dir):
            print(f"⚠️  Music directory does not exist: {self.music_dir}")
            return tracks
            
        try:
            # Look for mode-specific tracks first
            for root, dirs, files in os.walk(self.music_dir):
                for file in files:
                    file_lower = file.lower()
                    if mode in file_lower and file_lower.endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac')):
                        tracks.append(os.path.join(root, file))
            
            # If no mode-specific tracks, look in mode-specific subdirectories
            mode_dir = os.path.join(self.music_dir, mode)
            if os.path.exists(mode_dir):
                for root, dirs, files in os.walk(mode_dir):
                    for file in files:
                        if file.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac')):
                            tracks.append(os.path.join(root, file))
            
            # If still no tracks, use any audio files as fallback
            if not tracks:
                for root, dirs, files in os.walk(self.music_dir):
                    for file in files:
                        if file.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac')):
                            tracks.append(os.path.join(root, file))
                            
        except Exception as e:
            print(f"❌ Error scanning music directory: {e}")
                    
        return tracks
    
    def _get_player_command(self, file_path: str, volume: float = None) -> List[str]:
        """Get appropriate player command with volume control based on platform and file type."""
        if volume is None:
            volume = self.volume
            
        # Convert volume (0.0-1.0) to platform-specific volume format
        if sys.platform == "darwin":  # macOS
            # afplay doesn't support volume directly, but we can set system volume
            # Store volume for later use in _play_file
            return ["afplay", file_path]
        elif sys.platform == "win32":  # Windows
            if file_path.lower().endswith('.wav'):
                return ["powershell", "-c", f"(New-Object Media.SoundPlayer '{file_path}').PlaySync()"]
            else:
                return ["start", "/min", "", file_path]
        else:  # Linux
            # Try different players in order of preference with volume support
            players = [
                ("mpv", ["mpv", f"--volume={int(volume * 100)}", "--no-video", file_path]),
                ("mplayer", ["mplayer", "-volume", str(int(volume * 100)), "-novideo", file_path]),
                ("vlc", ["vlc", "--intf", "dummy", "--volume", str(int(volume * 255)), file_path]),
                ("aplay", ["aplay", file_path] if file_path.lower().endswith('.wav') else None),
                ("mpg123", ["mpg123", "-g", str(int(volume * 100)), file_path] if file_path.lower().endswith('.mp3') else None)
            ]
            
            for player_name, cmd in players:
                if cmd is None:
                    continue
                try:
                    subprocess.run(["which", player_name], check=True, capture_output=True)
                    return cmd
                except subprocess.CalledProcessError:
                    continue
            
            # Fallback without volume control
            return ["play", file_path] if file_path.lower().endswith('.wav') else ["mpg123", file_path]
    
    def _play_file(self, file_path: str, volume: float = None) -> bool:
        """Play audio file using appropriate system player."""
        if volume is None:
            volume = self.volume
            
        try:
            # Stop current playback
            self.stop_music()
            
            # Check if file exists
            if not os.path.exists(file_path):
                print(f"❌ Audio file not found: {file_path}")
                return False
            
            # Get player command with volume control
            cmd = self._get_player_command(file_path, volume)
            
            # Set system volume for macOS (since afplay doesn't support volume)
            if sys.platform == "darwin" and volume != self.volume:
                try:
                    # Convert 0.0-1.0 to 0-100 for osascript
                    volume_percent = int(volume * 100)
                    subprocess.run([
                        "osascript", "-e", 
                        f"set volume output volume {volume_percent}"
                    ], check=True, capture_output=True)
                    print(f"🔊 Set system volume to {volume_percent}%")
                except subprocess.CalledProcessError:
                    print("⚠️ Failed to set system volume on macOS")
            
            # Start playback
            self.current_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
                preexec_fn=None if sys.platform == "win32" else os.setsid
            )
            
            self.current_track = file_path
            self.is_playing = True
            self.is_paused = False
            self.paused_track = None
            self.paused_position = 0
            
            print(f"🎵 Playing: {os.path.basename(file_path)}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to play music: {e}")
            return False
    
    def play_relaxation_music(self) -> bool:
        """Play relaxation background music."""
        if not self.relaxation_tracks:
            print("⚠️  No relaxation music files found")
            return False
            
        track = random.choice(self.relaxation_tracks)
        self.current_track_type = "relax"
        print("🧘 Playing relaxation music...")
        return self._play_file(track)
        
    def play_focus_music(self) -> bool:
        """Play focus-enhancing background music."""
        tracks = self.focus_tracks if self.focus_tracks else self.relaxation_tracks
            
        if not tracks:
            print("⚠️  No focus music files found")
            return False
            
        track = random.choice(tracks)
        self.current_track_type = "focus"
        print("🎯 Playing focus music...")
        return self._play_file(track)
    
    def pause_music(self) -> bool:
        """Pause current music playback."""
        if not self.is_playing or self.is_paused:
            return False
            
        try:
            if self.current_process and sys.platform != "win32":
                # Send SIGSTOP to pause (Unix/Linux/macOS)
                os.killpg(os.getpgid(self.current_process.pid), 19)  # SIGSTOP
                self.is_paused = True
                self.paused_track = self.current_track
                print("⏸️  Music paused")
                return True
            else:
                # For Windows or unsupported pause, stop and remember position
                self.paused_track = self.current_track
                self.stop_music()
                self.is_paused = True
                print("⏸️  Music paused (stopped)")
                return True
                
        except Exception as e:
            print(f"❌ Failed to pause music: {e}")
            return False
    
    def resume_music(self) -> bool:
        """Resume paused music playback."""
        if not self.is_paused:
            return False
            
        try:
            if self.current_process and sys.platform != "win32":
                # Send SIGCONT to resume (Unix/Linux/macOS)
                os.killpg(os.getpgid(self.current_process.pid), 18)  # SIGCONT
                self.is_paused = False
                self.is_playing = True
                print("▶️  Music resumed")
                return True
            else:
                # For Windows or when track was stopped, restart from beginning
                if self.paused_track:
                    result = self._play_file(self.paused_track)
                    if result:
                        self.is_paused = False
                        print("▶️  Music resumed (restarted)")
                    return result
                return False
                
        except Exception as e:
            print(f"❌ Failed to resume music: {e}")
            return False
    
    def skip_track(self) -> bool:
        """Skip to next track of the same type elegantly."""
        if not self.current_track_type:
            print("⚠️  No track type set, cannot skip")
            return False
            
        current_tracks = self.focus_tracks if self.current_track_type == "focus" else self.relaxation_tracks
        
        if len(current_tracks) < 2:
            print("⚠️  Not enough tracks to skip")
            return False
        
        # Find current track index
        current_index = -1
        if self.current_track:
            try:
                current_index = current_tracks.index(self.current_track)
            except ValueError:
                pass
        
        # Get next track (avoid playing the same track)
        available_tracks = [t for t in current_tracks if t != self.current_track]
        if not available_tracks:
            available_tracks = current_tracks
            
        next_track = random.choice(available_tracks)
        
        print(f"⏭️  Skipping to next {self.current_track_type} track...")
        return self._play_file(next_track)
        
    def stop_music(self):
        """Stop current music playback."""
        if self.current_process:
            try:
                if sys.platform != "win32":
                    # Kill process group to ensure all child processes are terminated
                    os.killpg(os.getpgid(self.current_process.pid), 15)  # SIGTERM
                else:
                    self.current_process.terminate()
                    
                # Non-blocking wait with timeout - don't block event loop
                try:
                    self.current_process.wait(timeout=0.1)  # Very short timeout
                except subprocess.TimeoutExpired:
                    # If still not terminated, force kill
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(self.current_process.pid), 9)  # SIGKILL
                    else:
                        self.current_process.kill()
            except:
                try:
                    if sys.platform != "win32":
                        os.killpg(os.getpgid(self.current_process.pid), 9)  # SIGKILL
                    else:
                        self.current_process.kill()
                except:
                    pass
            finally:
                self.current_process = None
                
        self.is_playing = False
        self.is_paused = False
        self.current_track = None
        
        if self.fade_task and not self.fade_task.done():
            self.fade_task.cancel()
            
        print("🔇 Music stopped")
        
    def set_volume(self, volume: float):
        """Set playback volume (0.0 to 1.0)."""
        self.volume = max(0.0, min(1.0, volume))
        print(f"🔊 Volume set to {self.volume:.2f}")
        
    async def fade_volume(self, target_volume: float, duration: float = 5.0, fade_type: str = "to"):
        """Fade volume with different types."""
        if not self.is_playing or self.is_paused:
            return False
            
        if fade_type == "out":
            target_volume = 0.0
        elif fade_type == "in":
            target_volume = min(target_volume, 1.0)
            
        print(f"🔊 Fading volume {fade_type} to {target_volume:.2f} over {duration}s")
        
        async def fade():
            steps = max(20, int(duration * 4))  # More steps for smoother fade
            step_duration = duration / steps
            start_volume = self.volume
            volume_step = (target_volume - start_volume) / steps
            
            for i in range(steps):
                if not self.is_playing or self.is_paused:
                    break
                self.volume = max(0.0, min(1.0, self.volume + volume_step))
                
                # Apply volume control to system/player in real-time
                if sys.platform == "darwin":
                    try:
                        volume_percent = int(self.volume * 100)
                        subprocess.run([
                            "osascript", "-e", 
                            f"set volume output volume {volume_percent}"
                        ], check=True, capture_output=True)
                    except subprocess.CalledProcessError:
                        pass
                
                await asyncio.sleep(step_duration)
            
            # Final volume adjustment
            self.volume = target_volume
            
            # Stop music if faded out completely
            if fade_type == "out" and target_volume == 0.0:
                self.stop_music()
                
        if self.fade_task and not self.fade_task.done():
            self.fade_task.cancel()
            try:
                await self.fade_task
            except asyncio.CancelledError:
                pass
            
        self.fade_task = asyncio.create_task(fade())
        return True
        
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive player status."""
        return {
            'is_playing': self.is_playing,
            'is_paused': self.is_paused,
            'current_track': os.path.basename(self.current_track) if self.current_track else None,
            'current_track_type': self.current_track_type,
            'paused_track': os.path.basename(self.paused_track) if self.paused_track else None,
            'volume': self.volume,
            'music_directory': self.music_dir,
            'available_relaxation_tracks': len(self.relaxation_tracks),
            'available_focus_tracks': len(self.focus_tracks),
            'platform': sys.platform
        }

# Global music player instance
music_player = None

def init_music_player():
    """Initialize music player with error handling."""
    global music_player
    if music_player is None:
        try:
            # Try to determine music directory - prioritize absolute path
            possible_dirs = [
                "/Users/m3airmima0000/Mind-Daemon/music",  # Absolute path first
                "music",  # Current directory
                "../music",  # Up one level
                "../../music",  # Up two levels  
                os.path.join(os.path.dirname(__file__), "..", "..", "..", "music"),  # From mcp directory
            ]
            music_dir = "/Users/m3airmima0000/Mind-Daemon/music"  # default to absolute path
            
            for dir_path in possible_dirs:
                if os.path.exists(dir_path):
                    music_dir = os.path.abspath(dir_path)
                    print(f"🎵 Found music directory: {music_dir}")
                    break
                    
            music_player = EnhancedMusicPlayer(music_dir=music_dir)
            print(f"🎵 Enhanced music player initialized")
            
        except Exception as e:
            print(f"❌ Failed to initialize music player: {e}")
            # Create minimal fallback player
            music_player = EnhancedMusicPlayer(music_dir="music")

server = Server("music")

@server.list_resources()
async def handle_list_resources() -> list[Resource]:
    """List available music resources."""
    return [
        Resource(
            uri="music://status",
            name="Music Player Status",
            description="Enhanced music player status with pause/resume support",
            mimeType="application/json",
        ),
        Resource(
            uri="music://tracks",
            name="Available Tracks",
            description="List of available music tracks by type",
            mimeType="application/json",
        ),
    ]

@server.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Read music resource."""
    init_music_player()
    
    if uri == "music://status":
        status = music_player.get_status()
        return json.dumps(status, indent=2)
        
    elif uri == "music://tracks":
        tracks_info = {
            "relaxation_tracks": [os.path.basename(track) for track in music_player.relaxation_tracks],
            "focus_tracks": [os.path.basename(track) for track in music_player.focus_tracks],
            "total_tracks": len(music_player.relaxation_tracks) + len(music_player.focus_tracks),
            "music_directory": music_player.music_dir
        }
        return json.dumps(tracks_info, indent=2)
        
    else:
        raise ValueError(f"Unknown resource: {uri}")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available music control tools."""
    return [
        Tool(
            name="play_music",
            description="Play music with enhanced error handling and type support",
            inputSchema={
                "type": "object",
                "properties": {
                    "music_type": {
                        "type": "string",
                        "enum": ["focus", "relax", "relaxation"],
                        "description": "Type of music to play"
                    },
                    "mood": {
                        "type": "string",
                        "enum": ["focus", "relax", "relaxation"],
                        "description": "Mood-based music selection (alias for music_type)"
                    },
                    "track_name": {
                        "type": "string",
                        "description": "Specific track name to play (optional)"
                    },
                    "volume": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Volume level (0.0 to 1.0)"
                    }
                },
                "additionalProperties": False
            },
        ),
        Tool(
            name="stop_music",
            description="Stop current music playback",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="pause_music",
            description="Pause current music playback (enhanced functionality)",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="resume_music",
            description="Resume paused music playback (enhanced functionality)",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="skip_track",
            description="Skip to next track of the same type (elegant implementation)",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
        Tool(
            name="set_volume",
            description="Set music volume level",
            inputSchema={
                "type": "object",
                "properties": {
                    "volume": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Volume level (0.0 to 1.0)"
                    }
                },
                "required": ["volume"],
                "additionalProperties": False
            },
        ),
        Tool(
            name="fade_volume",
            description="Gradually change volume with enhanced control",
            inputSchema={
                "type": "object",
                "properties": {
                    "target_volume": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "description": "Target volume level (0.0 to 1.0)"
                    },
                    "duration": {
                        "type": "number",
                        "minimum": 0.5,
                        "maximum": 60.0,
                        "description": "Fade duration in seconds"
                    },
                    "fade_type": {
                        "type": "string",
                        "enum": ["in", "out", "to"],
                        "description": "Type of fade: in (increase), out (decrease), to (target)"
                    }
                },
                "required": ["fade_type"],
                "additionalProperties": False
            },
        ),
        Tool(
            name="get_music_status",
            description="Get enhanced music player status",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False
            },
        ),
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    """Handle tool calls with enhanced functionality."""
    init_music_player()
    
    if name == "play_music":
        music_type = arguments.get("music_type") or arguments.get("mood", "relax")
        track_name = arguments.get("track_name")
        volume = arguments.get("volume")
        
        # Set volume if specified
        if volume is not None:
            music_player.set_volume(volume)
        
        # Play specific track or by type
        if track_name:
            # Find and play specific track
            all_tracks = music_player.relaxation_tracks + music_player.focus_tracks
            matching_tracks = [t for t in all_tracks if track_name.lower() in os.path.basename(t).lower()]
            
            if matching_tracks:
                success = music_player._play_file(matching_tracks[0])
                track_played = os.path.basename(matching_tracks[0])
                if success:
                    return [types.TextContent(
                        type="text",
                        text=f"Playing specific track: {track_played}"
                    )]
                else:
                    return [types.TextContent(
                        type="text",
                        text=f"Failed to play track: {track_played}"
                    )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Track not found: {track_name}"
                )]
        else:
            # Play by type
            if music_type in ["focus"]:
                success = music_player.play_focus_music()
            else:  # relax, relaxation
                success = music_player.play_relaxation_music()
            
            if success:
                return [types.TextContent(
                    type="text",
                    text=f"Playing {music_type} music"
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=f"Failed to play {music_type} music - check if music files exist in {music_player.music_dir}"
                )]
                
    elif name == "stop_music":
        music_player.stop_music()
        return [types.TextContent(
            type="text",
            text="Music stopped"
        )]
        
    elif name == "pause_music":
        success = music_player.pause_music()
        return [types.TextContent(
            type="text",
            text="Music paused" if success else "Cannot pause music (not playing or already paused)"
        )]
        
    elif name == "resume_music":
        success = music_player.resume_music()
        return [types.TextContent(
            type="text",
            text="Music resumed" if success else "Cannot resume music (not paused)"
        )]
        
    elif name == "skip_track":
        success = music_player.skip_track()
        return [types.TextContent(
            type="text",
            text="Skipped to next track" if success else "Cannot skip track"
        )]
        
    elif name == "set_volume":
        volume = arguments.get("volume", 0.5)
        music_player.set_volume(volume)
        return [types.TextContent(
            type="text",
            text=f"Volume set to {volume:.2f}"
        )]
        
    elif name == "fade_volume":
        fade_type = arguments.get("fade_type")
        target_volume = arguments.get("target_volume", 0.5)
        duration = arguments.get("duration", 5.0)
        
        success = await music_player.fade_volume(target_volume, duration, fade_type)
        
        if success:
            return [types.TextContent(
                type="text",
                text=f"Fading volume {fade_type} to {target_volume:.2f} over {duration}s"
            )]
        else:
            return [types.TextContent(
                type="text",
                text="Cannot fade volume (music not playing)"
            )]
            
    elif name == "get_music_status":
        status = music_player.get_status()
        return [types.TextContent(
            type="text",
            text=json.dumps(status, indent=2)
        )]
        
    else:
        raise ValueError(f"Unknown tool: {name}")

async def main():
    """Main server function."""
    print("🔄 Starting enhanced music MCP server...")
    
    # Run the server using stdin/stdout streams
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="music",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())