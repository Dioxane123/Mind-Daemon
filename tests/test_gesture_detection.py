#!/usr/bin/env python3
"""
测试手势检测模块的完整功能
Test program for the gesture detection module functionality.
"""

import sys
import time
import threading
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from mind_daemon.detect.gesture_detector import GestureDetector, EnhancedGestureDetector, GESTURE_MAP, MODE_GESTURES
from mind_daemon.detect.socket_client import SocketClient
from mind_daemon.detect.config import remote_config

class GestureDetectionTester:
    """手势检测模块测试器"""
    
    def __init__(self):
        print("🎯 Mind Daemon 手势检测模块测试器")
        print("=" * 60)
        print(f"📡 远程设备配置:")
        print(f"   主机: {remote_config.host}")
        print(f"   用户: {remote_config.username}")
        print(f"   端口: {remote_config.port}")
        print(f"   脚本路径: {remote_config.script_path}")
        print("=" * 60)
        
        self.gesture_detector = None
        self.socket_client = None
        self.enhanced_detector = None
        
    def test_ssh_connection(self):
        """测试 SSH 连接"""
        print("\n🔗 测试 1: SSH 连接测试")
        print("-" * 30)
        
        try:
            self.gesture_detector = GestureDetector(remote_config)
            
            print("⏳ 尝试连接到 RDK X5 开发板...")
            if self.gesture_detector.connect():
                print("✅ SSH 连接成功!")
                return True
            else:
                print("❌ SSH 连接失败!")
                return False
                
        except Exception as e:
            print(f"❌ 连接异常: {e}")
            return False
    
    def test_service_management(self):
        """测试服务管理功能"""
        print("\n⚙️  测试 2: 服务管理测试")
        print("-" * 30)
        
        if not self.gesture_detector:
            print("❌ 需要先建立 SSH 连接")
            return False
            
        try:
            # 测试获取服务状态
            print("📊 获取服务状态...")
            status = self.gesture_detector.get_status()
            print(f"状态信息: {status}")
            
            # 测试启动服务
            print("🚀 启动远程服务...")
            if self.gesture_detector.start_services():
                print("✅ 服务启动成功!")
                time.sleep(2)  # 等待服务完全启动
                
                # 再次检查状态
                status = self.gesture_detector.get_status()
                print(f"启动后状态: {status}")
                
                return True
            else:
                print("❌ 服务启动失败!")
                return False
                
        except Exception as e:
            print(f"❌ 服务管理异常: {e}")
            return False
    
    def test_socket_connection(self):
        """测试 Socket 连接"""
        print("\n🔌 测试 3: Socket 连接测试")
        print("-" * 30)
        
        try:
            self.socket_client = SocketClient()
            
            print("⏳ 尝试连接到 Socket 服务...")
            if self.socket_client.connect():
                print("✅ Socket 连接成功!")
                print(f"连接状态: {self.socket_client.is_connected()}")
                return True
            else:
                print("❌ Socket 连接失败!")
                print("💡 提示: 请确保远程服务已启动")
                return False
                
        except Exception as e:
            print(f"❌ Socket 连接异常: {e}")
            return False
    
    def test_gesture_receiving(self, timeout=10):
        """测试手势接收功能"""
        print(f"\n👋 测试 4: 手势接收测试 (超时: {timeout}秒)")
        print("-" * 30)
        
        if not self.socket_client or not self.socket_client.is_connected():
            print("❌ 需要先建立 Socket 连接")
            return False
        
        try:
            print("👀 等待手势输入...")
            print("💡 请在摄像头前做手势，支持的手势:")
            for value, name in GESTURE_MAP.items():
                mode = MODE_GESTURES.get(name, "无对应模式")
                print(f"   {name} (值: {value}) -> {mode}")
            
            # 设置超时
            import socket
            self.socket_client.socket.settimeout(timeout)
            
            gesture_data = self.socket_client.wait_gesture()
            
            if gesture_data:
                print("✅ 成功接收到手势数据!")
                print(f"📊 手势信息: {gesture_data}")
                
                # 解析手势信息
                if 'gestures' in gesture_data and gesture_data['gestures']:
                    gesture = gesture_data['gestures'][0]
                    gesture_name = gesture.get('name', 'Unknown')
                    confidence = gesture.get('confidence', 0)
                    value = gesture.get('value', 0)
                    
                    print(f"🎯 识别结果:")
                    print(f"   手势名称: {gesture_name}")
                    print(f"   置信度: {confidence}")
                    print(f"   手势值: {value}")
                    
                    # 检查是否为模式切换手势
                    if gesture_name in MODE_GESTURES:
                        mode = MODE_GESTURES[gesture_name]
                        print(f"🔄 触发模式切换: {mode}")
                
                return True
            else:
                print("⏰ 超时或未接收到手势数据")
                return False
                
        except Exception as e:
            print(f"❌ 手势接收异常: {e}")
            return False
    
    def test_enhanced_detector(self):
        """测试增强版手势检测器"""
        print("\n🚀 测试 5: 增强版手势检测器")
        print("-" * 30)
        
        try:
            self.enhanced_detector = EnhancedGestureDetector()
            
            # 设置手势回调
            def gesture_callback(gesture_name, mode):
                print(f"🎯 检测到手势: {gesture_name} -> 模式: {mode}")
            
            self.enhanced_detector.set_gesture_callback(gesture_callback)
            
            print("🔄 启动连续监控...")
            self.enhanced_detector.start_monitoring()
            
            print("👀 监控中... (10秒后自动停止)")
            time.sleep(10)
            
            self.enhanced_detector.stop_monitoring()
            print("✅ 增强版检测器测试完成")
            return True
            
        except Exception as e:
            print(f"❌ 增强版检测器异常: {e}")
            return False
    
    def test_service_monitoring(self, duration=10):
        """测试服务监控功能"""
        print(f"\n📊 测试 6: 服务监控测试 ({duration}秒)")
        print("-" * 30)
        
        if not self.gesture_detector:
            print("❌ 需要先建立连接")
            return False
        
        try:
            print("🔄 启动服务监控...")
            self.gesture_detector.start_monitoring(interval=2)
            
            print(f"⏱️  监控运行中... ({duration}秒)")
            time.sleep(duration)
            
            print("🛑 停止监控...")
            self.gesture_detector.stop_monitoring()
            
            print("✅ 服务监控测试完成")
            return True
            
        except Exception as e:
            print(f"❌ 服务监控异常: {e}")
            return False
    
    def interactive_test(self):
        """交互式测试模式"""
        print("\n🎮 交互式测试模式")
        print("-" * 30)
        
        while True:
            print("\n📋 可用测试:")
            print("1. SSH 连接测试")
            print("2. 服务管理测试")
            print("3. Socket 连接测试")
            print("4. 手势接收测试")
            print("5. 增强版检测器测试")
            print("6. 服务监控测试")
            print("7. 完整自动测试")
            print("8. 退出")
            
            choice = input("\n请选择测试项 (1-8): ").strip()
            
            if choice == "1":
                self.test_ssh_connection()
            elif choice == "2":
                self.test_service_management()
            elif choice == "3":
                self.test_socket_connection()
            elif choice == "4":
                timeout = input("手势接收超时时间(秒) [10]: ").strip()
                timeout = int(timeout) if timeout.isdigit() else 10
                self.test_gesture_receiving(timeout)
            elif choice == "5":
                self.test_enhanced_detector()
            elif choice == "6":
                duration = input("监控时长(秒) [10]: ").strip()
                duration = int(duration) if duration.isdigit() else 10
                self.test_service_monitoring(duration)
            elif choice == "7":
                self.run_full_test()
            elif choice == "8":
                break
            else:
                print("❌ 无效选择")
    
    def run_full_test(self):
        """运行完整自动测试"""
        print("\n🎯 运行完整自动测试")
        print("=" * 60)
        
        results = []
        
        # 1. SSH 连接测试
        results.append(("SSH连接", self.test_ssh_connection()))
        
        # 2. 服务管理测试
        if results[-1][1]:  # 如果 SSH 连接成功
            results.append(("服务管理", self.test_service_management()))
            
            # 3. Socket 连接测试
            if results[-1][1]:  # 如果服务启动成功
                time.sleep(3)  # 等待服务完全启动
                results.append(("Socket连接", self.test_socket_connection()))
                
                # 4. 手势接收测试
                if results[-1][1]:  # 如果 Socket 连接成功
                    results.append(("手势接收", self.test_gesture_receiving(5)))
        
        # 5. 增强版检测器测试（独立测试）
        # results.append(("增强版检测器", self.test_enhanced_detector()))
        
        # 6. 服务监控测试
        if self.gesture_detector:
            results.append(("服务监控", self.test_service_monitoring(5)))
        
        # 显示测试结果
        print("\n📊 测试结果汇总")
        print("=" * 60)
        passed = 0
        for test_name, result in results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name:<12} {status}")
            if result:
                passed += 1
        
        print("-" * 60)
        print(f"总体结果: {passed}/{len(results)} 测试通过")
        
        if passed == len(results):
            print("🎉 所有测试通过! 手势检测模块工作正常")
        else:
            print("⚠️  部分测试失败，请检查配置和连接")
    
    def cleanup(self):
        """清理资源"""
        print("\n🧹 清理资源...")
        
        try:
            if self.enhanced_detector:
                self.enhanced_detector.stop_monitoring()
            
            if self.gesture_detector:
                self.gesture_detector.stop_monitoring()
                self.gesture_detector.disconnect()
            
            if self.socket_client:
                self.socket_client.disconnect()
            
            print("✅ 资源清理完成")
        except Exception as e:
            print(f"⚠️  清理异常: {e}")

def main():
    """主函数"""
    tester = GestureDetectionTester()
    
    try:
        # 检查启动参数
        if len(sys.argv) > 1:
            if sys.argv[1] == "--auto":
                tester.run_full_test()
            elif sys.argv[1] == "--help":
                print("使用方法:")
                print("  python test_gesture_detection.py           # 交互式模式")
                print("  python test_gesture_detection.py --auto    # 自动测试模式")
                print("  python test_gesture_detection.py --help    # 显示帮助")
                return
        else:
            tester.interactive_test()
            
    except KeyboardInterrupt:
        print("\n🛑 用户中断测试")
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
    finally:
        tester.cleanup()
        print("👋 测试程序结束")

if __name__ == "__main__":
    main()