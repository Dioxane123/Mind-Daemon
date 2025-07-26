#!/usr/bin/env python3
"""
手势识别Agent集成测试工具

测试手势识别与环境控制智能体的完整集成功能
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
from typing import Dict, Any

class GestureAgentIntegrationTest:
    """手势识别与Agent集成测试器"""
    
    def __init__(self, host: str = "localhost", port: int = 8889):
        self.host = host
        self.port = port
        self.uri = f"ws://{host}:{port}"
        self.test_results = {
            "websocket_connection": False,
            "gesture_data_present": False,
            "environment_control_working": False,
            "execution_results_available": False,
            "mode_switching_functional": False
        }
        
    async def run_integration_test(self):
        """运行完整的集成测试"""
        print("🧪 手势识别Agent集成测试")
        print("=" * 60)
        print(f"测试目标: {self.uri}")
        print("=" * 60)
        
        try:
            async with websockets.connect(self.uri) as websocket:
                print("✅ WebSocket连接成功")
                self.test_results["websocket_connection"] = True
                
                # 接收和分析数据
                await self._analyze_websocket_data(websocket)
                
        except ConnectionRefusedError:
            print("❌ 无法连接到WebSocket服务器")
            print("💡 请先启动WebSocket服务器:")
            print("   uv run python src/mind_daemon/interfaces/websocket_interface.py")
        except Exception as e:
            print(f"❌ 连接错误: {e}")
        
        self._generate_test_report()
    
    async def _analyze_websocket_data(self, websocket):
        """分析WebSocket数据"""
        print("📊 开始数据分析 (测试30秒)...")
        
        start_time = time.time()
        message_count = 0
        gesture_data_samples = []
        execution_results = []
        
        while time.time() - start_time < 30:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                data = json.loads(message)
                message_count += 1
                
                # 分析基础数据中的手势识别信息
                if 'basic' in data and 'gesture_recognition' in data['basic']:
                    gesture_data = data['basic']['gesture_recognition']
                    self.test_results["gesture_data_present"] = True
                    
                    # 记录手势数据样本
                    if gesture_data.get('last_gesture', {}).get('name'):
                        gesture_data_samples.append({
                            'timestamp': datetime.now().isoformat(),
                            'gesture': gesture_data['last_gesture'],
                            'service_status': gesture_data.get('service_running', False)
                        })
                    
                    # 检查执行结果
                    if gesture_data.get('last_execution', {}).get('result'):
                        execution_result = gesture_data['last_execution']
                        execution_results.append(execution_result)
                        self.test_results["execution_results_available"] = True
                        
                        # 检查环境控制是否工作
                        result = execution_result.get('result', {})
                        if result.get('actions_performed'):
                            self.test_results["environment_control_working"] = True
                        
                        print(f"🤚 [{datetime.now().strftime('%H:%M:%S')}] 手势执行结果:")
                        print(f"   手势: {result.get('gesture_name', 'N/A')}")
                        print(f"   模式: {result.get('gesture_mode', 'N/A')}")
                        print(f"   成功: {result.get('success', False)}")
                        print(f"   操作: {', '.join(result.get('actions_performed', []))}")
                
                # 显示实时状态
                if message_count % 5 == 0:
                    print(f"📈 接收到 {message_count} 条消息...")
                
            except asyncio.TimeoutError:
                continue
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"❌ 数据处理错误: {e}")
        
        # 分析收集的数据
        self._analyze_collected_data(gesture_data_samples, execution_results)
    
    def _analyze_collected_data(self, gesture_samples, execution_results):
        """分析收集的数据"""
        print(f"\n📊 数据分析结果:")
        print(f"   手势数据样本: {len(gesture_samples)} 个")
        print(f"   执行结果: {len(execution_results)} 个")
        
        # 分析手势模式切换功能
        if gesture_samples:
            unique_modes = set()
            for sample in gesture_samples:
                mode = sample['gesture'].get('mode')
                if mode and mode != 'unknown_mode':
                    unique_modes.add(mode)
            
            if len(unique_modes) >= 2:
                self.test_results["mode_switching_functional"] = True
                print(f"   检测到的模式: {', '.join(unique_modes)}")
            else:
                print(f"   模式切换测试: 需要更多手势输入来验证")
        
        # 显示最近的执行结果
        if execution_results:
            print(f"\n🔍 最近的执行结果:")
            for i, exec_result in enumerate(execution_results[-3:], 1):
                result = exec_result.get('result', {})
                timestamp = exec_result.get('timestamp', 'N/A')
                print(f"   {i}. [{timestamp[-8:]}] {result.get('gesture_name', 'N/A')} → "
                      f"{result.get('gesture_mode', 'N/A')} "
                      f"({'成功' if result.get('success') else '失败'})")
    
    def _generate_test_report(self):
        """生成测试报告"""
        print("\n" + "=" * 60)
        print("📋 手势识别Agent集成测试报告")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result)
        
        print(f"📊 测试摘要: {passed_tests}/{total_tests} 项测试通过")
        
        # 详细测试结果
        test_descriptions = {
            "websocket_connection": "WebSocket连接测试",
            "gesture_data_present": "手势数据存在性测试",
            "environment_control_working": "环境控制功能测试",
            "execution_results_available": "执行结果可用性测试",
            "mode_switching_functional": "模式切换功能测试"
        }
        
        print("\n📋 详细测试结果:")
        for test_name, passed in self.test_results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            description = test_descriptions.get(test_name, test_name)
            print(f"  {status} {description}")
        
        # 系统状态评估
        print(f"\n🎯 系统状态评估:")
        if passed_tests == total_tests:
            print("🟢 优秀 - 手势识别与环境控制系统完全正常")
        elif passed_tests >= total_tests * 0.8:
            print("🟡 良好 - 系统基本正常，部分功能需要验证")
        elif passed_tests >= total_tests * 0.6:
            print("🟠 一般 - 系统部分功能正常，需要检查配置")
        else:
            print("🔴 异常 - 系统存在重大问题，需要全面检查")
        
        # 功能建议
        print(f"\n💡 使用建议:")
        if not self.test_results["gesture_data_present"]:
            print("   - 检查RDK X5开发板连接和手势识别服务")
        if not self.test_results["environment_control_working"]:
            print("   - 验证环境控制设备(音乐、灯光、光晕)配置")
        if not self.test_results["mode_switching_functional"]:
            print("   - 尝试做不同的手势来测试模式切换功能")
        if self.test_results["websocket_connection"] and self.test_results["gesture_data_present"]:
            print("   - 系统连接正常，可以开始使用手势控制功能")

async def main():
    """主测试函数"""
    print("🚀 启动手势识别Agent集成测试")
    print("💡 测试将验证以下功能:")
    print("   1. WebSocket数据传输")
    print("   2. 手势识别数据获取")
    print("   3. 环境控制执行")
    print("   4. 执行结果反馈")
    print("   5. 模式切换功能")
    print()
    
    # 询问是否继续
    try:
        input("按Enter开始测试，或Ctrl+C取消...")
    except KeyboardInterrupt:
        print("\n❌ 测试被用户取消")
        return
    
    tester = GestureAgentIntegrationTest()
    await tester.run_integration_test()

if __name__ == "__main__":
    asyncio.run(main())