"""Enhanced gesture detection using socket communication with RDK board."""

import threading
import time
from typing import Optional, Callable, Dict, Any
from .socket_client import SocketClient

# 手势映射表
GESTURE_MAP = {
    2: "ThumbUp",     # 竖起大拇指 - 切换到工作状态
    3: "Victory",     # "V"手势
    4: "Mute",        # "嘘"手势 - 静音
    5: "Palm",        # 手掌 - 切换休息状态
    11: "Okay",       # OK手势
    12: "ThumbLeft",  # 大拇指向左
    13: "ThumbRight", # 大拇指向右
    14: "Awesome"     # 666手势
}

# 支持的模式切换手势
MODE_GESTURES = {
    "ThumbUp": "work_mode",    # 工作模式
    "Mute": "silent_mode",     # 静音模式
    "Palm": "rest_mode"        # 休息模式
}

class EnhancedGestureDetector:
    """增强版手势检测器，支持socket通信和模式切换."""
    
    def __init__(self, host: str = "172.20.10.2", port: int = 8888):
        self.socket_client = SocketClient(host, port)
        self.is_monitoring = False
        self.monitoring_thread = None
        self.gesture_callback: Optional[Callable[[str, str], None]] = None
        self.last_gesture = None
        self.last_gesture_time = 0
        self.gesture_cooldown = 2.0  # 2秒冷却时间，避免重复触发
        
    def set_gesture_callback(self, callback: Callable[[str, str], None]):
        """设置手势回调函数.
        
        Args:
            callback: 回调函数，参数为(gesture_name, mode)
        """
        self.gesture_callback = callback
        
    def start_monitoring(self):
        """开始连续手势监控."""
        if self.is_monitoring:
            print("⚠️  手势检测已在运行")
            return
            
        self.is_monitoring = True
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        print("✅ 开始手势检测监控")
        
    def stop_monitoring(self):
        """停止手势监控."""
        self.is_monitoring = False
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=1)
        self.socket_client.disconnect()
        print("⏹️  手势检测监控已停止")
        
    def _monitoring_loop(self):
        """手势监控主循环."""
        while self.is_monitoring:
            try:
                # 尝试连接并接收手势数据
                if not self.socket_client.is_connected():
                    if not self.socket_client.connect():
                        print("🔄 等待手势检测服务器连接...")
                        time.sleep(5)
                        continue
                
                # 等待手势数据
                gesture_data = self.socket_client.wait_gesture()
                
                if gesture_data:
                    self._process_gesture_data(gesture_data)
                else:
                    # 没有数据，等待一下再继续
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"⚠️  手势监控出错: {e}")
                time.sleep(2)
                
    def _process_gesture_data(self, gesture_data: Dict[str, Any]):
        """处理接收到的手势数据."""
        try:
            # 解析手势数据
            gesture_id = gesture_data.get('gesture', 0)
            confidence = gesture_data.get('confidence', 0.0)
            timestamp = gesture_data.get('timestamp', time.time())
            
            # 转换为手势名称
            gesture_name = GESTURE_MAP.get(gesture_id, f"Unknown_{gesture_id}")
            
            # 检查冷却时间
            current_time = time.time()
            if (gesture_name == self.last_gesture and 
                current_time - self.last_gesture_time < self.gesture_cooldown):
                return
                
            # 检查是否为支持的模式切换手势
            if gesture_name in MODE_GESTURES:
                mode = MODE_GESTURES[gesture_name]
                
                print(f"👋 检测到手势: {gesture_name} -> {mode} (置信度: {confidence:.2f})")
                
                # 更新最后手势信息
                self.last_gesture = gesture_name
                self.last_gesture_time = current_time
                
                # 调用回调函数
                if self.gesture_callback:
                    self.gesture_callback(gesture_name, mode)
            else:
                print(f"👋 检测到手势: {gesture_name} (置信度: {confidence:.2f}) - 无对应模式")
                
        except Exception as e:
            print(f"⚠️  处理手势数据失败: {e}")
            
    def detect_single_gesture(self, timeout: float = 5.0) -> Optional[tuple]:
        """检测单个手势 (阻塞式).
        
        Args:
            timeout: 超时时间
            
        Returns:
            (gesture_name, mode) 或 None
        """
        try:
            if not self.socket_client.connect():
                print("❌ 无法连接到手势检测服务器")
                return None
                
            # 设置socket超时
            self.socket_client.socket.settimeout(timeout)
            
            gesture_data = self.socket_client.wait_gesture()
            
            if gesture_data:
                gesture_id = gesture_data.get('gesture', 0)
                gesture_name = GESTURE_MAP.get(gesture_id, f"Unknown_{gesture_id}")
                
                if gesture_name in MODE_GESTURES:
                    mode = MODE_GESTURES[gesture_name]
                    return (gesture_name, mode)
                    
            return None
            
        except Exception as e:
            print(f"⚠️  单次手势检测失败: {e}")
            return None
        finally:
            self.socket_client.disconnect()
            
    def get_supported_gestures(self) -> Dict[str, str]:
        """获取支持的手势和对应模式."""
        return MODE_GESTURES.copy()
        
    def is_connected(self) -> bool:
        """检查是否连接到手势检测服务器."""
        return self.socket_client.is_connected()

# 保持向后兼容
class GestureDetector(EnhancedGestureDetector):
    """向后兼容的手势检测器."""
    pass