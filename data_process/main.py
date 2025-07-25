"""
Mind Daemon - 精神状态分析与智能干预系统主程序

整合了三个核心模块：
1. Task 1: 传统方法 + BCI指标的状态分析
2. Task 2: LLM深度精神状态分析与总结
3. Task 3: MiniMax智能体的阈值行为决策

作者：Mind Daemon Project
"""

import os
import sys
import time
import signal
import argparse
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(__file__))

# 导入三个核心模块
from state_analyzer import StateAnalyzer, MentalState, StateAnalysisResult
from llm_analyzer import LLMAnalyzer, LLMAnalysisResult
from minimax_agent import MiniMaxAgent

# 配置日志系统
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('mind_daemon.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

class MindDaemonSystem:
    """Mind Daemon主系统类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化Mind Daemon系统
        
        Args:
            config: 系统配置字典
        """
        self.config = config or {}
        self.running = False
        
        # 初始化三个核心模块
        try:
            logger.info("初始化Mind Daemon系统...")
            
            self.state_analyzer = StateAnalyzer()
            self.llm_analyzer = LLMAnalyzer()
            self.minimax_agent = MiniMaxAgent()
            
            # 系统运行参数
            self.analysis_interval = self.config.get('analysis_interval', 60)  # 分析间隔（秒）
            self.llm_analysis_interval = self.config.get('llm_analysis_interval', 300)  # LLM分析间隔（秒）
            self.enable_autonomous_agent = self.config.get('enable_autonomous_agent', True)
            
            # 运行统计
            self.stats = {
                'start_time': None,
                'total_analyses': 0,
                'llm_analyses': 0,
                'agent_actions': 0,
                'last_analysis_time': None,
                'last_llm_analysis_time': None
            }
            
            logger.info("Mind Daemon系统初始化完成")
            
        except Exception as e:
            logger.error(f"系统初始化失败: {e}")
            raise

    def run_single_analysis(self, include_llm: bool = True, 
                          include_agent: bool = True) -> Dict[str, Any]:
        """
        运行单次完整分析
        
        Args:
            include_llm: 是否包含LLM分析
            include_agent: 是否包含智能体决策
            
        Returns:
            分析结果字典
        """
        try:
            logger.info("开始单次分析循环")
            analysis_start = datetime.now()
            
            # Step 1: 基础状态分析
            logger.info("Step 1: 执行基础状态分析")
            state_result = self.state_analyzer.analyze_current_state()
            
            # Step 2: LLM深度分析（可选）
            llm_result = None
            if include_llm:
                try:
                    logger.info("Step 2: 执行LLM深度分析")
                    llm_result = self.llm_analyzer.analyze_mental_state(window_minutes=30)
                    self.stats['llm_analyses'] += 1
                except Exception as e:
                    logger.warning(f"LLM分析失败: {e}")
            
            # Step 3: 智能体决策与行为执行（可选）
            agent_summary = None
            if include_agent:
                try:
                    logger.info("Step 3: 执行智能体决策")
                    agent_summary = self.minimax_agent.run_autonomous_cycle()
                    if agent_summary.get('executed_actions_count', 0) > 0:
                        self.stats['agent_actions'] += agent_summary['executed_actions_count']
                except Exception as e:
                    logger.warning(f"智能体决策失败: {e}")
            
            # 统计更新
            self.stats['total_analyses'] += 1
            self.stats['last_analysis_time'] = analysis_start.isoformat()
            if include_llm and llm_result:
                self.stats['last_llm_analysis_time'] = analysis_start.isoformat()
            
            analysis_duration = (datetime.now() - analysis_start).total_seconds()
            
            # 构建完整结果
            result = {
                'timestamp': analysis_start.isoformat(),
                'duration_seconds': round(analysis_duration, 2),
                'state_analysis': {
                    'state': state_result.state.name,
                    'state_code': state_result.state.value,
                    'confidence': state_result.confidence,
                    'details': state_result.details,
                    'metrics': state_result.metrics
                },
                'llm_analysis': None,
                'agent_summary': agent_summary,
                'success': True
            }
            
            if llm_result:
                result['llm_analysis'] = {
                    'assessment': llm_result.mental_state_assessment,
                    'summary': llm_result.summary,
                    'key_insights': llm_result.key_insights,
                    'recommendations': llm_result.recommendations,
                    'confidence_level': llm_result.confidence_level
                }
            
            logger.info(f"单次分析完成，耗时: {analysis_duration:.2f}秒")
            
            return result
            
        except Exception as e:
            logger.error(f"单次分析失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'success': False
            }

    def display_analysis_result(self, result: Dict[str, Any]):
        """显示分析结果"""
        if not result.get('success', False):
            print(f"❌ 分析失败: {result.get('error', '未知错误')}")
            return
        
        print(f"\n{'='*60}")
        print(f"🧠 Mind Daemon 分析报告")
        print(f"📅 时间: {result['timestamp']}")
        print(f"⏱️  耗时: {result['duration_seconds']}秒")
        print(f"{'='*60}")
        
        # 基础状态分析结果
        state_analysis = result['state_analysis']
        state_emoji = {
            'FOCUSED': '🎯', 'RELAXED': '😌', 'EXCITED': '⚡',
            'STRESSED': '😰', 'DISTRACTED': '🤯', 'NEUTRAL': '😐',
            'FATIGUED': '😴'
        }.get(state_analysis['state'], '❓')
        
        print(f"\n📊 基础状态分析:")
        print(f"   状态: {state_emoji} {state_analysis['state']} (代码: {state_analysis['state_code']})")
        print(f"   置信度: {state_analysis['confidence']:.2f}")
        print(f"   详情: {state_analysis['details']}")
        
        print(f"\n📈 关键指标:")
        for key, value in state_analysis['metrics'].items():
            if isinstance(value, (int, float)):
                print(f"   {key}: {value:.3f}")
        
        # LLM分析结果
        if result.get('llm_analysis'):
            llm_analysis = result['llm_analysis']
            print(f"\n🤖 LLM深度分析:")
            print(f"   评估: {llm_analysis['assessment']}")
            print(f"   置信度: {llm_analysis['confidence_level']}")
            print(f"   摘要: {llm_analysis['summary']}")
            
            if llm_analysis['key_insights']:
                print(f"   关键洞察:")
                for insight in llm_analysis['key_insights']:
                    print(f"     • {insight}")
            
            if llm_analysis['recommendations']:
                print(f"   建议:")
                for rec in llm_analysis['recommendations']:
                    print(f"     • {rec}")
        
        # 智能体执行摘要
        if result.get('agent_summary'):
            agent_summary = result['agent_summary']
            print(f"\n🎯 智能体行为:")
            print(f"   触发行为数: {agent_summary.get('triggered_actions_count', 0)}")
            print(f"   执行行为数: {agent_summary.get('executed_actions_count', 0)}")
            print(f"   成功行为数: {agent_summary.get('successful_actions', 0)}")
            if agent_summary.get('strategy_generated'):
                print(f"   ✅ 已生成智能策略建议")

    def run_continuous_monitoring(self, duration_minutes: int = 0):
        """
        运行持续监控模式
        
        Args:
            duration_minutes: 运行时长（分钟），0表示无限运行
        """
        try:
            self.running = True
            self.stats['start_time'] = datetime.now().isoformat()
            
            print(f"\n🚀 启动Mind Daemon持续监控模式")
            print(f"⚙️  分析间隔: {self.analysis_interval}秒")
            print(f"⚙️  LLM分析间隔: {self.llm_analysis_interval}秒")
            print(f"⚙️  智能体: {'启用' if self.enable_autonomous_agent else '禁用'}")
            if duration_minutes > 0:
                print(f"⚙️  运行时长: {duration_minutes}分钟")
            else:
                print(f"⚙️  运行模式: 无限循环 (Ctrl+C停止)")
            print(f"{'='*60}")
            
            # 设置信号处理
            signal.signal(signal.SIGINT, self._signal_handler)
            
            start_time = datetime.now()
            last_llm_analysis = datetime.now() - timedelta(seconds=self.llm_analysis_interval)
            
            cycle_count = 0
            
            while self.running:
                try:
                    current_time = datetime.now()
                    
                    # 检查是否需要停止
                    if duration_minutes > 0:
                        elapsed_minutes = (current_time - start_time).total_seconds() / 60
                        if elapsed_minutes >= duration_minutes:
                            logger.info(f"达到设定运行时长 {duration_minutes}分钟，停止监控")
                            break
                    
                    cycle_count += 1
                    logger.info(f"开始第{cycle_count}次监控循环")
                    
                    # 判断是否需要进行LLM分析
                    time_since_llm = (current_time - last_llm_analysis).total_seconds()
                    include_llm = time_since_llm >= self.llm_analysis_interval
                    
                    if include_llm:
                        last_llm_analysis = current_time
                    
                    # 执行分析
                    result = self.run_single_analysis(
                        include_llm=include_llm,
                        include_agent=self.enable_autonomous_agent
                    )
                    
                    # 显示结果（简化版）
                    if result.get('success'):
                        state = result['state_analysis']['state']
                        confidence = result['state_analysis']['confidence']
                        print(f"\n[{current_time.strftime('%H:%M:%S')}] 🧠 {state} (置信度: {confidence:.2f})")
                        
                        if result.get('agent_summary', {}).get('executed_actions_count', 0) > 0:
                            actions = result['agent_summary']['executed_actions_count']
                            print(f"   🎯 执行了 {actions} 个智能体行为")
                    else:
                        print(f"\n[{current_time.strftime('%H:%M:%S')}] ❌ 分析失败")
                    
                    # 等待下次循环
                    if self.running:
                        time.sleep(self.analysis_interval)
                    
                except KeyboardInterrupt:
                    logger.info("收到中断信号，正在停止...")
                    break
                except Exception as e:
                    logger.error(f"监控循环异常: {e}")
                    if self.running:
                        time.sleep(self.analysis_interval)
            
            # 显示统计信息
            self._display_final_stats()
            
        except Exception as e:
            logger.error(f"持续监控模式失败: {e}")
            raise
        finally:
            self.running = False

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        logger.info("收到停止信号，正在优雅退出...")
        self.running = False

    def _display_final_stats(self):
        """显示最终统计信息"""
        if not self.stats['start_time']:
            return
        
        start_time = datetime.fromisoformat(self.stats['start_time'])
        total_duration = (datetime.now() - start_time).total_seconds()
        
        print(f"\n{'='*60}")
        print(f"📊 Mind Daemon 运行统计")
        print(f"{'='*60}")
        print(f"⏱️  总运行时长: {total_duration/60:.1f} 分钟")
        print(f"🔄 总分析次数: {self.stats['total_analyses']}")
        print(f"🤖 LLM分析次数: {self.stats['llm_analyses']}")
        print(f"🎯 智能体行为次数: {self.stats['agent_actions']}")
        if self.stats['total_analyses'] > 0:
            print(f"📈 平均分析间隔: {total_duration/self.stats['total_analyses']:.1f} 秒")
        print(f"{'='*60}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Mind Daemon - BCI精神状态分析系统')
    
    parser.add_argument('--mode', choices=['single', 'continuous'], default='single',
                       help='运行模式: single(单次分析) 或 continuous(持续监控)')
    parser.add_argument('--duration', type=int, default=0,
                       help='持续监控时长（分钟），0表示无限运行')
    parser.add_argument('--interval', type=int, default=60,
                       help='分析间隔（秒）')
    parser.add_argument('--llm-interval', type=int, default=300,
                       help='LLM分析间隔（秒）')
    parser.add_argument('--no-agent', action='store_true',
                       help='禁用智能体自主行为')
    parser.add_argument('--no-llm', action='store_true',
                       help='禁用LLM深度分析')
    parser.add_argument('--verbose', action='store_true',
                       help='启用详细日志')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 构建配置
    config = {
        'analysis_interval': args.interval,
        'llm_analysis_interval': args.llm_interval,
        'enable_autonomous_agent': not args.no_agent
    }
    
    try:
        # 创建系统实例
        system = MindDaemonSystem(config)
        
        if args.mode == 'single':
            # 单次分析模式
            print("🧠 Mind Daemon - 单次分析模式")
            result = system.run_single_analysis(
                include_llm=not args.no_llm,
                include_agent=not args.no_agent
            )
            system.display_analysis_result(result)
            
        else:
            # 持续监控模式
            system.run_continuous_monitoring(duration_minutes=args.duration)
        
        logger.info("Mind Daemon正常退出")
        
    except KeyboardInterrupt:
        logger.info("用户中断程序")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())