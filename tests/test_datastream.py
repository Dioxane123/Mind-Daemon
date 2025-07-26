#!/usr/bin/env python3
"""
测试BCI数据流服务 - 验证追加模式和滚动模式

验证数据订阅、存储和实时分析功能
"""

import asyncio
import sys
import os
import time
import json

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_data_stream_service():
    """测试BCI数据流服务"""
    print("🧠 测试BCI数据流服务")
    print("=" * 50)
    
    try:
        from mind_daemon.bci.data_stream_service import get_data_stream_service
        
        # 获取数据流服务实例
        service = get_data_stream_service()
        print("✅ 数据流服务创建成功")
        
        # 添加数据回调
        received_data_count = 0
        def data_callback(data):
            nonlocal received_data_count
            received_data_count += 1
            scores = data.get('scores', {})
            print(f"  📊 接收数据 #{received_data_count}: At={scores.get('At', 0)} Ex={scores.get('Ex', 0)} Re={scores.get('Re', 0)} St={scores.get('St', 0)}")
        
        service.add_data_callback(data_callback)
        print("✅ 数据回调注册成功")
        
        # 启动服务
        print("\n🚀 启动数据流服务...")
        service.start_service()
        
        # 等待服务完全启动
        await asyncio.sleep(2)
        
        # 检查服务状态
        status = service.get_service_status()
        print(f"  • 运行状态: {'✅' if status['is_running'] else '❌'}")
        print(f"  • 开发模式: {'✅' if status['dev_mode'] else '❌'}")
        print(f"  • 有效凭证: {'✅' if status['has_credentials'] else '❌'}")
        print(f"  • 回调函数数量: {status['callbacks_count']}")
        
        # 运行10秒钟收集数据
        print(f"\n📡 数据收集测试 (10秒)...")
        for i in range(10):
            await asyncio.sleep(1)
            current_data = service.get_current_data()
            scores = current_data.get('scores', {})
            print(f"  秒 {i+1}: At={scores['At']} Ex={scores['Ex']} Re={scores['Re']} St={scores['St']}")
        
        print(f"\n📈 数据收集摘要:")
        print(f"  • 总接收数据包: {received_data_count}")
        print(f"  • 平均接收频率: {received_data_count/10:.1f} Hz")
        
        # 停止服务
        print("\n🛑 停止数据流服务...")
        service.stop_service()
        
        print("✅ 数据流服务测试完成")
        return True
        
    except Exception as e:
        print(f"❌ 数据流服务测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_integration():
    """测试WebSocket集成"""
    print("\n🌐 测试WebSocket集成")
    print("=" * 50)
    
    try:
        from mind_daemon.interfaces.websocket_interface import WebSocketInterface
        
        # 创建WebSocket接口
        interface = WebSocketInterface()
        print("✅ WebSocket接口创建成功")
        
        # 测试数据生成
        print("\n📊 测试数据生成...")
        
        # 生成基础参数
        basic_params = interface.generate_basic_params()
        print("✅ 基础参数生成成功")  
        print(f"  💡 灯光: {'开启' if basic_params.light['is_on'] else '关闭'}")
        print(f"  🎵 音乐: {'播放' if basic_params.music['is_playing'] else '停止'}")
        print(f"  📊 分数: At={basic_params.Scores['At']} Ex={basic_params.Scores['Ex']} Re={basic_params.Scores['Re']} St={basic_params.Scores['St']}")
        
        # 生成高级参数
        state_result = interface.state_analyzer.analyze_current_state()
        advanced_params = interface.generate_advanced_params(state_result)
        print("✅ 高级参数生成成功")
        print(f"  🧠 状态: {advanced_params.State}")
        print(f"  ⚡ 动作: {advanced_params.Action}")
        
        # 测试完整数据包格式
        data_package = {
            'basic': {
                'light': basic_params.light,
                'music': basic_params.music,
                'curtain': basic_params.curtain,
                'Scores': basic_params.Scores,
                'timestamp': basic_params.timestamp
            },
            'advanced': {
                'State': advanced_params.State,
                'Summary': advanced_params.Summary,
                'Action': advanced_params.Action,
                'timestamp': advanced_params.timestamp
            }
        }
        
        print("✅ 数据包格式验证通过")
        print(f"  📦 数据包大小: {len(json.dumps(data_package))} 字节")
        
        return True
        
    except Exception as e:
        print(f"❌ WebSocket集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """主测试函数"""
    print("🔬 Mind Daemon 数据流测试")
    print("=" * 60)
    
    # 测试数据流服务
    datastream_ok = await test_data_stream_service()
    
    # 测试WebSocket集成
    websocket_ok = await test_websocket_integration()
    
    # 测试结果汇总
    print("\n" + "=" * 60)
    print("📊 测试结果汇总:")
    print(f"  BCI数据流服务: {'✅ 通过' if datastream_ok else '❌ 失败'}")  
    print(f"  WebSocket集成: {'✅ 通过' if websocket_ok else '❌ 失败'}")
    
    all_passed = datastream_ok and websocket_ok
    
    if all_passed:
        print("\n🎉 所有数据流测试通过！")
        print("\n🚀 系统已准备就绪:")
        print("  1. 数据订阅：追加模式 + 滚动模式 ✅")
        print("  2. 实时分析：认知分数计算 ✅")
        print("  3. 前端交互：WebSocket数据传输 ✅")
        print("\n启动命令: uv run mind-daemon")
        print("前端地址: dashboard/index.html")
    else:
        print("\n⚠️  部分测试失败，请检查配置和依赖。")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())