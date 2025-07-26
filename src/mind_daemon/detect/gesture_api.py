#!/usr/bin/env python3
"""
手势识别API封装
Gesture Recognition API Wrapper
"""

import threading
import time
import logging
from typing import Optional, Callable, Dict, Any

try:
    from .gesture_detector import GestureDetector
    from .socket_client import SocketClient
    from .config import remote_config
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from gesture_detector import GestureDetector
    from socket_client import SocketClient
    from config import remote_config

logger = logging.getLogger(__name__)

class GestureAPI:
    """手势识别API封装类"""
    
    def __init__(self, gesture_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        初始化手势识别API
        
        Args:
            gesture_callback: 手势检测回调函数，参数为手势数据字典
        """
        self.gesture_detector = GestureDetector(remote_config)
        self.socket_client = SocketClient()
        self.gesture_callback = gesture_callback
        
        self.running = False
        self.receiver_thread = None
        
        # 状态信息
        self.status = {
            "ssh_connected": False,
            "service_running": False,
            "socket_connected": False,
            "monitoring_active": False,
            "last_gesture": None,
            "error_message": None
        }
    
    def start(self) -> bool:
        """
        启动手势识别服务
        执行完整的操作流程：操作1 → 操作6 → socket实时接收
        
        Returns:
            bool: 启动是否成功
        """
        try:
            logger.info("🚀 启动手势识别API服务")
            
            # 操作1: 连接并启动服务
            logger.info("步骤1: SSH连接并启动服务")
            if not self.gesture_detector.connect():
                self.status["error_message"] = "SSH连接失败"
                logger.error("❌ SSH连接失败")
                return False
            
            self.status["ssh_connected"] = True
            logger.info("✅ SSH连接成功")
            
            if not self.gesture_detector.start_services():
                self.status["error_message"] = "服务启动失败"
                logger.error("❌ 服务启动失败")
                return False
            
            self.status["service_running"] = True
            logger.info("✅ 服务启动成功")
            
            # 等待服务完全启动
            time.sleep(2)
            
            # 操作6: 开始监控，间隔0.1秒
            logger.info("步骤2: 启动监控（间隔0.1秒）")
            self.gesture_detector.start_monitoring(interval=0.1)
            self.status["monitoring_active"] = True
            logger.info("✅ 监控启动成功")
            
            # 等待监控启动
            time.sleep(1)
            
            # 步骤3: 启动socket实时接收线程
            logger.info("步骤3: 启动socket实时接收")
            self.running = True
            self.receiver_thread = threading.Thread(target=self._socket_receiver_loop, daemon=True)
            self.receiver_thread.start()
            logger.info("✅ Socket接收线程启动成功")
            
            logger.info("🎉 手势识别API服务启动完成")
            return True
            
        except Exception as e:
            self.status["error_message"] = f"启动异常: {e}"
            logger.error(f"❌ 手势识别API启动失败: {e}")
            return False
    
    def stop(self):
        """停止手势识别服务"""
        logger.info("🛑 停止手势识别API服务")
        
        try:
            # 停止接收线程
            self.running = False
            if self.receiver_thread:
                self.receiver_thread.join(timeout=2)
            
            # 停止监控
            if self.status["monitoring_active"]:
                self.gesture_detector.stop_monitoring()
                self.status["monitoring_active"] = False
            
            # 断开连接
            if self.status["ssh_connected"]:
                self.gesture_detector.disconnect()
                self.status["ssh_connected"] = False
            
            if self.status["socket_connected"]:
                self.socket_client.disconnect()
                self.status["socket_connected"] = False
            
            self.status["service_running"] = False
            logger.info("✅ 手势识别API服务已停止")
            
        except Exception as e:
            logger.error(f"❌ 停止服务时发生错误: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            Dict: 状态信息字典
        """
        return self.status.copy()
    
    def set_gesture_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """设置手势检测回调函数"""
        self.gesture_callback = callback
    
    def _socket_receiver_loop(self):
        """Socket实时接收循环线程"""
        logger.info("🎯 Socket接收线程开始运行")
        
        while self.running:
            try:
                # 确保socket连接
                if not self.socket_client.is_connected():
                    logger.debug("🔌 尝试连接Socket...")
                    if self.socket_client.connect():
                        self.status["socket_connected"] = True
                        logger.info("✅ Socket连接成功")
                    else:
                        self.status["socket_connected"] = False
                        logger.warning("❌ Socket连接失败，1秒后重试")
                        time.sleep(1)
                        continue
                
                # 阻塞式接收手势数据
                gesture_data = self.socket_client.wait_gesture()
                
                if gesture_data:
                    self.status["last_gesture"] = gesture_data
                    logger.info(f"🎯 检测到手势: {gesture_data}")
                    
                    # 调用回调函数
                    if self.gesture_callback:
                        try:
                            self.gesture_callback(gesture_data)
                        except Exception as e:
                            logger.error(f"❌ 手势回调函数执行失败: {e}")
                    
                    # 重新连接以接收下一个手势
                    self.socket_client.connect()
                
            except Exception as e:
                self.status["socket_connected"] = False
                logger.debug(f"Socket接收错误: {e}")
                
                # 尝试重新连接
                try:
                    self.socket_client.connect()
                except:
                    pass
                time.sleep(0.5)
        
        logger.info("🛑 Socket接收线程已停止")

# 便捷函数
def create_gesture_api(gesture_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> GestureAPI:
    """
    创建手势识别API实例
    
    Args:
        gesture_callback: 手势检测回调函数
        
    Returns:
        GestureAPI: API实例
    """
    return GestureAPI(gesture_callback)

# 测试用例
if __name__ == "__main__":
    def test_callback(gesture_data):
        print(f"🎯 手势回调: {gesture_data}")
    
    api = create_gesture_api(test_callback)
    
    try:
        if api.start():
            print("✅ API启动成功，等待手势...")
            while True:
                status = api.get_status()
                print(f"📊 状态: {status}")
                time.sleep(5)
        else:
            print("❌ API启动失败")
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    finally:
        api.stop()
        print("👋 测试结束")