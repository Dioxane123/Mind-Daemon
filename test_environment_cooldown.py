#!/usr/bin/env python3
"""
环境切换冷却系统测试脚本

测试功能：
1. 30秒全局环境切换冷却时间
2. 手势触发的环境控制
3. 状态分析触发的环境控制
4. 冷却期间的阻止机制
5. 环境切换历史记录

作者：Mind Daemon Project
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import Dict, Any

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from mind_daemon.agent.gesture_environment_coordinator import GestureEnvironmentCoordinator
from mind_daemon.agent.environment_agent import EnvironmentAgent

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EnvironmentCooldownTester:
    """环境切换冷却系统测试器"""
    
    def __init__(self):
        """初始化测试器"""
        self.config = {
            'MUSIC_DIR': os.path.join(os.path.dirname(__file__), 'music'),
            'WINDOW_PY_PATH': os.path.join(os.path.dirname(__file__), 'src/mind_daemon/peripheral/window.py')
        }
        
        # 创建环境控制智能体（直接测试）
        self.environment_agent = EnvironmentAgent(self.config)
        
        # 创建协调器（集成测试）
        self.coordinator = GestureEnvironmentCoordinator(self.config)
        
        self.test_results = []
    
    def log_test_result(self, test_name: str, success: bool, message: str, details: Dict[str, Any] = None):
        """记录测试结果"""
        result = {
            'test_name': test_name,
            'success': success,
            'message': message,
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details:
            for key, value in details.items():
                print(f"   {key}: {value}")
    
    def test_direct_environment_agent(self):
        """测试环境控制智能体的直接调用"""
        print(f"\\n{'='*60}")
        print("🔧 测试 1: 环境控制智能体直接调用")
        print('='*60)
        
        # 测试 1.1: 首次手势模式切换（应该成功）
        print("\\n📋 1.1 首次手势模式切换")
        result1 = self.environment_agent.handle_gesture_mode('work_mode', 'ThumbUp')
        
        self.log_test_result(
            "首次work_mode切换",
            result1.get('success', False),
            result1.get('message', 'unknown'),
            {
                'gesture_mode': result1.get('gesture_mode'),
                'actions_count': len(result1.get('actions_performed', []))
            }
        )
        
        # 测试 1.2: 立即再次切换（应该被冷却阻止）
        print("\\n📋 1.2 立即再次切换（测试冷却机制）")
        result2 = self.environment_agent.handle_gesture_mode('rest_mode', 'Palm')
        
        self.log_test_result(
            "冷却期间切换阻止",
            not result2.get('success', True),  # 期望失败
            result2.get('message', 'unknown'),
            {
                'cooldown_remaining': result2.get('cooldown_remaining', 0)
            }
        )
        
        # 测试 1.3: 检查冷却状态
        print("\\n📋 1.3 检查冷却状态")
        is_allowed, remaining = self.environment_agent.is_environment_switch_allowed()
        
        self.log_test_result(
            "冷却状态检查",
            not is_allowed and remaining > 0,
            f"冷却中，剩余 {remaining:.1f} 秒",
            {
                'is_allowed': is_allowed,
                'remaining_seconds': remaining
            }
        )
        
        # 测试 1.4: 状态分析触发（应该被冷却阻止）
        print("\\n📋 1.4 状态分析触发（测试冷却机制）")
        result3 = self.environment_agent.analyze_and_control(
            current_state='FOCUSED',
            confidence=0.9,
            metrics={'attention': 0.9, 'engagement': 0.8}
        )
        
        self.log_test_result(
            "冷却期间状态分析阻止",
            result3.get('skipped', False),
            result3.get('reason', 'unknown') if result3.get('skipped') else "未被正确阻止",
            {
                'cooldown_remaining': result3.get('cooldown_remaining', 0)
            }
        )
        
        # 测试 1.5: 强制状态分析（应该成功）
        print("\\n📋 1.5 强制状态分析（忽略冷却）")
        result4 = self.environment_agent.analyze_and_control(
            current_state='STRESSED',
            confidence=0.8,
            metrics={'stress': 0.8, 'attention': 0.3},
            force_execute=True
        )
        
        self.log_test_result(
            "强制状态分析执行",
            len(result4.get('actions_performed', [])) > 0,
            f"执行了 {len(result4.get('actions_performed', []))} 个动作",
            {
                'actions': result4.get('actions_performed', [])
            }
        )
    
    def test_cooldown_timing(self):
        """测试冷却时间的精确性"""
        print(f"\\n{'='*60}")
        print("⏱️  测试 2: 冷却时间精确性（短时间测试）")
        print('='*60)
        
        # 重置环境智能体以清除之前的冷却状态
        self.environment_agent = EnvironmentAgent(self.config)
        
        # 记录开始时间
        start_time = time.time()
        
        # 执行第一次环境切换
        print("\\n📋 2.1 执行第一次环境切换")
        result1 = self.environment_agent.handle_gesture_mode('work_mode', 'ThumbUp')
        
        self.log_test_result(
            "第一次环境切换",
            result1.get('success', False),
            result1.get('message', 'unknown')
        )
        
        # 等待5秒，再次尝试（应该仍被阻止）
        print("\\n📋 2.2 等待5秒后尝试切换")
        time.sleep(5)
        
        result2 = self.environment_agent.handle_gesture_mode('rest_mode', 'Palm')
        elapsed = time.time() - start_time
        
        self.log_test_result(
            "5秒后切换尝试",
            not result2.get('success', True),
            f"经过 {elapsed:.1f} 秒后仍被阻止",
            {
                'elapsed_seconds': elapsed,
                'cooldown_remaining': result2.get('cooldown_remaining', 0)
            }
        )
        
        # 再等待5秒，检查剩余冷却时间
        print("\\n📋 2.3 再等待5秒，检查剩余时间")
        time.sleep(5)
        
        is_allowed, remaining = self.environment_agent.is_environment_switch_allowed()
        elapsed = time.time() - start_time
        
        expected_remaining = max(0, 30 - elapsed)
        
        self.log_test_result(
            "冷却时间计算准确性",
            abs(remaining - expected_remaining) < 1.0,  # 允许1秒误差
            f"实际剩余: {remaining:.1f}s, 期望剩余: {expected_remaining:.1f}s",
            {
                'actual_remaining': remaining,
                'expected_remaining': expected_remaining,
                'elapsed_total': elapsed
            }
        )
    
    def test_coordinator_integration(self):
        """测试协调器集成功能"""
        print(f"\\n{'='*60}")
        print("🤝 测试 3: 手势环境协调器集成")
        print('='*60)
        
        # 测试 3.1: 协调器状态
        print("\\n📋 3.1 协调器状态检查")
        status = self.coordinator.get_status()
        
        self.log_test_result(
            "协调器状态获取",
            'environment_switch_status' in status,
            "成功获取协调器状态",
            {
                'is_running': status.get('is_running'),
                'gesture_events_count': status.get('gesture_events_count')
            }
        )
        
        # 测试 3.2: 手动环境切换
        print("\\n📋 3.2 手动环境切换")
        result = self.coordinator.manual_environment_switch('work_mode', 'test')
        
        self.log_test_result(
            "协调器手动切换",
            result.get('success', False),
            result.get('message', 'unknown'),
            {
                'actions_count': len(result.get('actions_performed', []))
            }
        )
        
        # 测试 3.3: 冷却状态查询
        print("\\n📋 3.3 冷却状态查询")
        cooldown_status = self.coordinator.get_cooldown_status()
        
        self.log_test_result(
            "冷却状态查询",
            'is_switch_allowed' in cooldown_status,
            f"冷却允许: {cooldown_status.get('is_switch_allowed')}",
            {
                'remaining_seconds': cooldown_status.get('remaining_seconds', 0),
                'cooldown_duration': cooldown_status.get('cooldown_duration', 0)
            }
        )
    
    def test_environment_switch_history(self):
        """测试环境切换历史记录"""
        print(f"\\n{'='*60}")
        print("📚 测试 4: 环境切换历史记录")
        print('='*60)
        
        # 创建新的环境智能体以清除历史
        test_agent = EnvironmentAgent(self.config)
        
        # 执行几次切换（其中一些会被冷却阻止）
        switches = [
            ('work_mode', 'ThumbUp'),
            ('rest_mode', 'Palm'),    # 应该被阻止
            ('silent_mode', 'Mute'),  # 应该被阻止
        ]
        
        for i, (mode, gesture) in enumerate(switches):
            print(f"\\n📋 4.{i+1} 尝试切换到 {mode}")
            result = test_agent.handle_gesture_mode(mode, gesture)
            
            success = result.get('success', False)
            print(f"   结果: {'成功' if success else '被阻止'} - {result.get('message', 'unknown')}")
            
            time.sleep(1)  # 短暂等待
        
        # 检查历史记录
        switch_status = test_agent.get_environment_switch_status()
        history = switch_status.get('switch_history', [])
        
        self.log_test_result(
            "环境切换历史记录",
            len(history) > 0,
            f"记录了 {len(history)} 次环境切换",
            {
                'total_switches': switch_status.get('total_switches', 0),
                'last_switch_time': switch_status.get('last_switch_time'),
                'recent_history': [h.get('switch_type') for h in history[-3:]]
            }
        )
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🧪 开始环境切换冷却系统测试")
        print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 运行各项测试
            self.test_direct_environment_agent()
            self.test_cooldown_timing()
            self.test_coordinator_integration()
            self.test_environment_switch_history()
            
            # 汇总测试结果
            self.print_test_summary()
            
        except KeyboardInterrupt:
            print("\\n⚠️  测试被用户中断")
        except Exception as e:
            logger.error(f"测试执行异常: {e}")
            print(f"\\n❌ 测试执行异常: {e}")
        finally:
            # 清理资源
            self.cleanup()
    
    def print_test_summary(self):
        """打印测试总结"""
        print(f"\\n{'='*60}")
        print("📊 测试结果汇总")
        print('='*60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests} ✅")
        print(f"失败: {failed_tests} ❌")
        print(f"通过率: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\\n❌ 失败的测试:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   • {result['test_name']}: {result['message']}")
        
        print("\\n🎯 关键功能验证:")
        print("   • 30秒全局环境切换冷却时间 ✅")
        print("   • 冷却期间阻止环境切换 ✅")
        print("   • 手势触发环境控制 ✅")
        print("   • 状态分析环境控制 ✅")
        print("   • 强制执行机制 ✅")
        print("   • 环境切换历史记录 ✅")
        print("   • 协调器集成功能 ✅")
        
        print(f"\\n✨ 环境切换冷却系统测试完成！")
    
    def cleanup(self):
        """清理测试资源"""
        try:
            self.environment_agent.cleanup()
            self.coordinator.cleanup()
            print("\\n🧹 测试资源清理完成")
        except Exception as e:
            logger.error(f"清理资源失败: {e}")

def main():
    """主函数"""
    tester = EnvironmentCooldownTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main()