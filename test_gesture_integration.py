#!/usr/bin/env python3
"""
手势识别集成测试工具

测试WebSocket接口中手势识别功能的完整集成
"""

import asyncio
import json
import time
from typing import Dict, Any

async def run_integration_test():
    """运行完整的集成测试"""
    print("🧪 手势识别集成测试")
    print("=" * 50)
    
    # 测试1: WebSocket参数测试
    print("1️⃣  启动WebSocket参数测试...")
    try:
        from test_websocket_gesture_params import WebSocketGestureParamsTest
        
        tester = WebSocketGestureParamsTest()
        await tester.connect_and_test(duration=10)  # 测试10秒
        tester.generate_test_report()
        
        # 检查测试结果
        if tester.test_results.get('gesture_recognition_test'):
            print("✅ WebSocket手势识别参数测试通过")
        else:
            print("❌ WebSocket手势识别参数测试失败")
            
    except Exception as e:
        print(f"❌ WebSocket参数测试错误: {e}")
    
    print("\n" + "=" * 50)
    
    # 测试2: 模拟手势数据测试
    print("2️⃣  模拟手势数据测试...")
    await test_simulated_gesture_data()
    
    print("\n" + "=" * 50)
    print("🎯 集成测试完成")

async def test_simulated_gesture_data():
    """测试模拟手势数据"""
    try:
        # 导入WebSocket接口
        import sys
        import os
        sys.path.append('/Users/m3airmima0000/new_dir/Mind-Daemon/src')
        
        from mind_daemon.interfaces.websocket_interface import WebSocketInterface
        
        # 创建接口实例（不启动服务器）
        interface = WebSocketInterface()
        
        # 模拟手势状态更新
        test_gestures = [
            {"name": "ThumbUp", "value": 2, "confidence": 0.85, "mode": "work_mode"},
            {"name": "Palm", "value": 5, "confidence": 0.92, "mode": "rest_mode"},
            {"name": "Mute", "value": 4, "confidence": 0.78, "mode": "silent_mode"},
        ]
        
        print("🤚 测试手势数据处理...")
        
        for i, gesture_data in enumerate(test_gestures, 1):
            print(f"\n测试手势 {i}: {gesture_data['name']}")
            
            # 模拟接收到的手势消息
            mock_message = {
                "timestamp": time.time(),
                "gestures": [{
                    "name": gesture_data["name"],
                    "value": gesture_data["value"],
                    "confidence": gesture_data["confidence"]
                }]
            }
            
            # 处理手势消息
            interface._process_gesture_message(mock_message)
            
            # 生成基础参数
            basic_params = interface.generate_basic_params()
            
            # 验证手势数据是否正确包含
            gesture_recognition = basic_params.gesture_recognition
            
            print(f"  📡 服务状态: {gesture_recognition.get('connection_status', 'N/A')}")
            print(f"  🤚 最新手势: {gesture_recognition.get('last_gesture', {}).get('name', 'N/A')}")
            print(f"  🎯 对应模式: {gesture_recognition.get('last_gesture', {}).get('mode', 'N/A')}")
            print(f"  📊 置信度: {gesture_recognition.get('last_gesture', {}).get('confidence', 0):.2f}")
            
            # 验证数据正确性
            if (gesture_recognition.get('last_gesture', {}).get('name') == gesture_data['name'] and
                gesture_recognition.get('last_gesture', {}).get('mode') == gesture_data['mode']):
                print(f"  ✅ 手势数据验证通过")
            else:
                print(f"  ❌ 手势数据验证失败")
            
            time.sleep(1)
        
        print("\n✅ 模拟手势数据测试完成")
        
    except Exception as e:
        print(f"❌ 模拟手势数据测试错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🚀 开始手势识别集成测试")
    print("💡 请确保已经启动WebSocket服务器:")
    print("   uv run python src/mind_daemon/interfaces/websocket_interface.py")
    print()
    
    # 询问是否继续
    try:
        input("按Enter继续测试，或Ctrl+C取消...")
    except KeyboardInterrupt:
        print("\n❌ 测试被用户取消")
        exit(0)
    
    asyncio.run(run_integration_test())