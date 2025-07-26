#!/usr/bin/env python3
"""
RDK X5手势检测模块测试程序

该程序演示如何使用detect模块与RDK X5开发板通信，进行手势检测。

功能：
1. 连接到RDK X5开发板
2. 启动远程服务（ROS + Socket）
3. 接收手势检测结果
4. 解析并显示手势信息
"""

import time
import signal
import sys
from typing import Optional, Dict, Any

# 导入detect模块
from src.mind_daemon.detect import GestureDetector, SocketClient
from src.mind_daemon.detect.config import remote_config

# 手势映射表（与detect模块保持一致）
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

# 模式切换手势
MODE_GESTURES = {
    "ThumbUp": "work_mode",    # 工作模式
    "Mute": "silent_mode",     # 静音模式
    "Palm": "rest_mode"        # 休息模式
}

class GestureDetectionTester:
    """手势检测测试器"""
    
    def __init__(self):
        self.gesture_detector: Optional[GestureDetector] = None
        self.socket_client: Optional[SocketClient] = None
        self.running = False
        
        # 设置信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        # 显示配置信息
        print(f"📡 RDK X5配置:")
        print(f"   主机: {remote_config.host}")
        print(f"   用户: {remote_config.username}")
        print(f"   SSH端口: {remote_config.port}")
        print(f"   Socket端口: 8888")
        print(f"   脚本路径: {remote_config.script_path}")
    
    def _signal_handler(self, signum, frame):
        """处理中断信号"""
        print(f"\n🛑 接收到信号 {signum}，正在安全退出...")
        self.running = False
        self.cleanup()
        sys.exit(0)
    
    def setup_remote_service(self) -> bool:
        """设置远程服务连接"""
        print("🔧 初始化手势检测器...")
        self.gesture_detector = GestureDetector(remote_config)
        
        print(f"🌐 连接到RDK X5开发板 ({remote_config.host})...")
        if not self.gesture_detector.connect():
            print("❌ 无法连接到开发板")
            return False
        
        print("✅ 成功连接到开发板")
        
        print("🚀 启动远程服务...")
        if not self.gesture_detector.start_services():
            print("❌ 启动远程服务失败")
            return False
        
        print("✅ 远程服务启动成功")
        return True
    
    def setup_socket_client(self) -> bool:
        """设置Socket客户端"""
        print("🔌 初始化Socket客户端...")
        self.socket_client = SocketClient(
            host=remote_config.host,
            port=8888  # 从.env配置中读取的GESTURE_DETECTOR_PORT
        )
        
        print("🔗 测试Socket连接...")
        print("⚠️  注意: Socket服务需要远程服务先启动成功")
        
        # 等待一段时间让远程服务完全启动
        print("⏳ 等待远程服务启动完成...")
        time.sleep(3)
        
        if not self.socket_client.connect():
            print("❌ Socket连接失败 - 这是正常的，远程服务可能需要更多时间启动")
            print("💡 提示: 手势监控时会自动重试连接")
            return True  # 改为True，因为这不是致命错误
        
        print("✅ Socket连接成功")
        self.socket_client.disconnect()  # 测试完成后断开，等待实际使用时重连
        return True
    
    def check_service_status(self) -> Dict[str, Any]:
        """检查服务状态"""
        if not self.gesture_detector:
            return {"error": "手势检测器未初始化"}
        
        print("📊 检查服务状态...")
        status = self.gesture_detector.get_status()
        
        print("📋 服务状态:")
        print(f"  连接状态: {'🟢' if status.get('connected') else '🔴'}")
        print(f"  服务运行: {'🟢' if status.get('services_running') else '🔴'}")
        print(f"  退出代码: {status.get('exit_code', 'N/A')}")
        
        if status.get('output'):
            print(f"  输出信息: {status['output'].strip()}")
        if status.get('error'):
            print(f"  错误信息: {status['error'].strip()}")
        
        return status
    
    def parse_gesture_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """解析手势消息"""
        if not message or 'gestures' not in message:
            return None
        
        gestures = message['gestures']
        if not gestures:
            return None
        
        # 获取置信度最高的手势
        best_gesture = max(gestures, key=lambda g: g.get('confidence', 0))
        
        gesture_value = best_gesture.get('value')
        gesture_name = best_gesture.get('name', GESTURE_MAP.get(gesture_value, 'Unknown'))
        confidence = best_gesture.get('confidence', 0)
        timestamp = message.get('timestamp', time.time())
        
        return {
            'name': gesture_name,
            'value': gesture_value,
            'confidence': confidence,
            'timestamp': timestamp,
            'mode': MODE_GESTURES.get(gesture_name, 'unknown_mode')
        }
    
    def start_gesture_monitoring(self, max_gestures: int = 10):
        """开始手势监控"""
        print(f"👁️  开始手势监控 (最多接收 {max_gestures} 个手势)...")
        print("📝 支持的手势:")
        for value, name in GESTURE_MAP.items():
            mode = MODE_GESTURES.get(name, "无模式切换")
            print(f"  {name} ({value}) → {mode}")
        
        print("\n🎯 等待手势检测结果...")
        print("按 Ctrl+C 退出监控\n")
        
        self.running = True
        gesture_count = 0
        
        while self.running and gesture_count < max_gestures:
            try:
                # 连接Socket客户端，增加重试逻辑
                print(f"🔌 尝试连接到 {self.socket_client.host}:{self.socket_client.port}")
                
                if not self.socket_client.connect():
                    print("❌ Socket连接失败，尝试重连...")
                    if not self.socket_client.reconnect(max_retries=5):
                        print("❌ 多次重连失败")
                        print("💡 可能的原因:")
                        print("   1. 远程服务未启动或启动失败")
                        print("   2. 网络连接问题")
                        print("   3. 防火墙阻止连接")
                        print("   4. 端口配置错误")
                        
                        # 检查服务状态
                        print("🔍 检查远程服务状态...")
                        status = self.check_service_status()
                        if not status.get('services_running'):
                            print("🔧 尝试重启远程服务...")
                            if self.gesture_detector.restart_services():
                                print("✅ 远程服务重启成功，等待5秒后重试...")
                                time.sleep(5)
                                continue
                        print("❌ 无法建立连接，退出监控")
                        break
                
                # 等待接收手势消息
                print(f"⏳ 等待第 {gesture_count + 1} 个手势...")
                message = self.socket_client.wait_gesture()
                
                if message:
                    # 解析手势信息
                    gesture_info = self.parse_gesture_message(message)
                    
                    if gesture_info:
                        gesture_count += 1
                        timestamp = time.strftime(
                            '%H:%M:%S', 
                            time.localtime(gesture_info['timestamp'])
                        )
                        
                        print(f"✨ [{timestamp}] 检测到手势:")
                        print(f"   🤚 手势: {gesture_info['name']}")
                        print(f"   📊 置信度: {gesture_info['confidence']:.2f}")
                        print(f"   🔄 模式: {gesture_info['mode']}")
                        print(f"   📅 时间戳: {gesture_info['timestamp']}")
                        print("-" * 50)
                        
                        # 如果是模式切换手势，给出特殊提示
                        if gesture_info['mode'] != 'unknown_mode':
                            print(f"🎯 模式切换: → {gesture_info['mode']}")
                    else:
                        print("⚠️  接收到无效手势数据")
                else:
                    print("⏰ 接收手势超时或连接断开")
                    time.sleep(1)  # 短暂等待后重试
                
            except KeyboardInterrupt:
                print("\n🛑 用户中断监控")
                break
            except Exception as e:
                print(f"❌ 监控过程中出现错误: {e}")
                time.sleep(2)  # 等待后重试
        
        print(f"\n📊 监控结束，共检测到 {gesture_count} 个有效手势")
    
    def run_interactive_test(self):
        """运行交互式测试"""
        print("🎮 进入交互式测试模式")
        print("可用命令:")
        print("  status  - 检查服务状态")
        print("  restart - 重启远程服务")
        print("  monitor - 开始手势监控")
        print("  quit    - 退出程序")
        
        while True:
            try:
                cmd = input("\n请输入命令: ").strip().lower()
                
                if cmd == 'status':
                    self.check_service_status()
                elif cmd == 'restart':
                    if self.gesture_detector:
                        print("🔄 重启远程服务...")
                        if self.gesture_detector.restart_services():
                            print("✅ 服务重启成功")
                        else:
                            print("❌ 服务重启失败")
                elif cmd == 'monitor':
                    max_gestures = input("输入最大手势数量 [10]: ").strip()
                    try:
                        max_gestures = int(max_gestures) if max_gestures else 10
                    except ValueError:
                        max_gestures = 10
                    self.start_gesture_monitoring(max_gestures)
                elif cmd == 'quit':
                    break
                else:
                    print("❌ 未知命令")
                    
            except KeyboardInterrupt:
                print("\n🛑 退出交互模式")
                break
    
    def cleanup(self):
        """清理资源"""
        print("🧹 清理资源...")
        
        if self.socket_client:
            self.socket_client.disconnect()
        
        if self.gesture_detector:
            print("🛑 停止远程服务...")
            self.gesture_detector.stop_services()
            self.gesture_detector.disconnect()
        
        print("✅ 资源清理完成")

def main():
    """主函数"""
    print("🎯 RDK X5手势检测模块测试程序")
    print("=" * 50)
    print(f"📡 开发板地址: {remote_config.host}")
    print(f"👤 SSH用户: {remote_config.username}")
    print(f"🔧 脚本路径: {remote_config.script_path}")
    print("=" * 50)
    
    tester = GestureDetectionTester()
    
    try:
        # 设置远程服务
        if not tester.setup_remote_service():
            print("❌ 远程服务设置失败，程序退出")
            return
        
        # 设置Socket客户端
        if not tester.setup_socket_client():
            print("❌ Socket客户端设置失败，程序退出")
            return
        
        # 检查服务状态
        tester.check_service_status()
        
        # 询问用户运行模式
        print("\n🎮 选择运行模式:")
        print("1. 自动监控模式 (监控10个手势后自动退出)")
        print("2. 交互式测试模式 (手动控制)")
        
        choice = input("请选择 (1/2) [1]: ").strip() or "1"
        
        if choice == "1":
            tester.start_gesture_monitoring(10)
        else:
            tester.run_interactive_test()
            
    except Exception as e:
        print(f"❌ 程序运行出现错误: {e}")
    finally:
        tester.cleanup()
        print("👋 程序结束")

if __name__ == "__main__":
    main()