"""Reminder System for Mental Command triggered reminders."""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum

from .action_config import ReminderAction, MentalCommandAction
from .detector import MentalCommandEvent

class ReminderStatus(Enum):
    """Status of a reminder."""
    PENDING = "pending"
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"
    EXPIRED = "expired"

@dataclass
class ReminderInstance:
    """An instance of a triggered reminder."""
    id: str
    action: ReminderAction
    trigger_event: MentalCommandEvent
    trigger_time: float
    status: ReminderStatus = ReminderStatus.TRIGGERED
    acknowledgment_time: Optional[float] = None
    cognitive_state_at_trigger: str = "unknown"
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'action': self.action.to_dict(),
            'trigger_event': {
                'command': self.trigger_event.command.value,
                'confidence': self.trigger_event.confidence,
                'timestamp': self.trigger_event.timestamp,
                'description': self.trigger_event.description
            },
            'trigger_time': self.trigger_time,
            'status': self.status.value,
            'acknowledgment_time': self.acknowledgment_time,
            'cognitive_state_at_trigger': self.cognitive_state_at_trigger,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReminderInstance':
        """Create from dictionary for JSON deserialization."""
        from .action_config import ReminderAction
        
        action = ReminderAction.from_dict(data['action'])
        
        # Reconstruct trigger event
        event_data = data['trigger_event']
        trigger_event = MentalCommandEvent(
            command=MentalCommandAction(event_data['command']),
            confidence=event_data['confidence'],
            timestamp=event_data['timestamp'],
            description=event_data['description']
        )
        
        return cls(
            id=data['id'],
            action=action,
            trigger_event=trigger_event,
            trigger_time=data['trigger_time'],
            status=ReminderStatus(data['status']),
            acknowledgment_time=data.get('acknowledgment_time'),
            cognitive_state_at_trigger=data.get('cognitive_state_at_trigger', 'unknown'),
            notes=data.get('notes', '')
        )

class ReminderSystem:
    """Comprehensive reminder management system."""
    
    def __init__(self, data_dir: str = "reminder_data"):
        self.data_dir = data_dir
        self._ensure_data_dir()
        
        # Active reminders
        self.active_reminders: List[ReminderInstance] = []
        self.reminder_history: List[ReminderInstance] = []
        
        # State tracking
        self.current_cognitive_state = "unknown"
        self.last_state_change = time.time()
        
        # Callbacks
        self.on_reminder_created: Optional[Callable[[ReminderInstance], None]] = None
        self.on_state_change_reminders: Optional[Callable[[str, List[ReminderInstance]], None]] = None
        
        # Load existing data
        self._load_reminder_data()
        
        # Settings
        self.max_active_reminders = 5
        self.reminder_expiry_hours = 24
        self.auto_acknowledge_timeout = 300  # 5 minutes
    
    def _ensure_data_dir(self):
        """Ensure data directory exists."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
            print(f"📁 创建提醒数据目录: {self.data_dir}")
    
    def _load_reminder_data(self):
        """Load reminder data from files."""
        # Load active reminders
        active_file = os.path.join(self.data_dir, "active_reminders.json")
        if os.path.exists(active_file):
            try:
                with open(active_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.active_reminders = [ReminderInstance.from_dict(item) for item in data]
                print(f"📥 加载了 {len(self.active_reminders)} 个活动提醒")
            except Exception as e:
                print(f"⚠️  加载活动提醒失败: {e}")
        
        # Load reminder history
        history_file = os.path.join(self.data_dir, "reminder_history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.reminder_history = [ReminderInstance.from_dict(item) for item in data]
                print(f"📥 加载了 {len(self.reminder_history)} 条提醒历史")
            except Exception as e:
                print(f"⚠️  加载提醒历史失败: {e}")
    
    def _save_reminder_data(self):
        """Save reminder data to files."""
        try:
            # Save active reminders
            active_file = os.path.join(self.data_dir, "active_reminders.json")
            with open(active_file, 'w', encoding='utf-8') as f:
                data = [reminder.to_dict() for reminder in self.active_reminders]
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            # Save reminder history (keep only recent ones)
            recent_history = self._get_recent_history(days=30)
            history_file = os.path.join(self.data_dir, "reminder_history.json")
            with open(history_file, 'w', encoding='utf-8') as f:
                data = [reminder.to_dict() for reminder in recent_history]
                json.dump(data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"❌ 保存提醒数据失败: {e}")
    
    def create_reminder(self, action: ReminderAction, trigger_event: MentalCommandEvent) -> ReminderInstance:
        """Create a new reminder instance."""
        # Generate unique ID
        reminder_id = f"reminder_{int(time.time() * 1000)}"
        
        # Create reminder instance
        reminder = ReminderInstance(
            id=reminder_id,
            action=action,
            trigger_event=trigger_event,
            trigger_time=time.time(),
            cognitive_state_at_trigger=self.current_cognitive_state
        )
        
        # Add to active reminders
        self.active_reminders.append(reminder)
        
        # Manage active reminder count
        self._cleanup_active_reminders()
        
        # Save data
        self._save_reminder_data()
        
        print(f"📝 创建提醒: {action.description}")
        print(f"   🔔 消息: {action.message}")
        print(f"   🧠 触发状态: {self.current_cognitive_state}")
        
        # Notify callback
        if self.on_reminder_created:
            self.on_reminder_created(reminder)
        
        return reminder
    
    def acknowledge_reminder(self, reminder_id: str, notes: str = "") -> bool:
        """Acknowledge a reminder."""
        for reminder in self.active_reminders:
            if reminder.id == reminder_id:
                reminder.status = ReminderStatus.ACKNOWLEDGED
                reminder.acknowledgment_time = time.time()
                reminder.notes = notes
                
                # Move to history
                self.reminder_history.append(reminder)
                self.active_reminders.remove(reminder)
                
                self._save_reminder_data()
                
                print(f"✅ 确认提醒: {reminder.action.description}")
                if notes:
                    print(f"   📝 备注: {notes}")
                
                return True
        
        print(f"⚠️  未找到提醒ID: {reminder_id}")
        return False
    
    def dismiss_reminder(self, reminder_id: str, notes: str = "") -> bool:
        """Dismiss a reminder without acknowledging."""
        for reminder in self.active_reminders:
            if reminder.id == reminder_id:
                reminder.status = ReminderStatus.DISMISSED
                reminder.acknowledgment_time = time.time()
                reminder.notes = notes
                
                # Move to history
                self.reminder_history.append(reminder)
                self.active_reminders.remove(reminder)
                
                self._save_reminder_data()
                
                print(f"🚫 忽略提醒: {reminder.action.description}")
                if notes:
                    print(f"   📝 备注: {notes}")
                
                return True
        
        print(f"⚠️  未找到提醒ID: {reminder_id}")
        return False
    
    def update_cognitive_state(self, new_state: str):
        """Update current cognitive state and check for state-change reminders."""
        if new_state == self.current_cognitive_state:
            return
        
        old_state = self.current_cognitive_state
        self.current_cognitive_state = new_state
        self.last_state_change = time.time()
        
        print(f"🧠 认知状态变化: {old_state} -> {new_state}")
        
        # Check for relevant reminders
        relevant_reminders = self._get_state_relevant_reminders(new_state)
        
        if relevant_reminders:
            print(f"💡 发现 {len(relevant_reminders)} 个相关提醒")
            
            # Notify callback
            if self.on_state_change_reminders:
                self.on_state_change_reminders(new_state, relevant_reminders)
    
    def _get_state_relevant_reminders(self, state: str) -> List[ReminderInstance]:
        """Get reminders relevant to the current cognitive state."""
        relevant = []
        
        for reminder in self.active_reminders:
            if (state in reminder.action.trigger_states or 
                len(reminder.action.trigger_states) == 0):  # Empty trigger_states means always relevant
                relevant.append(reminder)
        
        # Sort by priority and recency
        relevant.sort(key=lambda r: (r.action.priority, r.trigger_time), reverse=True)
        
        return relevant
    
    def _cleanup_active_reminders(self):
        """Clean up expired and excessive active reminders."""
        current_time = time.time()
        
        # Remove expired reminders
        expired_reminders = []
        for reminder in self.active_reminders[:]:
            reminder_age_hours = (current_time - reminder.trigger_time) / 3600
            if reminder_age_hours > self.reminder_expiry_hours:
                reminder.status = ReminderStatus.EXPIRED
                expired_reminders.append(reminder)
                self.active_reminders.remove(reminder)
                self.reminder_history.append(reminder)
        
        if expired_reminders:
            print(f"⏰ 移除 {len(expired_reminders)} 个过期提醒")
        
        # Limit active reminders count
        if len(self.active_reminders) > self.max_active_reminders:
            # Move oldest reminders to history
            excess_count = len(self.active_reminders) - self.max_active_reminders
            oldest_reminders = sorted(self.active_reminders, key=lambda r: r.trigger_time)[:excess_count]
            
            for reminder in oldest_reminders:
                reminder.status = ReminderStatus.DISMISSED
                reminder.notes = "自动移除（超出活动提醒数量限制）"
                self.active_reminders.remove(reminder)
                self.reminder_history.append(reminder)
            
            print(f"📦 自动移除 {excess_count} 个最旧的提醒")
    
    def get_active_reminders(self, priority_filter: Optional[int] = None) -> List[ReminderInstance]:
        """Get active reminders, optionally filtered by priority."""
        reminders = self.active_reminders.copy()
        
        if priority_filter is not None:
            reminders = [r for r in reminders if r.action.priority >= priority_filter]
        
        # Sort by priority and recency
        reminders.sort(key=lambda r: (r.action.priority, r.trigger_time), reverse=True)
        
        return reminders
    
    def get_reminders_by_category(self, category: str) -> List[ReminderInstance]:
        """Get reminders by category."""
        return [r for r in self.active_reminders if r.action.category == category]
    
    def _get_recent_history(self, days: int = 7) -> List[ReminderInstance]:
        """Get reminder history from recent days."""
        cutoff_time = time.time() - (days * 24 * 3600)
        return [r for r in self.reminder_history if r.trigger_time > cutoff_time]
    
    def get_statistics(self, days: int = 7) -> Dict[str, Any]:
        """Get reminder statistics for analysis."""
        recent_history = self._get_recent_history(days)
        all_recent = recent_history + self.active_reminders
        
        if not all_recent:
            return {
                'total_reminders': 0,
                'active_count': 0,
                'acknowledged_rate': 0,
                'categories': {},
                'commands': {},
                'cognitive_states': {}
            }
        
        # Calculate statistics
        total_count = len(all_recent)
        active_count = len(self.active_reminders)
        acknowledged_count = len([r for r in recent_history if r.status == ReminderStatus.ACKNOWLEDGED])
        
        # Category distribution
        categories = {}
        for reminder in all_recent:
            cat = reminder.action.category
            categories[cat] = categories.get(cat, 0) + 1
        
        # Command distribution
        commands = {}
        for reminder in all_recent:
            cmd = reminder.trigger_event.command.value
            commands[cmd] = commands.get(cmd, 0) + 1
        
        # Cognitive state distribution
        states = {}
        for reminder in all_recent:
            state = reminder.cognitive_state_at_trigger
            states[state] = states.get(state, 0) + 1
        
        return {
            'total_reminders': total_count,
            'active_count': active_count,
            'acknowledged_count': acknowledged_count,
            'acknowledged_rate': (acknowledged_count / total_count * 100) if total_count > 0 else 0,
            'categories': categories,
            'commands': commands,
            'cognitive_states': states,
            'average_acknowledgment_time': self._calculate_avg_acknowledgment_time(recent_history)
        }
    
    def _calculate_avg_acknowledgment_time(self, reminders: List[ReminderInstance]) -> float:
        """Calculate average time to acknowledge reminders."""
        acknowledged = [r for r in reminders if r.acknowledgment_time and r.trigger_time]
        
        if not acknowledged:
            return 0
        
        total_time = sum(r.acknowledgment_time - r.trigger_time for r in acknowledged)
        return total_time / len(acknowledged)
    
    def print_active_reminders(self):
        """Print current active reminders."""
        if not self.active_reminders:
            print("📭 当前没有活动提醒")
            return
        
        print(f"\n📋 活动提醒 ({len(self.active_reminders)}个):")
        print("=" * 60)
        
        for i, reminder in enumerate(self.get_active_reminders(), 1):
            age_minutes = (time.time() - reminder.trigger_time) / 60
            
            print(f"{i:2d}. {reminder.action.description}")
            print(f"     💬 {reminder.action.message}")
            print(f"     🧠 命令: {reminder.trigger_event.command.value} (置信度: {reminder.trigger_event.confidence:.2f})")
            print(f"     ⏰ {age_minutes:.0f}分钟前 | 优先级: {reminder.action.priority}/5")
            print(f"     🎯 状态: {reminder.cognitive_state_at_trigger}")
            print()
    
    def print_statistics(self, days: int = 7):
        """Print reminder statistics."""
        stats = self.get_statistics(days)
        
        print(f"\n📊 提醒系统统计 (最近{days}天):")
        print("=" * 40)
        print(f"📝 总提醒数: {stats['total_reminders']}")
        print(f"🔔 活动提醒: {stats['active_count']}")
        print(f"✅ 确认率: {stats['acknowledged_rate']:.1f}%")
        print(f"⏱️  平均确认时间: {stats['average_acknowledgment_time']/60:.1f}分钟")
        
        if stats['categories']:
            print("\n📂 分类分布:")
            for category, count in stats['categories'].items():
                print(f"  {category:10}: {count:3d}次")
        
        if stats['commands']:
            print("\n🧠 命令分布:")
            for command, count in stats['commands'].items():
                print(f"  {command:15}: {count:3d}次")

# Example usage and testing
if __name__ == "__main__":
    # Create test reminder system
    reminder_system = ReminderSystem("test_reminder_data")
    
    # Simulate some reminders
    from .action_config import ReminderAction, MentalCommandAction
    from .detector import MentalCommandEvent
    
    # Test reminder action
    test_action = ReminderAction(
        command=MentalCommandAction.PUSH,
        description="测试提醒",
        category="test",
        priority=3,
        trigger_states=["high_focus"],
        message="这是一个测试提醒消息",
        cooldown_minutes=10
    )
    
    # Test command event
    test_event = MentalCommandEvent(
        command=MentalCommandAction.PUSH,
        confidence=0.85,
        timestamp=time.time(),
        description="测试命令"
    )
    
    # Create reminder
    reminder = reminder_system.create_reminder(test_action, test_event)
    
    # Print status
    reminder_system.print_active_reminders()
    reminder_system.print_statistics()
    
    # Test acknowledgment
    print(f"\n✅ 确认提醒...")
    reminder_system.acknowledge_reminder(reminder.id, "测试完成")
    
    reminder_system.print_active_reminders()
    reminder_system.print_statistics()