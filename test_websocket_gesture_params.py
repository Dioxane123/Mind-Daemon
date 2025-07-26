#!/usr/bin/env python3
"""
WebSocket手势识别参数测试工具

测试WebSocket接口是否能正确生成和发送包含手势识别数据的参数
"""

import asyncio
import websockets
import json
import time
from datetime import datetime
from typing import Dict, Any

class WebSocketGestureParamsTest:
    """WebSocket手势识别参数测试器"""
    
    def __init__(self, host: str = "localhost", port: int = 8889):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.received_data = []
        self.test_results = {
            "connection_test": False,
            "basic_params_test": False,
            "gesture_recognition_test": False,
            "data_structure_test": False,
            "continuous_updates_test": False
        }
    
    async def connect_and_test(self, duration: int = 30):
        """连接WebSocket并测试指定时间"""
        print(f"🔌 连接到WebSocket服务器: {self.uri}")
        
        try:
            async with websockets.connect(self.uri) as websocket:
                print("✅ WebSocket连接成功")
                self.test_results["connection_test"] = True
                
                print(f"📊 开始接收数据测试 (持续 {duration} 秒)...")
                start_time = time.time()
                
                while time.time() - start_time < duration:
                    try:
                        # 设置接收超时
                        message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        data = json.loads(message)
                        
                        # 记录接收时间
                        data['_received_at'] = datetime.now().isoformat()
                        self.received_data.append(data)
                        
                        # 实时显示数据
                        self._display_realtime_data(data)
                        
                        # 验证数据结构
                        self._validate_data_structure(data)
                        
                    except asyncio.TimeoutError:
                        print("⏰ 5秒内未收到数据，继续等待...")
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析错误: {e}")
                    except Exception as e:
                        print(f"❌ 接收数据错误: {e}")
                
                print(f"\n📈 测试完成，共接收到 {len(self.received_data)} 条数据")
                
        except ConnectionRefusedError:
            print("❌ 无法连接到WebSocket服务器")
            print("💡 请确保WebSocket服务器正在运行:")
            print("   uv run python src/mind_daemon/interfaces/websocket_interface.py")
        except Exception as e:
            print(f"❌ 连接错误: {e}")
    
    def _display_realtime_data(self, data: Dict[str, Any]):
        """实时显示接收到的数据"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # 基础数据
        if 'basic' in data:
            basic = data['basic']
            print(f"\n[{timestamp}] 📦 基础数据:")
            
            # BCI分数
            if 'Scores' in basic:
                scores = basic['Scores']
                print(f"  🧠 BCI分数: At={scores.get('At', 'N/A')} Ex={scores.get('Ex', 'N/A')} Re={scores.get('Re', 'N/A')} St={scores.get('St', 'N/A')}")
            
            # 手势识别数据
            if 'gesture_recognition' in basic:
                gesture = basic['gesture_recognition']
                print(f"  🤚 手势识别状态:")
                print(f"     连接状态: {gesture.get('connection_status', 'N/A')}")
                print(f"     服务运行: {gesture.get('service_running', False)}")
                
                if gesture.get('last_gesture'):
                    last_gesture = gesture['last_gesture']
                    print(f"     最新手势: {last_gesture.get('name', 'N/A')} (置信度: {last_gesture.get('confidence', 0):.2f})")
                    print(f"     对应模式: {last_gesture.get('mode', 'N/A')}")
            
            # 环境控制
            if 'light' in basic and 'music' in basic:
                light = basic['light']
                music = basic['music']
                print(f"  💡 灯光: {'开启' if light.get('is_on') else '关闭'} ({light.get('color_hex', 'N/A')})")
                print(f"  🎵 音乐: {'播放中' if music.get('is_playing') else '停止'} ({music.get('name', 'N/A')})")
        
        # 高级数据
        if 'advanced' in data:
            advanced = data['advanced']
            print(f"  🎯 当前状态: {advanced.get('State', 'N/A')}")
            print(f"  🎬 系统动作: {advanced.get('Action', 'N/A')}")
    
    def _validate_data_structure(self, data: Dict[str, Any]):
        """验证数据结构"""
        # 检查基础参数结构
        if 'basic' in data:
            basic = data['basic']
            required_basic_fields = ['light', 'music', 'curtain', 'Scores', 'timestamp']
            
            has_all_basic = all(field in basic for field in required_basic_fields)
            if has_all_basic:
                self.test_results["basic_params_test"] = True
            
            # 检查手势识别字段
            if 'gesture_recognition' in basic:
                gesture = basic['gesture_recognition']
                required_gesture_fields = [
                    'service_connected', 'service_running', 'connection_status', 
                    'last_gesture', 'supported_gestures'
                ]
                
                has_all_gesture = all(field in gesture for field in required_gesture_fields)
                if has_all_gesture:
                    self.test_results["gesture_recognition_test"] = True
                    
                    # 检查last_gesture结构
                    if gesture.get('last_gesture'):
                        last_gesture = gesture['last_gesture']
                        gesture_fields = ['name', 'value', 'confidence', 'mode', 'timestamp']
                        has_gesture_structure = all(field in last_gesture for field in gesture_fields)
                        if has_gesture_structure:
                            self.test_results["data_structure_test"] = True
        
        # 检查高级参数结构
        if 'advanced' in data:
            advanced = data['advanced']
            required_advanced_fields = ['State', 'Summary', 'Action', 'timestamp']
            has_all_advanced = all(field in advanced for field in required_advanced_fields)
            
            if has_all_advanced and len(self.received_data) >= 3:
                self.test_results["continuous_updates_test"] = True
    
    def generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📋 WebSocket手势识别参数测试报告")
        print("=" * 60)
        
        # 测试结果摘要
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 测试摘要: {passed_tests}/{total_tests} 项测试通过")
        
        # 详细测试结果
        test_descriptions = {
            "connection_test": "WebSocket连接测试",
            "basic_params_test": "基础参数结构测试",
            "gesture_recognition_test": "手势识别字段测试",
            "data_structure_test": "数据结构完整性测试",
            "continuous_updates_test": "连续数据更新测试"
        }
        
        print("\n📋 详细测试结果:")
        for test_name, passed in self.test_results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            description = test_descriptions.get(test_name, test_name)
            print(f"  {status} {description}")
        
        # 数据统计
        if self.received_data:
            print(f"\n📈 数据统计:")
            print(f"  总接收数据: {len(self.received_data)} 条")
            
            # 统计手势识别数据
            gesture_data_count = 0
            valid_gestures = 0
            
            for data in self.received_data:
                if data.get('basic', {}).get('gesture_recognition'):
                    gesture_data_count += 1
                    gesture_rec = data['basic']['gesture_recognition']
                    if gesture_rec.get('last_gesture', {}).get('name'):
                        valid_gestures += 1
            
            print(f"  包含手势数据: {gesture_data_count} 条")
            print(f"  有效手势识别: {valid_gestures} 条")
            
            # 最后一条数据样本
            if self.received_data:
                last_data = self.received_data[-1]
                print(f"\n📄 最新数据样本:")
                print(f"  时间戳: {last_data.get('_received_at', 'N/A')}")
                
                if 'basic' in last_data and 'gesture_recognition' in last_data['basic']:
                    gesture = last_data['basic']['gesture_recognition']
                    print(f"  手势服务状态: {gesture.get('connection_status', 'N/A')}")
                    print(f"  服务运行: {gesture.get('service_running', False)}")
                    
                    if gesture.get('last_gesture', {}).get('name'):
                        last_gesture = gesture['last_gesture']
                        print(f"  最新手势: {last_gesture.get('name')} (模式: {last_gesture.get('mode')})")
        
        # 问题诊断
        print(f"\n🔍 问题诊断:")
        if not self.test_results["connection_test"]:
            print("  ❌ WebSocket服务器连接失败")
            print("     - 确保服务器正在运行")
            print("     - 检查端口8889是否被占用")
        
        if not self.test_results["gesture_recognition_test"]:
            print("  ❌ 手势识别数据缺失")
            print("     - 检查RDK X5开发板连接")
            print("     - 确认手势识别服务启动")
        
        if not self.test_results["continuous_updates_test"]:
            print("  ❌ 数据更新不连续")
            print("     - 检查数据生成循环")
            print("     - 确认BCI数据流正常")
        
        # 总体评估
        print(f"\n🎯 总体评估:", end=" ")
        if passed_tests == total_tests:
            print("🟢 所有测试通过，系统运行正常")
        elif passed_tests >= total_tests * 0.8:
            print("🟡 大部分测试通过，存在小问题")
        else:
            print("🔴 多项测试失败，需要检查系统配置")

async def main():
    """主测试函数"""
    print("🧪 WebSocket手势识别参数测试工具")
    print("=" * 50)
    
    tester = WebSocketGestureParamsTest()
    
    # 询问测试时长
    try:
        duration_input = input("请输入测试时长(秒) [30]: ").strip()
        duration = int(duration_input) if duration_input else 30
    except ValueError:
        duration = 30
    
    print(f"⏱️  测试时长: {duration} 秒")
    print("💡 测试期间请确保WebSocket服务器正在运行")
    print("💡 如果有RDK X5开发板，可以尝试做手势进行测试")
    
    # 开始测试
    await tester.connect_and_test(duration)
    
    # 生成报告
    tester.generate_test_report()

if __name__ == "__main__":
    asyncio.run(main())