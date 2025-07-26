"""
手势环境协调器 - 连接手势检测与环境控制的桥梁

功能：
- 监听手势检测结果
- 协调环境切换请求
- 管理30秒全局冷却时间
- 提供统一的环境控制接口

作者：Mind Daemon Project
"""

import time
import threading
import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass

from .environment_agent import EnvironmentAgent
from ..detect.gesture_detector import GestureDetector, EnhancedGestureDetector
from ..detect.socket_client import SocketClient
from ..detect.config import remote_config

# 配置日志
logger = logging.getLogger(__name__)

@dataclass
class GestureEvent:
    """手势事件数据类"""
    gesture_name: str
    mode: str
    timestamp: datetime
    confidence: float = 1.0

class GestureEnvironmentCoordinator:
    """手势环境协调器 - 统一管理手势检测和环境控制"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化协调器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 初始化环境控制智能体
        self.environment_agent = EnvironmentAgent(config)
        
        # 初始化SSH服务管理器（管理远程服务）
        self.ssh_service_manager = GestureDetector(remote_config)
        
        # 初始化增强手势检测器（处理Socket通信和手势识别）
        gesture_host = self.config.get('gesture_host', '172.20.10.2')
        gesture_port = self.config.get('gesture_port', 8888)
        self.gesture_detector = EnhancedGestureDetector(gesture_host, gesture_port)
        
        # 设置手势回调
        self.gesture_detector.set_gesture_callback(self._on_gesture_detected)
        
        # SSH连接状态
        self.ssh_connected = False
        
        # 运行状态
        self.is_running = False
        
        # 事件统计
        self.gesture_events = []
        self.max_events_history = 50
        
        # 外部回调函数
        self.environment_change_callback: Optional[Callable] = None
        
        logger.info("手势环境协调器初始化完成")
    
    def set_environment_change_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        设置环境变化回调函数
        
        Args:
            callback: 环境变化时的回调函数，参数为环境控制结果
        """
        self.environment_change_callback = callback
        logger.info("环境变化回调函数已设置")
    
    def start_monitoring(self):
        """开始监控手势并协调环境控制"""
        if self.is_running:
            logger.warning("协调器已在运行中")
            return False
        
        try:
            logger.info("正在启动手势环境协调器...")
            
            # 步骤1: 建立SSH连接到远程设备
            logger.info("建立SSH连接到远程手势检测设备...")
            if not self.ssh_service_manager.connect():
                logger.error("无法建立SSH连接到手势检测设备")
                return False
            
            self.ssh_connected = True
            logger.info("SSH连接建立成功")
            
            # 步骤2: 启动远程服务
            logger.info("启动远程手势检测服务...")
            if not self.ssh_service_manager.start_services():
                logger.error("无法启动远程手势检测服务")
                return False
            
            logger.info("远程手势检测服务启动成功")
            
            # 步骤3: 开始SSH服务监控（保持服务运行）
            self.ssh_service_manager.start_monitoring()
            
            # 步骤4: 启动Socket手势检测器
            logger.info("启动Socket手势检测器...")
            self.gesture_detector.start_monitoring()
            
            self.is_running = True
            logger.info("手势环境协调器启动成功")
            
            return True
            
        except Exception as e:
            logger.error(f"启动手势环境协调器失败: {e}")
            self.ssh_connected = False
            return False
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_running:
            return
        
        try:
            self.is_running = False
            
            # 停止Socket手势检测器
            if hasattr(self.gesture_detector, 'stop_monitoring'):
                try:
                    self.gesture_detector.stop_monitoring()
                    logger.info("Socket手势检测器已停止")
                except Exception as e:
                    logger.warning(f"停止Socket手势检测器失败: {e}")
            
            # 停止SSH服务监控
            if hasattr(self.ssh_service_manager, 'stop_monitoring'):
                try:
                    self.ssh_service_manager.stop_monitoring()
                    logger.info("SSH服务监控已停止")
                except Exception as e:
                    logger.warning(f"停止SSH服务监控失败: {e}")
            
            # 停止远程服务
            if self.ssh_connected:
                try:
                    self.ssh_service_manager.stop_services()
                    logger.info("远程服务已停止")
                except Exception as e:
                    logger.warning(f"停止远程服务失败: {e}")
            
            # 断开SSH连接
            if self.ssh_connected:
                try:
                    self.ssh_service_manager.disconnect()
                    self.ssh_connected = False
                    logger.info("SSH连接已断开")
                except Exception as e:
                    logger.warning(f"断开SSH连接失败: {e}")
            
            logger.info("手势环境协调器已停止")
            
        except Exception as e:
            logger.error(f"停止手势环境协调器失败: {e}")
    
    def _on_gesture_detected(self, gesture_name: str, mode: str):
        """
        手势检测回调函数
        
        Args:
            gesture_name: 手势名称
            mode: 模式名称 (work_mode, rest_mode, silent_mode, unknown_mode)
        """
        try:
            current_time = datetime.now()
            
            # 记录手势事件
            event = GestureEvent(
                gesture_name=gesture_name,
                mode=mode,
                timestamp=current_time
            )
            
            self.gesture_events.append(event)
            if len(self.gesture_events) > self.max_events_history:
                self.gesture_events.pop(0)
            
            logger.info(f"检测到手势: {gesture_name} -> {mode}")
            
            # 如果是unknown_mode，不执行环境控制
            if mode == 'unknown_mode':
                logger.info(f"手势 {gesture_name} 不触发环境变化")
                return
            
            # 调用环境控制智能体处理手势模式
            result = self.environment_agent.handle_gesture_mode(
                gesture_mode=mode,
                gesture_name=gesture_name,
                confidence=1.0
            )
            
            # 记录结果
            logger.info(f"环境控制结果: {result.get('message', 'unknown')}")
            
            # 如果设置了外部回调，调用它
            if self.environment_change_callback:
                try:
                    self.environment_change_callback(result)
                except Exception as e:
                    logger.error(f"调用环境变化回调失败: {e}")
            
        except Exception as e:
            logger.error(f"处理手势检测事件失败: {e}")
    
    def manual_environment_switch(self, mode: str, reason: str = "manual") -> Dict[str, Any]:
        """
        手动触发环境切换
        
        Args:
            mode: 环境模式 (work_mode, rest_mode, silent_mode)
            reason: 切换原因
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"手动环境切换: {mode} (原因: {reason})")
            
            result = self.environment_agent.handle_gesture_mode(
                gesture_mode=mode,
                gesture_name=f"manual_{reason}",
                confidence=1.0
            )
            
            # 调用外部回调
            if self.environment_change_callback:
                try:
                    self.environment_change_callback(result)
                except Exception as e:
                    logger.error(f"调用环境变化回调失败: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"手动环境切换失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def force_environment_analysis(self, state: str, confidence: float, 
                                 metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        强制执行基于状态的环境分析（忽略冷却时间）
        
        Args:
            state: 精神状态
            confidence: 置信度
            metrics: 指标
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            logger.info(f"强制环境分析: {state} (置信度: {confidence:.2f})")
            
            result = self.environment_agent.analyze_and_control(
                current_state=state,
                confidence=confidence,
                metrics=metrics,
                force_execute=True
            )
            
            # 调用外部回调
            if self.environment_change_callback:
                try:
                    self.environment_change_callback(result)
                except Exception as e:
                    logger.error(f"调用环境变化回调失败: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"强制环境分析失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取协调器状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        try:
            # 获取SSH服务状态
            ssh_status = {}
            if self.ssh_connected:
                try:
                    ssh_status = self.ssh_service_manager.get_status()
                except Exception as e:
                    logger.warning(f"获取SSH状态失败: {e}")
                    ssh_status = {'error': str(e)}
            
            return {
                'is_running': self.is_running,
                'ssh_connected': self.ssh_connected,
                'ssh_status': ssh_status,
                'timestamp': datetime.now().isoformat(),
                'gesture_events_count': len(self.gesture_events),
                'recent_gestures': [
                    {
                        'gesture': event.gesture_name,
                        'mode': event.mode,
                        'timestamp': event.timestamp.isoformat()
                    }
                    for event in self.gesture_events[-5:]  # 最近5个手势
                ],
                'environment_switch_status': self.environment_agent.get_environment_switch_status(),
                'current_environment': self.environment_agent.get_current_environment_state(),
                'gesture_mode_info': self.environment_agent.get_gesture_mode_info()
            }
            
        except Exception as e:
            logger.error(f"获取协调器状态失败: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_cooldown_status(self) -> Dict[str, Any]:
        """
        获取冷却状态
        
        Returns:
            Dict[str, Any]: 冷却状态信息
        """
        try:
            is_allowed, remaining_time = self.environment_agent.is_environment_switch_allowed()
            
            return {
                'is_switch_allowed': is_allowed,
                'remaining_seconds': remaining_time,
                'cooldown_duration': self.environment_agent.environment_switch_cooldown,
                'last_switch_time': datetime.fromtimestamp(
                    self.environment_agent.last_environment_switch_time
                ).isoformat() if self.environment_agent.last_environment_switch_time else None
            }
            
        except Exception as e:
            logger.error(f"获取冷却状态失败: {e}")
            return {'error': str(e)}
    
    def cleanup(self):
        """清理资源"""
        try:
            self.stop_monitoring()
            self.environment_agent.cleanup()
            logger.info("手势环境协调器资源清理完成")
            
        except Exception as e:
            logger.error(f"清理协调器资源失败: {e}")

def main():
    """测试函数"""
    try:
        print("🤝 手势环境协调器测试")
        
        # 创建协调器
        config = {
            'gesture_host': '172.20.10.2',
            'gesture_port': 8888
        }
        
        coordinator = GestureEnvironmentCoordinator(config)
        
        # 设置环境变化回调
        def on_environment_change(result):
            print(f"🌟 环境变化回调: {result.get('message', 'unknown')}")
            if result.get('actions_performed'):
                for action in result['actions_performed']:
                    print(f"  • {action}")
        
        coordinator.set_environment_change_callback(on_environment_change)
        
        # 测试手动环境切换
        print(f"\n{'='*50}")
        print("测试手动环境切换")
        
        modes = ['work_mode', 'rest_mode', 'silent_mode']
        for mode in modes:
            print(f"\n切换到 {mode}")
            result = coordinator.manual_environment_switch(mode, f"test_{mode}")
            print(f"结果: {result.get('message', 'unknown')}")
            
            # 显示冷却状态
            cooldown = coordinator.get_cooldown_status()
            if not cooldown['is_switch_allowed']:
                print(f"冷却中，剩余: {cooldown['remaining_seconds']:.1f}秒")
            
            # 等待一段时间测试冷却机制
            if mode != modes[-1]:  # 不是最后一个模式
                print("等待5秒测试冷却机制...")
                time.sleep(5)
        
        # 显示最终状态
        print(f"\n{'='*50}")
        print("协调器状态:")
        status = coordinator.get_status()
        print(f"运行状态: {status['is_running']}")
        print(f"手势事件数: {status['gesture_events_count']}")
        
        env_status = status['environment_switch_status']
        print(f"环境切换允许: {env_status['is_switch_allowed']}")
        if not env_status['is_switch_allowed']:
            print(f"剩余冷却时间: {env_status['remaining_cooldown_seconds']:.1f}秒")
        
        print(f"\n✅ 测试完成")
        
        # 清理资源
        coordinator.cleanup()
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()