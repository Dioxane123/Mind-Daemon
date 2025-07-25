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
"""Gesture detection using development board and camera - placeholder."""

from config import SSHConfig, remote_config

import paramiko
import time
import threading
import json
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from pathlib import Path
try:
    from loguru import logger
    islogger = True
except:
    islogger = False

class RemoteServiceController:
    """Controller remote service"""

    def __init__(self, config: SSHConfig):
        """remote configs"""
        self.config = config
        self.ssh_client: Optional[paramiko.SSHClient] = None
        self.is_monitoring = False
        self.is_connected = False
    
    def connect(self) -> bool:
        """connect to remote device"""
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if islogger:
                logger.info(f"正在连接至开发板{self.config.host}...")
            else:
                print(f"正在连接至开发板{self.config.host}...")
            self.ssh_client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout
            )
            self.is_connected = True
            if islogger:
                logger.info("成功连接至开发板！")
            else:
                print("成功连接至开发板！")
            return True
        except paramiko.AuthenticationException:
            if islogger:
                logger.error("SSH认证失败，请检查用户名或密码。")
            else:
                print("SSH认证失败，请检查用户名或密码。")
            return False
        except paramiko.SSHException as e:
            if islogger:
                logger.error(f"SSH连接错误: {e}")
            else:
                print(f"SSH连接错误: {e}")
            return False
        except Exception as e:
            if islogger:
                logger.error(f"遇到错误: {e}")
            else:
                print(f"遇到错误: {e}")
            return False
    
    def disconnect(self) -> None:
        """disconnect to remote device"""
        if self.ssh_client:
            self.ssh_client.close()
            self.is_connected = True
            if islogger:
                logger.info("已断开ssh连接")
            else:
                print("已断开ssh连接")
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[int, str, str]:
        """excute command on remote device"""
        if not self.is_connected:
            return -1, "", "SSH未连接"
        
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command, timeout=timeout)
            
            # 等待命令完成
            exit_status = stdout.channel.recv_exit_status()
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            return exit_status, output, error
            
        except Exception as e:
            return -1, "", str(e)
    
    def start_services(self) -> bool:
        """start service on remote device"""
        if islogger:
            logger.info("启动远程服务...")
        else:
            print("启动远程服务...")
        
        exit_code, output, error = self.execute_command(f"bash {self.config.script_path} start")
        
        if exit_code == 0:
            if islogger:
                logger.info("服务启动成功")
            else:
                print("服务启动成功")
            if output:
                if islogger:
                    logger.info(f"输出: {output}")
                else:
                    print(f"输出: {output}")
            return True
        else:
            if islogger:
                logger.error("服务启动失败")
            else:
                print("服务启动失败")
            if error:
                if islogger:
                    logger.error(f"错误信息: {error}")
                else:
                    print(f"错误信息: {error}")
            return False
    
    def stop_services(self) -> bool:
        """stop all services on remote device"""
        if islogger:
            logger.info("停止远程服务...")
        else:
            print("停止远程服务...")
        
        exit_code, output, error = self.execute_command(f"bash {self.config.script_path} stop")
        
        if exit_code == 0:
            if islogger:
                logger.info("服务已停止")
            else:
                print("服务已停止")
            return True
        else:
            if islogger:
                logger.error("停止服务失败")
            else:
                print("停止服务失败")
            if error:
                if islogger:
                    logger.error(f"错误信息: {error}")
                else:
                    print(f"错误信息: {error}")
            return False
    
    def restart_services(self) -> bool:
        """restart all services on remote device"""
        if islogger:
            logger.info("重启远程服务...")
        else:
            print("重启远程服务...")
        
        exit_code, output, error = self.execute_command(f"bash {self.config.script_path} restart")
        
        if exit_code == 0:
            if islogger:
                logger.info("服务重启成功")
            else:
                print("服务重启成功")
            return True
        else:
            if islogger:
                logger.error("服务重启失败")
            else:
                print("服务重启失败")
            if error:
                if islogger:
                    logger.error(f"错误信息: {error}")
                else:
                    print(f"错误信息: {error}")
            return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """get the status of services on remote device"""
        exit_code, output, error = self.execute_command(f"bash {self.config.script_path} status")
        
        status_info = {
            "connected": self.is_connected,
            "exit_code": exit_code,
            "output": output,
            "error": error,
            "services_running": False
        }
        
        if exit_code == 0 and "运行中" in output:
            status_info["services_running"] = True
        
        return status_info


class GestureDetector:
    """Handles gesture detection during relax mode."""

    def __init__(self, remote_config: SSHConfig):
        self.monitoring = False
        self.controller = RemoteServiceController(remote_config)
        self.auto_reconnect = True
        self.status_monitor_thread = None
        
    def connect(self) -> bool:
        return self.controller.connect()
    
    def disconnect(self) -> bool:
        self.monitoring = False
        return self.controller.disconnect()
    
    def start_services(self) -> bool:
        """start services"""
        if not self.controller.is_connected:
            if islogger:
                logger.error("未连接到开发板")
            else:
                print("未连接到开发板")
            return False
        
        return self.controller.start_services()
    
    def stop_services(self) -> bool:
        """stop services"""
        if not self.controller.is_connected:
            if islogger:
                logger.error("未连接到开发板")
            else:
                print("未连接到开发板")
            return False
        
        return self.controller.stop_services()

    def restart_services(self) -> bool:
        """restart services"""
        if not self.controller.is_connected:
            if islogger:
                logger.error("未连接到开发板")
            else:
                print("未连接到开发板")
            return False
        
        return self.controller.restart_services()
    
    def get_status(self) -> Dict[str, Any]:
        """get status of services"""
        if not self.controller.is_connected:
            return {"connected": False, "error": "未连接到开发板"}
        
        return self.controller.get_service_status()

    def start_monitoring(self, interval: int = 5):
        """Start continuous monitoring."""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.status_monitor_thread = threading.Thread(
            target=self._monitor_status, 
            args=(interval,),
            daemon=True
        )
        self.status_monitor_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring."""
        self.monitoring = False
        if self.status_monitor_thread:
            self.status_monitor_thread.join(timeout=5)
        if islogger:
            logger.info("状态监控已停止")
        else:
            print("状态监控已停止")
        
    # def detect_gesture(self) -> str:
    #     """Detect and return current gesture."""
    #     pass

    def _monitor_status(self, interval: int):
        """monitor thread"""
        while self.monitoring:
            try:
                if self.controller.is_connected:
                    status = self.get_status()
                    if status.get("services_running"):
                        if islogger:
                            logger.info("服务运行正常")
                        else:
                            print("服务运行正常")
                    else:
                        if islogger:
                            logger.warning("服务状态异常")
                        else:
                            print("服务状态异常")
                        if self.auto_reconnect:
                            if islogger:
                                logger.warning("尝试重启服务...")
                            else:
                                print("尝试重启服务...")
                            self.restart_services()
                else:
                    if islogger:
                        logger.error("连接断开")
                    else:
                        print("连接断开")
                    if self.auto_reconnect:
                        print("尝试重新连接...")
                        if self.connect():
                            self.start_services()
                
                time.sleep(interval)
                
            except Exception as e:
                if islogger:
                    logger.error(f"监控错误: {e}")
                else:
                    print(f"监控错误: {e}")
                time.sleep(interval)

if __name__ == "__main__":
    manager = GestureDetector(remote_config)
    
    print("🎯 手势识别服务远程控制器")
    print("=" * 50)
    
    try:
        # 连接到开发板
        if not manager.connect():
            print("❌ 无法连接到开发板，程序退出")
        
        # 交互式菜单
        while True:
            print("\n📋 可用命令:")
            print("1. start    - 启动服务")
            print("2. stop     - 停止服务")
            print("3. restart  - 重启服务")
            print("4. status   - 查看状态")
            print("5. logs     - 查看日志")
            print("6. monitor  - 开始监控")
            print("7. quit     - 退出程序")
            
            choice = input("\n请选择操作 (1-7): ").strip()
            
            if choice == "1" or choice.lower() == "start":
                manager.start_services()
            elif choice == "2" or choice.lower() == "stop":
                manager.stop_services()
            elif choice == "3" or choice.lower() == "restart":
                manager.restart_services()
            elif choice == "4" or choice.lower() == "status":
                status = manager.get_status()
                print(f"状态信息: {status}")
            elif choice == "5" or choice.lower() == "logs":
                log_type = input("选择日志类型 (ros/socket/all) [all]: ").strip() or "all"
                manager.show_logs(log_type)
            elif choice == "6" or choice.lower() == "monitor":
                if not manager.monitoring:
                    interval = input("监控间隔(秒) [10]: ").strip()
                    try:
                        interval = int(interval) if interval else 10
                    except ValueError:
                        interval = 10
                    manager.start_monitoring(interval)
                else:
                    print("监控已在运行中")
            elif choice == "7" or choice.lower() == "quit":
                break
            else:
                print("❌ 无效选择")
    
    except KeyboardInterrupt:
        print("\n🛑 用户中断")
    finally:
        print("🧹 清理资源...")
        manager.stop_services()
        manager.disconnect()
        print("👋 程序结束")