#!/usr/bin/env python3
"""
测试Agent模块的LLM调用功能

这个测试脚本验证agent模块中各个组件的LLM集成功能
"""

import sys
import os
import logging
from pathlib import Path
import json
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 添加项目路径到Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from src.mind_daemon.agent.minimax_agent import MiniMaxAgent
from src.mind_daemon.agent.environment_agent import EnvironmentAgent
from src.mind_daemon.agent.control_center import MindDaemonSystem
from src.mind_daemon.analyzers.state_analyzer import StateAnalysisResult, MentalState


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_minimax_agent_llm():
    """测试MiniMaxAgent的LLM调用功能"""
    logger.info("=== 测试 MiniMaxAgent LLM 功能 ===")
    
    try:
        # 创建MiniMaxAgent实例
        agent = MiniMaxAgent()
        
        # 测试1: 基础LLM API调用
        logger.info("测试1: 基础LLM API调用")
        test_prompt = "根据以下用户状态提供建议：用户感到压力很大，注意力不集中。请简洁回复。"
        response = agent.call_minimax_api(test_prompt)
        logger.info(f"LLM响应: {response}")
        
        # 测试2: 生成行为策略
        logger.info("测试2: 生成行为策略")
        mock_state_result = StateAnalysisResult(
            state=MentalState.STRESSED,
            confidence=0.8,
            details="用户表现出高压力状态，心率增加，注意力分散",
            metrics={
                'stress_level': 0.8,
                'attention_score': 0.3,
                'relaxation_index': 0.2,
                'fatigue_indicator': 0.6
            }
        )
        
        strategy = agent.generate_action_strategy(mock_state_result)
        logger.info(f"生成的策略: {strategy}")
        
        # 测试3: 运行完整的自主决策循环
        logger.info("测试3: 自主决策循环")
        try:
            summary = agent.run_autonomous_cycle()
            logger.info(f"决策循环摘要: {json.dumps(summary, indent=2, ensure_ascii=False)}")
        except Exception as e:
            logger.warning(f"决策循环测试失败: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"MiniMaxAgent LLM测试失败: {e}")
        return False

def test_environment_agent_llm():
    """测试EnvironmentAgent的LLM决策功能"""
    logger.info("=== 测试 EnvironmentAgent LLM 功能 ===")
    
    try:
        # 创建EnvironmentAgent实例
        agent = EnvironmentAgent()
        
        # 测试环境控制决策
        test_cases = [
            ("STRESSED", 0.8, {"stress": 0.8, "attention": 0.3}),
            ("FOCUSED", 0.9, {"attention": 0.9, "engagement": 0.8}),
            ("FATIGUED", 0.7, {"fatigue_index": 2.5, "attention": 0.2})
        ]
        
        for state, confidence, metrics in test_cases:
            logger.info(f"测试状态: {state}")
            
            # 调用分析和控制方法
            result = agent.analyze_and_control(state, confidence, metrics)
            
            if 'error' not in result:
                logger.info(f"LLM决策结果:")
                decisions = result.get('decisions', {})
                for device, action in decisions.items():
                    logger.info(f"  {device}: {action}")
                
                actions = result.get('actions_performed', [])
                if actions:
                    logger.info(f"执行的动作:")
                    for action in actions:
                        logger.info(f"  • {action}")
            else:
                logger.error(f"环境控制失败: {result['error']}")
        
        # 清理资源
        agent.cleanup()
        return True
        
    except Exception as e:
        logger.error(f"EnvironmentAgent LLM测试失败: {e}")
        return False

def test_control_center_integration():
    """测试ControlCenter的集成LLM功能"""
    logger.info("=== 测试 ControlCenter 集成功能 ===")
    
    try:
        # 创建MindDaemonSystem实例
        system = MindDaemonSystem()
        
        # 运行单次分析（包含LLM）
        logger.info("运行单次完整分析...")
        result = system.run_single_analysis(include_llm=True, include_agent=True)
        
        if result.get('success'):
            logger.info("单次分析成功完成:")
            
            # 显示状态分析结果
            state_analysis = result.get('state_analysis', {})
            logger.info(f"状态分析: {state_analysis.get('state')} (置信度: {state_analysis.get('confidence')})")
            
            # 显示LLM分析结果
            llm_analysis = result.get('llm_analysis')
            if llm_analysis:
                logger.info(f"LLM分析: {llm_analysis.get('assessment')}")
                logger.info(f"关键洞察: {llm_analysis.get('key_insights', [])[:2]}")
            else:
                logger.warning("LLM分析未执行或失败")
            
            # 显示智能体摘要
            agent_summary = result.get('agent_summary')
            if agent_summary:
                logger.info(f"智能体行为: 触发{agent_summary.get('triggered_actions_count', 0)}个，执行{agent_summary.get('executed_actions_count', 0)}个")
            else:
                logger.warning("智能体决策未执行或失败")
            
            return True
        else:
            logger.error(f"单次分析失败: {result.get('error')}")
            return False
        
    except Exception as e:
        logger.error(f"ControlCenter集成测试失败: {e}")
        return False

def main():
    """主测试函数"""
    logger.info("开始Agent模块LLM功能测试")
    
    # 检查API配置
    api_key = os.getenv('MINIMAX_API_KEY')
    if not api_key:
        logger.warning("Minimax API Key未配置，将使用模拟响应进行测试")
    else:
        logger.info("Minimax API已配置")
    
    # 运行测试
    test_results = []
    
    # 测试1: MiniMaxAgent
    result1 = test_minimax_agent_llm()
    test_results.append(("MiniMaxAgent LLM", result1))
    
    # 测试2: EnvironmentAgent
    result2 = test_environment_agent_llm()
    test_results.append(("EnvironmentAgent LLM", result2))
    
    # 测试3: ControlCenter集成
    result3 = test_control_center_integration()
    test_results.append(("ControlCenter 集成", result3))
    
    # 总结测试结果
    logger.info("\n=== Agent模块LLM功能测试总结 ===")
    success_count = 0
    for test_name, success in test_results:
        status = "✅ 通过" if success else "❌ 失败"
        logger.info(f"{test_name}: {status}")
        if success:
            success_count += 1
    
    logger.info(f"总体结果: {success_count}/{len(test_results)} 项测试通过")
    
    if success_count == len(test_results):
        logger.info("🎉 所有Agent模块LLM功能测试通过！")
        return True
    else:
        logger.warning("⚠️ 部分测试失败，请检查日志")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)