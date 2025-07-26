#!/usr/bin/env python3
"""
Mind Daemon 系统测试脚本

验证所有组件是否正常工作
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_imports():
    """测试模块导入"""
    print("📦 测试模块导入...")
    
    try:
        from mind_daemon.utils.config import config
        print("  ✅ 配置系统")
        
        from mind_daemon.bci.data_stream_service import get_data_stream_service
        print("  ✅ BCI数据流服务")
        
        from mind_daemon.interfaces.websocket_interface import WebSocketInterface
        print("  ✅ WebSocket接口")
        
        from mind_daemon.agent.minimax_agent import MiniMaxAgent
        print("  ✅ MiniMax智能体")
        
        from mind_daemon.agent.environment_agent import EnvironmentAgent
        print("  ✅ 环境控制智能体")
        
        return True
    except Exception as e:
        print(f"  ❌ 导入失败: {e}")
        return False

async def test_websocket_interface():
    """测试WebSocket接口"""
    print("\n🌐 测试WebSocket接口...")
    
    try:
        from mind_daemon.interfaces.websocket_interface import WebSocketInterface
        
        interface = WebSocketInterface()
        print("  ✅ 接口创建成功")
        
        # 测试数据生成（不启动实际服务）
        try:
            basic_params = interface.generate_basic_params()
            print("  ✅ 基础参数生成")
            print(f"     分数: At={basic_params.Scores['At']} Ex={basic_params.Scores['Ex']}")
            
            state_result = interface.state_analyzer.analyze_current_state()
            advanced_params = interface.generate_advanced_params(state_result)
            print("  ✅ 高级参数生成")
            print(f"     状态: {advanced_params.State}")
            
        except Exception as e:
            print(f"  ⚠️  数据生成警告: {e}")
        
        return True
    except Exception as e:
        print(f"  ❌ WebSocket接口测试失败: {e}")
        return False

def test_configuration():
    """测试配置系统"""
    print("\n⚙️  测试配置系统...")
    
    try:
        from mind_daemon.utils.config import config
        
        print(f"  📍 项目目录: {config.get('MUSIC_DIR')}")
        print(f"  🔧 开发模式: {config.get('DEV_MODE')}")
        print(f"  🌐 WebSocket端口: {config.get('WEBSOCKET_PORT')}")
        
        return True
    except Exception as e:
        print(f"  ❌ 配置系统测试失败: {e}")
        return False

async def main():
    """主测试函数"""
    print("🧠 Mind Daemon 系统测试")
    print("=" * 50)
    
    # 测试导入
    imports_ok = test_imports()
    
    # 测试配置
    config_ok = test_configuration()
    
    # 测试WebSocket接口
    websocket_ok = await test_websocket_interface()
    
    print("\n" + "=" * 50)
    print("📊 测试结果汇总:")
    print(f"  模块导入: {'✅' if imports_ok else '❌'}")
    print(f"  配置系统: {'✅' if config_ok else '❌'}")
    print(f"  WebSocket接口: {'✅' if websocket_ok else '❌'}")
    
    all_passed = imports_ok and config_ok and websocket_ok
    
    if all_passed:
        print("\n🎉 所有测试通过！系统可以启动。")
        print("\n🚀 启动方法:")
        print("  1. 运行后端: uv run mind-daemon")
        print("  2. 打开前端: dashboard/index.html")
        print("  3. 查看实时数据更新")
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
    
    return all_passed

if __name__ == "__main__":
    asyncio.run(main())