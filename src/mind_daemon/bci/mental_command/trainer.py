"""Mental Command Trainer for BCI-powered reminder system."""

import sys
import os
import time
import threading
from typing import List, Optional, Callable
from dataclasses import dataclass

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
class TrainingProgress:
    """Training progress tracking."""
    action: MentalCommandAction
    status: str  # 'pending', 'training', 'success', 'failed', 'completed'
    attempts: int
    start_time: Optional[float]
    end_time: Optional[float]
    description: str

class MentalCommandTrainer:
    """Enhanced Mental Command Trainer with reminder system integration."""
    
    def __init__(self, app_client_id: str, app_client_secret: str, **kwargs):
        if not Cortex:
            raise ImportError("Cortex模块未正确导入")
            
        self.app_client_id = app_client_id
        self.app_client_secret = app_client_secret
        
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=True, **kwargs)
        self._setup_callbacks()
        
        # Training state
        self.profile_name = ""
        self.actions_to_train: List[MentalCommandAction] = []
        self.action_descriptions: dict = {}  # Map command to description
        self.current_action_idx = 0
        self.training_progress: List[TrainingProgress] = []
        
        # Configuration
        self.config = ActionConfig()
        
        # Callbacks
        self.on_training_complete: Optional[Callable] = None
        self.on_progress_update: Optional[Callable[[TrainingProgress], None]] = None
        
        # Status
        self.is_training = False
        self.training_thread = None
        
    def _setup_callbacks(self):
        """Setup Cortex event callbacks."""
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(query_profile_done=self.on_query_profile_done)
        self.c.bind(load_unload_profile_done=self.on_load_unload_profile_done)
        self.c.bind(save_profile_done=self.on_save_profile_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_sys_data=self.on_new_sys_data)
        self.c.bind(inform_error=self.on_inform_error)
    
    def start_training_session(self, profile_name: str, headset_id: str = '', 
                              selected_actions: Optional[List[str]] = None):
        """
        Start a comprehensive training session.
        
        Args:
            profile_name: Profile name to create/load
            headset_id: Specific headset ID (optional)
            selected_actions: List of action descriptions to train (optional)
        """
        if self.is_training:
            print("⚠️  训练已在进行中")
            return False
            
        if not profile_name:
            raise ValueError("Profile name cannot be empty")
        
        self.profile_name = profile_name
        self.is_training = True
        
        # Prepare actions to train
        self._prepare_training_actions(selected_actions)
        
        if not self.actions_to_train:
            print("❌ 没有需要训练的动作")
            self.is_training = False
            return False
        
        # Setup headset
        if headset_id:
            self.c.set_wanted_headset(headset_id)
        
        self.c.set_wanted_profile(profile_name)
        
        print(f"🚀 开始训练会话...")
        print(f"📝 Profile: {profile_name}")
        print(f"🎯 训练动作: {len(self.actions_to_train)}个")
        
        # Display training plan
        self._display_training_plan()
        
        # Start Cortex connection
        self.c.open()
        return True
    
    def _prepare_training_actions(self, selected_actions: Optional[List[str]] = None):
        """Prepare the list of actions to train."""
        self.actions_to_train = []
        self.action_descriptions = {}
        self.training_progress = []
        
        if selected_actions:
            # Train only selected actions
            for description in selected_actions:
                action_config = None
                for config_action in self.config.actions:
                    if config_action.description == description:
                        action_config = config_action
                        break
                
                if action_config:
                    self.actions_to_train.append(action_config.command)
                    self.action_descriptions[action_config.command] = action_config.description
                else:
                    print(f"⚠️  未找到动作描述: {description}")
        else:
            # Train all configured actions
            for action_config in self.config.actions:
                self.actions_to_train.append(action_config.command)
                self.action_descriptions[action_config.command] = action_config.description
        
        # Always include neutral as baseline
        if MentalCommandAction.NEUTRAL not in self.actions_to_train:
            self.actions_to_train.insert(0, MentalCommandAction.NEUTRAL)
            self.action_descriptions[MentalCommandAction.NEUTRAL] = "基线状态"
        
        # Initialize training progress
        for action in self.actions_to_train:
            progress = TrainingProgress(
                action=action,
                status='pending',
                attempts=0,
                start_time=None,
                end_time=None,
                description=self.action_descriptions.get(action, action.value)
            )
            self.training_progress.append(progress)
    
    def _display_training_plan(self):
        """Display the training plan to user."""
        print("\n🎯 训练计划:")
        print("=" * 50)
        for i, progress in enumerate(self.training_progress, 1):
            print(f"{i:2d}. {progress.action.value:15} -> {progress.description}")
        
        print("\n💡 训练提示:")
        print("  • 每个动作需要专注8秒")
        print("  • 保持头戴设备良好接触")
        print("  • 训练时保持放松但专注的状态")
        print("  • 可以多次尝试直到满意")
        
        print("\n请确保:")
        print("  ✓ Emotiv Launcher正在运行")
        print("  ✓ 头戴设备已连接且信号良好")
        print("  ✓ 处于安静的环境中")
        
        input("\n按回车开始训练...")
    
    def get_current_progress(self) -> List[TrainingProgress]:
        """Get current training progress."""
        return self.training_progress.copy()
    
    def get_training_summary(self) -> dict:
        """Get training session summary."""
        total = len(self.training_progress)
        completed = len([p for p in self.training_progress if p.status == 'completed'])
        failed = len([p for p in self.training_progress if p.status == 'failed'])
        
        return {
            'total_actions': total,
            'completed': completed,
            'failed': failed,
            'success_rate': (completed / total * 100) if total > 0 else 0,
            'is_complete': completed == total
        }
    
    def stop_training(self):
        """Stop current training session."""
        self.is_training = False
        if self.c:
            try:
                self.c.close()
            except:
                pass
        print("⏹️  训练会话已停止")
    
    def train_mc_action(self, status: str):
        """Control mental command action training."""
        if self.current_action_idx >= len(self.actions_to_train):
            # All actions trained, save profile
            print("🎉 所有动作训练完成！保存配置文件...")
            self.c.setup_profile(self.profile_name, 'save')
            return
        
        action = self.actions_to_train[self.current_action_idx]
        progress = self.training_progress[self.current_action_idx]
        
        # Update progress
        if status == 'start':
            progress.status = 'training'
            progress.start_time = time.time()
            progress.attempts += 1
            print(f"\\n🧠 开始训练: {progress.description} ({action.value})")
            print(f"   尝试次数: {progress.attempts}")
            print(f"   请专注想象执行该动作8秒钟...")
        
        print(f'train_mc_action: {action.value} : {status}')
        
        self.c.train_request(detection='mentalCommand',
                           action=action.value,
                           status=status)
        
        # Notify progress update
        if self.on_progress_update:
            self.on_progress_update(progress)
    
    # Cortex event callbacks
    def on_create_session_done(self, *args, **kwargs):
        """Handle session creation."""
        print('✅ BCI会话创建成功')
        self.c.query_profile()
    
    def on_query_profile_done(self, *args, **kwargs):
        """Handle profile query completion."""
        print('📋 查询Profile完成')
        self.profile_lists = kwargs.get('data')
        
        if self.profile_name in self.profile_lists:
            print(f"✅ Profile '{self.profile_name}' 已存在，加载中...")
            self.c.get_current_profile()
        else:
            print(f"📝 创建新Profile: {self.profile_name}")
            self.c.setup_profile(self.profile_name, 'create')
    
    def on_load_unload_profile_done(self, *args, **kwargs):
        """Handle profile load/unload completion."""
        is_loaded = kwargs.get('isLoaded')
        
        if is_loaded:
            print(f"✅ Profile '{self.profile_name}' 加载成功")
            print("📡 订阅训练事件流...")
            self.c.sub_request(['sys'])
        else:
            print(f"🔄 Profile '{self.profile_name}' 已卸载")
            self.profile_name = ''
            self.is_training = False
            self.c.close()
    
    def on_save_profile_done(self, *args, **kwargs):
        """Handle profile save completion."""
        print(f"💾 Profile '{self.profile_name}' 保存成功！")
        
        # Show final summary
        summary = self.get_training_summary()
        print(f"\\n🎯 训练完成摘要:")
        print(f"  ✅ 成功: {summary['completed']}/{summary['total_actions']}")
        print(f"  ❌ 失败: {summary['failed']}/{summary['total_actions']}")
        print(f"  📊 成功率: {summary['success_rate']:.1f}%")
        
        if self.on_training_complete:
            self.on_training_complete(summary)
        
        # Unload profile
        print("🔄 卸载Profile...")
        self.c.setup_profile(self.profile_name, 'unload')
    
    def on_new_sys_data(self, *args, **kwargs):
        """Handle system training events."""
        data = kwargs.get('data')
        train_event = data[1]
        
        if self.current_action_idx >= len(self.actions_to_train):
            return
            
        action = self.actions_to_train[self.current_action_idx]
        progress = self.training_progress[self.current_action_idx]
        
        print(f'📊 训练事件: {action.value} -> {train_event}')
        
        if train_event == 'MC_Succeeded':
            print("✅ 训练成功！你可以选择接受或重新训练")
            # Auto-accept for better user experience
            self.train_mc_action('accept')
            
        elif train_event == 'MC_Failed':
            print("❌ 训练失败，重新开始训练")
            progress.status = 'failed'
            self.train_mc_action('reject')
            
        elif train_event == 'MC_Completed':
            print(f"🎉 '{progress.description}' 训练完成！")
            progress.status = 'completed'
            progress.end_time = time.time()
            
            # Move to next action
            self.current_action_idx += 1
            self.train_mc_action('start')
            
        elif train_event == 'MC_Rejected':
            print("🔄 训练被拒绝，重新开始")
            # Reset and retry
            self.train_mc_action('start')
    
    def on_new_data_labels(self, *args, **kwargs):
        """Handle data labels subscription."""
        data = kwargs.get('data')
        print('📡 数据流订阅成功')
        
        if data['streamName'] == 'sys':
            print("🚀 开始训练第一个动作...")
            self.current_action_idx = 0
            self.train_mc_action('start')
    
    def on_inform_error(self, *args, **kwargs):
        """Handle Cortex errors."""
        error_data = kwargs.get('error_data')
        error_code = error_data['code']
        error_message = error_data['message']
        
        print(f"❌ Cortex错误: {error_message} (代码: {error_code})")
        
        if error_code == cortex.ERR_PROFILE_ACCESS_DENIED:
            print("🔌 访问被拒绝，断开头戴设备以修复此问题")
            self.c.disconnect_headset()

def interactive_training_session():
    """Interactive training session for testing."""
    print("🧠 Mental Command 交互式训练")
    print("=" * 40)
    
    # Get credentials
    client_id = input("请输入 Client ID: ").strip()
    client_secret = input("请输入 Client Secret: ").strip()
    
    if not client_id or not client_secret:
        print("❌ Client ID 和 Secret 不能为空")
        return
    
    # Initialize trainer
    try:
        trainer = MentalCommandTrainer(client_id, client_secret)
    except Exception as e:
        print(f"❌ 初始化训练器失败: {e}")
        return
    
    # Show current configuration
    trainer.config.print_summary()
    
    # Get profile name
    profile_name = input("\\n请输入Profile名称 (或回车使用默认): ").strip()
    if not profile_name:
        profile_name = "MindDaemon_Reminders"
    
    # Start training
    try:
        trainer.start_training_session(profile_name)
    except KeyboardInterrupt:
        print("\\n⏹️  用户中断训练")
        trainer.stop_training()
    except Exception as e:
        print(f"❌ 训练过程出错: {e}")
        trainer.stop_training()

if __name__ == "__main__":
    interactive_training_session()