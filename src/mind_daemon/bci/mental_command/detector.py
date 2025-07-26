"""Mental Command Detector for real-time BCI reminder system."""

import sys
import os
import time
import threading
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass
from collections import defaultdict

# Add cortex path for imports
cortex_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'python_demo')
if cortex_path not in sys.path:
    sys.path.append(cortex_path)

try:
    import cortex
    from cortex import Cortex
except ImportError:
    print("⚠️  无法导入Cortex模块，请确保python_demo/cortex.py存在")
    Cortex = None

from .action_config import ActionConfig, ReminderAction, MentalCommandAction

@dataclass
class MentalCommandEvent:
    """A detected mental command event."""
    command: MentalCommandAction
    confidence: float
    timestamp: float
    description: str
    reminder_action: Optional[ReminderAction] = None

@dataclass
class DetectionStats:
    """Statistics for mental command detection."""
    total_detections: int = 0
    command_counts: Dict[str, int] = None
    false_positive_count: int = 0
    session_start_time: float = 0
    
    def __post_init__(self):
        if self.command_counts is None:
            self.command_counts = defaultdict(int)
        if self.session_start_time == 0:
            self.session_start_time = time.time()

class MentalCommandDetector:
    """Real-time Mental Command Detector with reminder integration."""
    
    def __init__(self, app_client_id: str, app_client_secret: str, 
                 profile_name: str = "", **kwargs):
        if not Cortex:
            raise ImportError("Cortex模块未正确导入")
            
        self.app_client_id = app_client_id
        self.app_client_secret = app_client_secret
        self.profile_name = profile_name
        
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=False, **kwargs)
        self._setup_callbacks()
        
        # Configuration
        self.config = ActionConfig()
        
        # Detection settings
        self.min_confidence_threshold = 0.7  # Minimum confidence to trigger
        self.enabled_commands: Dict[MentalCommandAction, bool] = {}
        self._initialize_enabled_commands()
        
        # Cooldown management (in seconds)
        self.command_cooldowns: Dict[MentalCommandAction, float] = {}
        self.last_trigger_times: Dict[MentalCommandAction, float] = {}
        self._initialize_cooldowns()
        
        # Current state context
        self.current_cognitive_state = "neutral"
        self.state_change_callback: Optional[Callable[[str], None]] = None
        
        # Callbacks
        self.on_command_detected: Optional[Callable[[MentalCommandEvent], None]] = None
        self.on_reminder_triggered: Optional[Callable[[ReminderAction, MentalCommandEvent], None]] = None
        
        # Status and statistics
        self.is_detecting = False
        self.detection_stats = DetectionStats()
        
        # Session management
        self.session_id = None
        
    def _setup_callbacks(self):
        """Setup Cortex event callbacks."""
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(query_profile_done=self.on_query_profile_done)
        self.c.bind(load_unload_profile_done=self.on_load_unload_profile_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_com_data=self.on_new_com_data)
        self.c.bind(inform_error=self.on_inform_error)
    
    def _initialize_enabled_commands(self):
        """Initialize enabled commands based on configuration."""
        for action in self.config.actions:
            self.enabled_commands[action.command] = True
        
        # Always enable neutral for baseline
        self.enabled_commands[MentalCommandAction.NEUTRAL] = True
    
    def _initialize_cooldowns(self):
        """Initialize command cooldowns from configuration."""
        for action in self.config.actions:
            cooldown_seconds = action.cooldown_minutes * 60
            self.command_cooldowns[action.command] = cooldown_seconds
            self.last_trigger_times[action.command] = 0
    
    def start_detection(self, profile_name: str = "", headset_id: str = ""):
        """
        Start real-time mental command detection.
        
        Args:
            profile_name: Profile to load (uses default if empty)
            headset_id: Specific headset ID (optional)
        """
        if self.is_detecting:
            print("⚠️  检测已在运行中")
            return False
        
        if profile_name:
            self.profile_name = profile_name
        
        if not self.profile_name:
            print("❌ 必须指定Profile名称")
            return False
        
        print(f"🧠 启动Mental Command检测...")
        print(f"📝 Profile: {self.profile_name}")
        print(f"🎯 监控命令: {len([cmd for cmd, enabled in self.enabled_commands.items() if enabled])}个")
        
        # Setup
        if headset_id:
            self.c.set_wanted_headset(headset_id)
        
        self.c.set_wanted_profile(self.profile_name)
        self.is_detecting = True
        self.detection_stats = DetectionStats()
        
        # Start Cortex connection
        self.c.open()
        return True
    
    def stop_detection(self):
        """Stop mental command detection."""
        self.is_detecting = False
        if self.c:
            try:
                self.c.close()
            except:
                pass
        
        # Show session summary
        self._print_session_summary()
        print("⏹️  Mental Command检测已停止")
    
    def update_cognitive_state(self, state: str):
        """Update current cognitive state context."""
        if state != self.current_cognitive_state:
            old_state = self.current_cognitive_state
            self.current_cognitive_state = state
            print(f"🧠 认知状态变化: {old_state} -> {state}")
            
            if self.state_change_callback:
                self.state_change_callback(state)
    
    def enable_command(self, command: MentalCommandAction, enabled: bool = True):
        """Enable or disable detection for a specific command."""
        self.enabled_commands[command] = enabled
        status = "启用" if enabled else "禁用"
        print(f"⚙️  {status}命令检测: {command.value}")
    
    def set_confidence_threshold(self, threshold: float):
        """Set minimum confidence threshold for detection."""
        self.min_confidence_threshold = max(0.0, min(1.0, threshold))
        print(f"⚙️  设置置信度阈值: {self.min_confidence_threshold}")
    
    def is_command_in_cooldown(self, command: MentalCommandAction) -> bool:
        """Check if a command is in cooldown period."""
        if command not in self.last_trigger_times:
            return False
        
        cooldown = self.command_cooldowns.get(command, 0)
        elapsed = time.time() - self.last_trigger_times[command]
        return elapsed < cooldown
    
    def _should_trigger_reminder(self, command: MentalCommandEvent) -> Optional[ReminderAction]:
        """Determine if this command should trigger a reminder."""
        # Check if command is enabled
        if not self.enabled_commands.get(command.command, False):
            return None
        
        # Check confidence threshold
        if command.confidence < self.min_confidence_threshold:
            return None
        
        # Check cooldown
        if self.is_command_in_cooldown(command.command):
            return None
        
        # Get reminder action configuration
        reminder_action = self.config.get_action_by_command(command.command)
        if not reminder_action:
            return None
        
        # Check if current state can trigger this reminder
        if (self.current_cognitive_state not in reminder_action.trigger_states and 
            len(reminder_action.trigger_states) > 0):
            return None
        
        return reminder_action
    
    def _trigger_reminder(self, command_event: MentalCommandEvent, reminder_action: ReminderAction):
        """Trigger a reminder action."""
        # Update last trigger time
        self.last_trigger_times[command_event.command] = time.time()
        
        # Create reminder event
        print(f"🔔 触发提醒: {reminder_action.description}")
        print(f"   💬 {reminder_action.message}")
        print(f"   ⏰ 冷却时间: {reminder_action.cooldown_minutes}分钟")
        
        # Notify callback
        if self.on_reminder_triggered:
            self.on_reminder_triggered(reminder_action, command_event)
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get current detection statistics."""
        session_duration = time.time() - self.detection_stats.session_start_time
        
        return {
            'session_duration_minutes': session_duration / 60,
            'total_detections': self.detection_stats.total_detections,
            'commands_detected': dict(self.detection_stats.command_counts),
            'detections_per_minute': self.detection_stats.total_detections / (session_duration / 60) if session_duration > 0 else 0,
            'enabled_commands': [cmd.value for cmd, enabled in self.enabled_commands.items() if enabled],
            'current_state': self.current_cognitive_state
        }
    
    def _print_session_summary(self):
        """Print detection session summary."""
        stats = self.get_detection_stats()
        
        print("\n📊 Mental Command检测会话摘要:")
        print("=" * 40)
        print(f"⏱️  会话时长: {stats['session_duration_minutes']:.1f}分钟")
        print(f"🎯 总检测次数: {stats['total_detections']}")
        print(f"📈 检测频率: {stats['detections_per_minute']:.1f}次/分钟")
        
        if stats['commands_detected']:
            print("\n📋 命令检测统计:")
            for cmd, count in stats['commands_detected'].items():
                print(f"  {cmd:15}: {count:3d}次")
    
    # Cortex event callbacks
    def on_create_session_done(self, *args, **kwargs):
        """Handle session creation."""
        session_data = kwargs.get('data', {})
        self.session_id = session_data.get('id')
        print(f'✅ 检测会话创建成功 (ID: {self.session_id})')
        self.c.query_profile()
    
    def on_query_profile_done(self, *args, **kwargs):
        """Handle profile query completion."""
        self.profile_lists = kwargs.get('data')
        
        if self.profile_name in self.profile_lists:
            print(f"✅ Profile '{self.profile_name}' 找到，加载中...")
            self.c.get_current_profile()
        else:
            print(f"❌ Profile '{self.profile_name}' 不存在")
            print("💡 请先使用MentalCommandTrainer训练该Profile")
            self.is_detecting = False
    
    def on_load_unload_profile_done(self, *args, **kwargs):
        """Handle profile load/unload completion."""
        is_loaded = kwargs.get('isLoaded')
        
        if is_loaded:
            print(f"✅ Profile '{self.profile_name}' 加载成功")
            print("📡 订阅Mental Command数据流...")
            self.c.sub_request(['com'])  # Subscribe to mental command stream
        else:
            print(f"🔄 Profile '{self.profile_name}' 已卸载")
            self.is_detecting = False
            self.c.close()
    
    def on_new_data_labels(self, *args, **kwargs):
        """Handle data labels subscription."""
        data = kwargs.get('data')
        
        if data and data.get('streamName') == 'com':
            print("✅ Mental Command数据流订阅成功")
            print("🔍 开始实时检测...")
            
            # Display monitoring info
            enabled_count = len([cmd for cmd, enabled in self.enabled_commands.items() if enabled])
            print(f"👁️  监控 {enabled_count} 个命令，置信度阈值: {self.min_confidence_threshold}")
    
    def on_new_com_data(self, *args, **kwargs):
        """Handle new mental command data."""
        data = kwargs.get('data')
        
        if not data or len(data) < 2:
            return
        
        # Parse mental command data
        # Data format: [timestamp, [command_results...]]
        timestamp = data[0]
        com_data = data[1]
        
        # Find the most confident command
        if not com_data or len(com_data) == 0:
            return
        
        # The com_data typically contains results for different commands
        # Find the command with highest confidence
        max_confidence = 0
        detected_command = None
        
        # Check each mental command result
        # Note: The exact format depends on Cortex API version
        # This is a simplified version - you may need to adjust based on actual data format
        try:
            for i, confidence in enumerate(com_data):
                if confidence > max_confidence and confidence > self.min_confidence_threshold:
                    max_confidence = confidence
                    # Map index to command (this mapping depends on your training)
                    if i < len(list(MentalCommandAction)):
                        detected_command = list(MentalCommandAction)[i]
            
            if detected_command and max_confidence > self.min_confidence_threshold:
                self._process_detected_command(detected_command, max_confidence, timestamp)
                
        except Exception as e:
            print(f"⚠️  处理Mental Command数据时出错: {e}")
    
    def _process_detected_command(self, command: MentalCommandAction, confidence: float, timestamp: float):
        """Process a detected mental command."""
        # Update statistics
        self.detection_stats.total_detections += 1
        self.detection_stats.command_counts[command.value] += 1
        
        # Create command event
        command_event = MentalCommandEvent(
            command=command,
            confidence=confidence,
            timestamp=timestamp,
            description=self.config.get_action_by_command(command).description if self.config.get_action_by_command(command) else command.value
        )
        
        # Notify detection callback
        if self.on_command_detected:
            self.on_command_detected(command_event)
        
        # Check if should trigger reminder
        reminder_action = self._should_trigger_reminder(command_event)
        if reminder_action:
            command_event.reminder_action = reminder_action
            self._trigger_reminder(command_event, reminder_action)
        else:
            # Log why not triggered
            if command == MentalCommandAction.NEUTRAL:
                pass  # Don't log neutral commands
            elif not self.enabled_commands.get(command, False):
                print(f"🔇 命令已禁用: {command.value}")
            elif confidence < self.min_confidence_threshold:
                print(f"📉 置信度过低: {command.value} ({confidence:.2f} < {self.min_confidence_threshold})")
            elif self.is_command_in_cooldown(command):
                cooldown_remaining = self.command_cooldowns.get(command, 0) - (time.time() - self.last_trigger_times.get(command, 0))
                print(f"⏳ 命令冷却中: {command.value} (剩余 {cooldown_remaining:.0f}秒)")
    
    def on_inform_error(self, *args, **kwargs):
        """Handle Cortex errors."""
        error_data = kwargs.get('error_data')
        error_code = error_data['code']
        error_message = error_data['message']
        
        print(f"❌ Cortex错误: {error_message} (代码: {error_code})")
        
        if error_code == cortex.ERR_PROFILE_ACCESS_DENIED:
            print("🔌 访问被拒绝，断开头戴设备以修复此问题")
            self.c.disconnect_headset()

def interactive_detection_session():
    """Interactive detection session for testing."""
    print("🔍 Mental Command 实时检测")
    print("=" * 40)
    
    # Get credentials
    client_id = input("请输入 Client ID: ").strip()
    client_secret = input("请输入 Client Secret: ").strip()
    profile_name = input("请输入已训练的Profile名称: ").strip()
    
    if not all([client_id, client_secret, profile_name]):
        print("❌ 所有字段都不能为空")
        return
    
    # Initialize detector
    try:
        detector = MentalCommandDetector(client_id, client_secret)
        
        # Setup callbacks for demonstration
        def on_command_detected(event: MentalCommandEvent):
            print(f"🧠 检测到命令: {event.command.value} (置信度: {event.confidence:.2f})")
        
        def on_reminder_triggered(reminder: ReminderAction, event: MentalCommandEvent):
            print(f"🔔 触发提醒: {reminder.description} - {reminder.message}")
        
        detector.on_command_detected = on_command_detected
        detector.on_reminder_triggered = on_reminder_triggered
        
        # Start detection
        print(f"\n🚀 开始检测，按 Ctrl+C 停止...")
        detector.start_detection(profile_name)
        
        # Keep running until interrupted
        try:
            while detector.is_detecting:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n⏹️  用户停止检测")
        
    except Exception as e:
        print(f"❌ 检测过程出错: {e}")
    finally:
        if 'detector' in locals():
            detector.stop_detection()

if __name__ == "__main__":
    interactive_detection_session()