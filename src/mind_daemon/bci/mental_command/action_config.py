"""Configuration for mental command actions and reminders."""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import json
import os

class MentalCommandAction(Enum):
    """Available mental command actions in Emotiv Cortex."""
    NEUTRAL = "neutral"
    PUSH = "push"
    PULL = "pull"
    LIFT = "lift"
    DROP = "drop"
    LEFT = "left"
    RIGHT = "right"
    ROTATE_LEFT = "rotateLeft"
    ROTATE_RIGHT = "rotateRight"
    ROTATE_CLOCKWISE = "rotateClockwise"
    ROTATE_COUNTER_CLOCKWISE = "rotateCounterClockwise"
    ROTATE_FORWARDS = "rotateForwards"
    ROTATE_REVERSE = "rotateReverse"
    DISAPPEAR = "disappear"

@dataclass
class ReminderAction:
    """A reminder action associated with a mental command."""
    command: MentalCommandAction  # The mental command trigger
    description: str             # User-friendly description (e.g., "记得喝水")
    category: str               # Category (e.g., "health", "work", "break")
    priority: int               # Priority level (1-5, 5 highest)
    trigger_states: List[str]   # Cognitive states that can trigger this reminder
    message: str                # Reminder message to display
    cooldown_minutes: int       # Cooldown period to avoid spam
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'command': self.command.value,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'trigger_states': self.trigger_states,
            'message': self.message,
            'cooldown_minutes': self.cooldown_minutes
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ReminderAction':
        """Create from dictionary for JSON deserialization."""
        return cls(
            command=MentalCommandAction(data['command']),
            description=data['description'],
            category=data['category'],
            priority=data['priority'],
            trigger_states=data['trigger_states'],
            message=data['message'],
            cooldown_minutes=data['cooldown_minutes']
        )

class ActionConfig:
    """Configuration manager for mental command actions."""
    
    def __init__(self, config_file: str = "mental_command_config.json"):
        self.config_file = config_file
        self.actions: List[ReminderAction] = []
        self.load_config()
    
    def add_action(self, action: ReminderAction):
        """Add a new reminder action."""
        # Check if command already exists
        existing = self.get_action_by_command(action.command)
        if existing:
            print(f"⚠️  命令 {action.command.value} 已存在，将替换现有配置")
            self.remove_action(action.command)
        
        self.actions.append(action)
        self.save_config()
        print(f"✅ 添加提醒动作: {action.description}")
    
    def remove_action(self, command: MentalCommandAction):
        """Remove an action by command."""
        self.actions = [a for a in self.actions if a.command != command]
        self.save_config()
        print(f"🗑️  删除命令: {command.value}")
    
    def get_action_by_command(self, command: MentalCommandAction) -> Optional[ReminderAction]:
        """Get action by mental command."""
        for action in self.actions:
            if action.command == command:
                return action
        return None
    
    def get_actions_by_state(self, state: str) -> List[ReminderAction]:
        """Get actions that can be triggered by a cognitive state."""
        return [a for a in self.actions if state in a.trigger_states]
    
    def get_actions_by_category(self, category: str) -> List[ReminderAction]:
        """Get actions by category."""
        return [a for a in self.actions if a.category == category]
    
    def list_trained_commands(self) -> List[MentalCommandAction]:
        """Get list of commands that need to be trained."""
        return [action.command for action in self.actions]
    
    def load_config(self):
        """Load configuration from JSON file."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.actions = [ReminderAction.from_dict(item) for item in data.get('actions', [])]
                print(f"✅ 加载了 {len(self.actions)} 个提醒动作配置")
            except Exception as e:
                print(f"⚠️  加载配置文件失败: {e}")
                self._create_default_config()
        else:
            print("📝 配置文件不存在，创建默认配置")
            self._create_default_config()
    
    def save_config(self):
        """Save configuration to JSON file."""
        try:
            data = {
                'actions': [action.to_dict() for action in self.actions],
                'version': '1.0'
            }
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"💾 配置已保存到 {self.config_file}")
        except Exception as e:
            print(f"❌ 保存配置失败: {e}")
    
    def _create_default_config(self):
        """Create default configuration."""
        default_actions = [
            ReminderAction(
                command=MentalCommandAction.PUSH,
                description="记得喝水",
                category="health",
                priority=4,
                trigger_states=["high_focus", "cognitive_overload"],
                message="💧 该喝水了！保持水分对专注很重要",
                cooldown_minutes=30
            ),
            ReminderAction(
                command=MentalCommandAction.PULL,
                description="休息提醒",
                category="break",
                priority=5,
                trigger_states=["cognitive_overload", "high_focus"],
                message="😌 工作辛苦了，该休息一下眼睛和大脑",
                cooldown_minutes=45
            ),
            ReminderAction(
                command=MentalCommandAction.LIFT,
                description="检查邮件",
                category="work",
                priority=3,
                trigger_states=["medium_focus", "neutral"],
                message="📧 可以检查一下邮件和消息了",
                cooldown_minutes=60
            )
        ]
        
        for action in default_actions:
            self.actions.append(action)
        
        self.save_config()
    
    def print_summary(self):
        """Print configuration summary."""
        print("\n🧠 Mental Command 提醒配置摘要:")
        print("=" * 50)
        
        if not self.actions:
            print("❌ 没有配置任何提醒动作")
            return
        
        # Group by category
        categories = {}
        for action in self.actions:
            if action.category not in categories:
                categories[action.category] = []
            categories[action.category].append(action)
        
        for category, actions in categories.items():
            print(f"\n📂 {category.upper()} ({len(actions)}个):")
            for action in sorted(actions, key=lambda x: x.priority, reverse=True):
                states_str = ", ".join(action.trigger_states)
                print(f"  🧠 {action.command.value:15} -> {action.description}")
                print(f"     优先级: {action.priority}/5, 触发状态: {states_str}")
                print(f"     冷却时间: {action.cooldown_minutes}分钟")
        
        print(f"\n📊 总计: {len(self.actions)} 个提醒动作需要训练")

# Example usage and testing
if __name__ == "__main__":
    config = ActionConfig("test_mental_command_config.json")
    config.print_summary()
    
    # Test adding a custom action
    custom_action = ReminderAction(
        command=MentalCommandAction.LEFT,
        description="站起来走走",
        category="health",
        priority=4,
        trigger_states=["drowsy", "low_focus"],
        message="🚶‍♂️ 起来活动一下，促进血液循环！",
        cooldown_minutes=20
    )
    
    config.add_action(custom_action)
    config.print_summary()