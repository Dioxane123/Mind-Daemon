#!/usr/bin/env python3
"""
冷却系统测试脚本 - 手动触发环境切换来测试30秒冷却机制

功能：
- 手动触发不同模式的环境切换
- 实时显示冷却状态
- 验证30秒冷却系统是否正常工作
- 连接WebSocket监控数据变化

使用方法：
    python test_cooldown_system.py
"""

import asyncio
import websockets
import json
import time
from datetime import datetime
from typing import Dict, Any

class CooldownTester:
    """冷却系统测试器"""
    
    def __init__(self):
        self.websocket_url = "ws://localhost:8889"
        self.environment_modes = ['work_mode', 'rest_mode', 'silent_mode']
        self.current_mode_index = 0
        
    async def connect_websocket(self):
        """连接到WebSocket服务器"""
        try:
            websocket = await websockets.connect(self.websocket_url)
            print(f"✅ 已连接到WebSocket服务器: {self.websocket_url}")
            return websocket
        except Exception as e:
            print(f"❌ 无法连接到WebSocket服务器: {e}")
            return None
    
    async def get_current_status(self, websocket) -> Dict[str, Any]:
        """获取当前环境控制状态"""
        try:
            # 等待接收一条消息
            message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(message)
            
            if 'basic' in data and 'environment_control' in data['basic']:
                return data['basic']['environment_control']
            else:
                return {}
                
        except asyncio.TimeoutError:
            print("⚠️  等待WebSocket数据超时")
            return {}
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
            return {}
    
    def display_status(self, env_control: Dict[str, Any]):
        """显示当前状态"""
        print(f"\n{'='*50}")
        print(f"⏰ 时间: {datetime.now().strftime('%H:%M:%S')}")
        
        # 冷却状态
        cooldown_status = env_control.get('cooldown_status', {})
        is_allowed = cooldown_status.get('is_switch_allowed', True)
        remaining = cooldown_status.get('remaining_seconds', 0)
        
        if is_allowed:
            print(f"🟢 冷却状态: Ready - 可以切换环境")
        else:
            print(f"🔴 冷却状态: Active - 剩余 {remaining:.1f} 秒")
        
        # 协调器状态
        is_coordinator_running = env_control.get('is_coordinator_running', False)
        print(f"🤝 协调器: {'运行中' if is_coordinator_running else '已停止'}")
        
        # 环境切换统计
        switch_status = env_control.get('environment_switch_status', {})
        total_switches = switch_status.get('total_switches', 0)
        print(f"📊 总切换次数: {total_switches}")
        
        # 最近的手势
        recent_gestures = env_control.get('recent_gestures', [])
        if recent_gestures:
            latest = recent_gestures[-1]
            print(f"🎯 最近手势: {latest.get('gesture', 'Unknown')} → {latest.get('mode', 'unknown')}")
        else:
            print(f"🎯 最近手势: 无")
    
    async def trigger_environment_switch(self):
        """触发环境切换（通过直接调用协调器API）"""
        try:
            # 导入协调器类
            from src.mind_daemon.agent.gesture_environment_coordinator import GestureEnvironmentCoordinator
            
            # 创建协调器实例
            config = {
                'gesture_host': '172.20.10.2',
                'gesture_port': 8888,
                'MUSIC_DIR': 'music',
                'WINDOW_PY_PATH': 'src/mind_daemon/peripheral/window.py'
            }
            
            coordinator = GestureEnvironmentCoordinator(config)
            
            # 选择模式
            current_mode = self.environment_modes[self.current_mode_index % len(self.environment_modes)]
            self.current_mode_index += 1
            
            print(f"\n🚀 尝试切换到模式: {current_mode}")
            
            # 手动触发环境切换
            result = coordinator.manual_environment_switch(current_mode, "manual_test")
            
            # 显示结果
            if result.get('success'):
                print(f"✅ 环境切换成功: {result.get('message', 'unknown')}")
                actions = result.get('actions_performed', [])
                if actions:
                    print(f"   执行的操作: {', '.join(actions)}")
                    
                # 如果有冷却信息
                if 'cooldown_remaining' in result:
                    print(f"   冷却开始: {result['cooldown_remaining']:.1f} 秒")
            else:
                error_msg = result.get('error', result.get('message', '未知错误'))
                print(f"❌ 环境切换失败: {error_msg}")
                
                # 如果是冷却导致的失败
                if 'cooldown' in error_msg.lower() or 'cd' in error_msg.lower():
                    cooldown_info = coordinator.get_cooldown_status()
                    remaining = cooldown_info.get('remaining_seconds', 0)
                    print(f"   冷却剩余: {remaining:.1f} 秒")
            
            return result
            
        except Exception as e:
            print(f"❌ 触发环境切换失败: {e}")
            return {'success': False, 'error': str(e)}
    
    async def run_interactive_test(self):
        """运行交互式测试"""
        print("🧪 30秒冷却系统测试器")
        print("=" * 50)
        print("这个工具将帮助你测试环境切换的30秒冷却机制")
        print("1. 连接到WebSocket监控环境状态")
        print("2. 手动触发环境切换")
        print("3. 观察冷却时间和状态变化")
        print()
        
        # 连接WebSocket
        websocket = await self.connect_websocket()
        if not websocket:
            print("❌ 无法连接WebSocket，测试终止")
            return
        
        try:
            while True:
                print(f"\n{'='*50}")
                print("📋 操作菜单:")
                print("1. 查看当前状态")
                print("2. 触发环境切换")
                print("3. 连续测试冷却系统")
                print("4. 退出")
                
                choice = input("\n请选择操作 (1-4): ").strip()
                
                if choice == '1':
                    print("\n🔍 获取当前状态...")
                    status = await self.get_current_status(websocket)
                    self.display_status(status)
                
                elif choice == '2':
                    print("\n🚀 手动触发环境切换...")
                    await self.trigger_environment_switch()
                    
                    # 等待一秒后显示状态
                    await asyncio.sleep(1)
                    status = await self.get_current_status(websocket)
                    self.display_status(status)
                
                elif choice == '3':
                    print("\n🔄 开始连续测试冷却系统...")
                    await self.continuous_cooldown_test(websocket)
                
                elif choice == '4':
                    print("\n👋 退出测试")
                    break
                
                else:
                    print("❌ 无效选择，请重试")
        
        finally:
            await websocket.close()
            print("🛑 WebSocket连接已关闭")
    
    async def continuous_cooldown_test(self, websocket):
        """连续测试冷却系统"""
        print("🔄 连续冷却测试模式 - 每10秒尝试一次环境切换")
        print("按 Ctrl+C 停止测试")
        print("-" * 50)
        
        test_count = 0
        successful_switches = 0
        blocked_by_cooldown = 0
        
        try:
            while True:
                test_count += 1
                print(f"\n🧪 测试 #{test_count} - {datetime.now().strftime('%H:%M:%S')}")
                
                # 获取当前状态
                status = await self.get_current_status(websocket)
                cooldown_status = status.get('cooldown_status', {})
                is_allowed = cooldown_status.get('is_switch_allowed', True)
                remaining = cooldown_status.get('remaining_seconds', 0)
                
                if is_allowed:
                    print("✅ 冷却就绪，尝试环境切换...")
                    result = await self.trigger_environment_switch()
                    
                    if result.get('success'):
                        successful_switches += 1
                        print(f"🎉 成功！总成功次数: {successful_switches}")
                    else:
                        print(f"❌ 切换失败: {result.get('error', 'unknown')}")
                else:
                    blocked_by_cooldown += 1
                    print(f"🚫 被冷却阻止，剩余: {remaining:.1f}秒 (总阻止次数: {blocked_by_cooldown})")
                
                # 显示统计
                print(f"📊 统计: 测试{test_count}次, 成功{successful_switches}次, 冷却阻止{blocked_by_cooldown}次")
                
                # 等待10秒
                print("⏳ 等待10秒...")
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print(f"\n🛑 用户中断测试")
            print(f"📈 最终统计:")
            print(f"   总测试次数: {test_count}")
            print(f"   成功切换次数: {successful_switches}")
            print(f"   冷却阻止次数: {blocked_by_cooldown}")
            if test_count > 0:
                success_rate = (successful_switches / test_count) * 100
                print(f"   成功率: {success_rate:.1f}%")

async def main():
    """主函数"""
    tester = CooldownTester()
    await tester.run_interactive_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 程序被用户中断")
    except Exception as e:
        print(f"❌ 程序运行出错: {e}")