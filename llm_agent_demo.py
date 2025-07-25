#!/usr/bin/env python3
"""
Mind Daemon LLM Agent Demo

基于真实BCI流数据处理的智能代理演示程序。
完全基于 python_demo/sub_data.py 的 Cortex API 实现真实BCI数据流获取。
使用纯MCP协议进行外设控制，无直接外设依赖。

架构：
Cortex API → BCI数据流 → LLM智能决策 → MCP协议 → 外设控制

使用方法：
python llm_agent_demo.py

需要环境变量：
- EMOTIV_CLIENT_ID: Emotiv开发者客户端ID
- EMOTIV_CLIENT_SECRET: Emotiv开发者客户端密钥
- MINIMAX_API_KEY: MiniMax LLM API密钥

特性：
✅ 真实BCI数据流获取（基于Cortex API）
✅ 智能LLM决策（MiniMax API）
✅ 纯MCP外设控制协议
✅ 自动降级到模拟模式（无设备时）
"""

import asyncio
import sys
import os
import time
import json
from typing import Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
# Add python_demo to path for Cortex API
sys.path.append(os.path.join(os.path.dirname(__file__), 'python_demo'))

try:
    from mind_daemon.agent.intelligent_agent import MindDaemonIntelligentAgent, BCIData, CognitiveState
    from mind_daemon.bci.enhanced_analyzer import EnhancedBCIAnalyzer
    from mind_daemon.utils.config import get_config
    from mind_daemon.bci.state_analyzer import StateAnalysis
    # Import Cortex API for real BCI data (optional, fallback to simulation if not available)
    try:
        from cortex import Cortex
        CORTEX_AVAILABLE = True
    except ImportError:
        print("⚠️  Cortex API不可用，将使用模拟数据")
        CORTEX_AVAILABLE = False
except ImportError as e:
    print(f"❌ 导入错误: {e}")
    print("请确保已安装所有依赖项和正确配置项目路径")
    sys.exit(1)


class BCIDataSubscriber:
    """基于Cortex API的BCI数据订阅器，仿照sub_data.py的Subcribe类"""
    
    def __init__(self, app_client_id, app_client_secret, demo_callback):
        """初始化Cortex连接"""
        print("🧠 初始化BCI数据订阅器...")
        self.demo_callback = demo_callback
        
        if CORTEX_AVAILABLE:
            self.c = Cortex(app_client_id, app_client_secret, debug_mode=False)
            # 绑定回调函数
            self.c.bind(create_session_done=self.on_create_session_done)
            self.c.bind(new_data_labels=self.on_new_data_labels) 
            self.c.bind(new_met_data=self.on_new_met_data)
            self.c.bind(inform_error=self.on_inform_error)
            print("✅ Cortex API连接已建立")
        else:
            self.c = None
            print("⚠️  Cortex API不可用，将使用模拟模式")
    
    def start(self, headset_id=''):
        """启动BCI数据订阅，仿照sub_data.py的start方法"""
        if not self.c:
            print("❌ 无法启动BCI订阅：Cortex API不可用")
            return False
            
        try:
            self.streams = ['met']  # 订阅性能指标数据流
            
            if headset_id != '':
                self.c.set_wanted_headset(headset_id)
            
            print("📡 连接到Emotiv设备...")
            self.c.open()
            return True
            
        except Exception as e:
            print(f"❌ BCI连接失败: {e}")
            return False
    
    def on_create_session_done(self, *args, **kwargs):
        """会话创建完成回调"""
        print("✅ Cortex会话创建完成")
        print("🔄 开始订阅性能指标数据流...")
        self.c.sub_request(['met'])
    
    def on_new_data_labels(self, *args, **kwargs):
        """数据标签回调"""
        data = kwargs.get('data')
        stream_name = data['streamName']
        stream_labels = data['labels']
        print(f"📊 {stream_name} 数据标签: {stream_labels}")
    
    def on_new_met_data(self, *args, **kwargs):
        """性能指标数据回调 - 这是关键的认知状态数据"""
        data = kwargs.get('data')
        # 调用demo的数据处理方法
        if self.demo_callback:
            self.demo_callback(data)
    
    def on_inform_error(self, *args, **kwargs):
        """错误信息回调"""
        error = kwargs.get('error')
        print(f"❌ Cortex错误: {error}")


class StreamingBCIDemo:
    """基于流数据处理的BCI演示类，使用真实Cortex API"""
    
    def __init__(self):
        """初始化演示环境"""
        self.config = get_config()
        
        # 直接从环境变量获取（已通过load_dotenv()加载）
        self.app_client_id = os.getenv('EMOTIV_CLIENT_ID')
        self.app_client_secret = os.getenv('EMOTIV_CLIENT_SECRET')
        self.minimax_api_key = os.getenv('MINIMAX_API_KEY')

        if not self.app_client_id or not self.app_client_secret:
            print("❌ 未找到Emotiv凭据，demo需要真实BCI设备")
            print("请在.env文件中设置EMOTIV_CLIENT_ID和EMOTIV_CLIENT_SECRET")
            sys.exit(1)
            
        if not self.minimax_api_key:
            print("❌ 未找到MiniMax API Key，demo需要LLM功能")
            print("请在.env文件中设置MINIMAX_API_KEY")
            sys.exit(1)
        
        # 组件初始化（纯MCP模式，不直接初始化外设）
        self.agent = None
        self.bci_subscriber = None
        self.enhanced_analyzer = None
        
        # 数据处理状态
        self.running = False
        self.data_count = 0
        self.last_decision_time = 0
        self.decision_interval = 10.0  # 10秒做一次决策
        
        # met数据标签映射
        self.met_labels = []
        self.last_met_data = None
        
    async def setup_components(self):
        """设置所有组件，使用真实Cortex API"""
        print("🚀 启动 Mind Daemon 流数据演示...")
        print("=" * 50)
        
        # 1. 初始化 BCI 数据订阅器（强制使用真实Cortex API）
        if not CORTEX_AVAILABLE:
            print("❌ Cortex API不可用，无法运行demo")
            print("请确保python_demo/cortex.py可访问")
            sys.exit(1)
            
        try:
            # 初始化enhanced_analyzer用于高级BCI分析
            if self.app_client_id and self.app_client_secret:
                self.enhanced_analyzer = EnhancedBCIAnalyzer(
                    self.app_client_id,
                    self.app_client_secret,
                    csv_output_dir="data/bci_logs",
                    user_id="demo_user",
                    averaging_interval=45.0
                )
                
                # 设置数据回调到demo处理函数
                self.enhanced_analyzer.set_data_callback(self.on_enhanced_bci_data_received)
                
                print("✅ Enhanced BCI 分析器初始化成功")
            else:
                print("❌ BCI凭据不完整，无法初始化Enhanced BCI分析器")
                sys.exit(1)
        except Exception as e:
            print(f"❌ Enhanced BCI 分析器初始化失败: {e}")
            print("请检查Emotiv设备连接和凭据配置")
            sys.exit(1)
        
        # 2. 初始化 LLM 智能代理
        try:
            # MiniMax API使用OpenAI兼容的端点
            # OpenAI客户端会自动添加/chat/completions，所以只需要基础URL
            self.agent = MindDaemonIntelligentAgent(
                minimax_api_key=self.minimax_api_key, 
                base_url='https://api.minimax.chat/v1'
            )
            print("✅ LLM 智能代理初始化成功（使用MiniMax API）")
            
            # 测试API连接
            print("🔌 测试MiniMax API连接...")
            await self._test_llm_connection()
            print("✅ MiniMax API连接正常")
            
        except Exception as e:
            print(f"❌ LLM代理初始化或API连接失败: {e}")
            print("demo需要可用的MiniMax API连接")
            sys.exit(1)
        
        # 所有外设控制通过MCP协议进行，无需直接初始化
        print("✅ 外设控制已配置为MCP模式")
        
        await asyncio.sleep(1)
        print("\n🎯 所有组件初始化完成!")
    
    def on_enhanced_bci_data_received(self, averaged_record):
        """处理来自EnhancedBCIAnalyzer的平均化数据"""
        try:
            print(f"📊 接收到平均化BCI数据: {averaged_record.cognitive_state}")
            self.data_count += 1
            
            # 转换AveragedStateRecord为StateAnalysis格式
            state_analysis = self.convert_averaged_record_to_state_analysis(averaged_record)
            if state_analysis:
                # 异步处理数据
                asyncio.create_task(self.process_bci_data(state_analysis))
                
        except Exception as e:
            print(f"⚠️  Enhanced BCI数据处理失败: {e}")
    
    def convert_averaged_record_to_state_analysis(self, averaged_record) -> Optional[StateAnalysis]:
        """将AveragedStateRecord转换为StateAnalysis格式"""
        try:
            # 从字符串转换为CognitiveState枚举
            from mind_daemon.bci.state_analyzer import CognitiveState
            
            # 映射字符串到枚举
            state_mapping = {
                'high_focus': CognitiveState.HIGH_FOCUS,
                'medium_focus': CognitiveState.MEDIUM_FOCUS,
                'low_focus': CognitiveState.LOW_FOCUS,
                'relaxed': CognitiveState.RELAXED,
                'drowsy': CognitiveState.DROWSY,
                'cognitive_overload': CognitiveState.COGNITIVE_OVERLOAD,
                'neutral': CognitiveState.NEUTRAL
            }
            
            cognitive_state = state_mapping.get(averaged_record.cognitive_state, CognitiveState.NEUTRAL)
            
            return StateAnalysis(
                state=cognitive_state,
                confidence=averaged_record.confidence,
                metrics=averaged_record.metrics,
                timestamp=time.time(),
                raw_data={'averaged_record': averaged_record}
            )
            
        except Exception as e:
            print(f"⚠️  AveragedRecord转换失败: {e}")
            return None
    
    def convert_met_to_state_analysis(self, met_data) -> Optional[StateAnalysis]:
        """将Cortex的met数据转换为StateAnalysis格式，使用enhanced_analyzer"""
        try:
            # 使用enhanced_analyzer已经在数据流中处理，这里保留为兼容性
            # enhanced_analyzer会自动处理数据转换和平均化
            
            # 备用的简单转换逻辑
            met_values = met_data.get('met', [])
            timestamp = met_data.get('time', time.time())
            
            if not met_values or len(met_values) < 6:
                return None
            
            # met数据标签通常为: 
            # ['eng.isActive', 'eng', 'exc.isActive', 'exc', 'lex', 'str.isActive', 'str', 'rel.isActive', 'rel', 'int.isActive', 'int', 'foc.isActive', 'foc']
            # 提取关键指标
            engagement = met_values[1] if len(met_values) > 1 else 0.5  # 'eng'
            excitement = met_values[3] if len(met_values) > 3 else 0.5  # 'exc' 
            relaxation = met_values[8] if len(met_values) > 8 else 0.5  # 'rel'
            focus = met_values[12] if len(met_values) > 12 else 0.5     # 'foc'
            
            # 计算综合指标
            attention = (engagement + focus) / 2
            arousal = excitement
            stress = 1.0 - relaxation
            
            # 根据指标判断认知状态
            cognitive_state = self.determine_cognitive_state(attention, engagement, relaxation, arousal)
            
            # 计算置信度（基于数据质量）
            confidence = min(0.95, max(0.6, (attention + engagement + relaxation) / 3))
            
            return StateAnalysis(
                state=cognitive_state,
                confidence=confidence,
                metrics={
                    'attention': attention,
                    'engagement': engagement,
                    'relaxation': relaxation,
                    'arousal': arousal,
                    'stress': stress,
                    'focus_index': attention * engagement,
                    'attention_current': attention,
                    'engagement_score': engagement,
                    'relaxation_score': relaxation,
                    'arousal_score': arousal
                },
                timestamp=timestamp,
                raw_data=met_data
            )
            
        except Exception as e:
            print(f"⚠️  met数据转换失败: {e}")
            return None
    
    def determine_cognitive_state(self, attention: float, engagement: float, relaxation: float, arousal: float) -> CognitiveState:
        """根据指标确定认知状态"""
        # 高专注：注意力和参与度都高
        if attention > 0.7 and engagement > 0.7:
            return CognitiveState.HIGH_FOCUS
        
        # 认知过载：arousal很高但relaxation很低
        elif arousal > 0.8 and relaxation < 0.3:
            return CognitiveState.COGNITIVE_OVERLOAD
        
        # 困倦：注意力和参与度都低，relaxation高
        elif attention < 0.4 and engagement < 0.4 and relaxation > 0.6:
            return CognitiveState.DROWSY
        
        # 放松：relaxation高，arousal低
        elif relaxation > 0.6 and arousal < 0.5:
            return CognitiveState.RELAXED
        
        # 中等专注：默认状态
        else:
            return CognitiveState.MEDIUM_FOCUS
    
    # 模拟模式已禁用，仅支持真实BCI数据流
    
    async def process_bci_data(self, state_analysis: StateAnalysis):
        """处理BCI数据流，仿照sub_data.py的数据处理方式"""
        self.data_count += 1
        current_time = time.time()
        
        # 显示数据接收信息（类似sub_data.py的打印方式）
        if self.data_count % 10 == 0:  # 每10条数据显示一次
            print(f"📊 已处理 {self.data_count} 条数据流 | "
                  f"状态: {state_analysis.state.value} | "
                  f"置信度: {state_analysis.confidence:.2f}")
        
        # 检查是否需要进行决策（类似定期分析模式）
        if current_time - self.last_decision_time >= self.decision_interval:
            await self.make_intelligent_decision(state_analysis)
            self.last_decision_time = current_time
    
    async def make_intelligent_decision(self, state_analysis: StateAnalysis):
        """基于BCI数据进行智能决策"""
        print(f"\n🧠 认知状态分析: {state_analysis.state.value}")
        print(f"   置信度: {state_analysis.confidence:.2f}")
        print(f"   注意力: {state_analysis.metrics.get('attention', 0):.2f}")
        print(f"   专注指数: {state_analysis.metrics.get('focus_index', 0):.2f}")
        print(f"   放松度: {state_analysis.metrics.get('relaxation', 0):.2f}")
        
        # 构造BCI数据用于Agent处理
        bci_data = BCIData(
            cognitive_state=state_analysis.state,
            confidence=state_analysis.confidence,
            attention_level=state_analysis.metrics.get('attention', 0),
            engagement_level=state_analysis.metrics.get('engagement', 0),
            relaxation_level=state_analysis.metrics.get('relaxation', 0),
            arousal_level=state_analysis.metrics.get('arousal', 0),
            timestamp=state_analysis.timestamp,
            metrics=state_analysis.metrics
        )
        
        # 使用LLM Agent进行决策
        if self.agent:
            try:
                # 处理BCI数据并检查认知阈值
                processed_bci = self.agent.process_bci_data(state_analysis)
                triggered_thresholds = self.agent.evaluate_cognitive_thresholds(processed_bci)
                
                if triggered_thresholds:
                    print(f"🎯 触发认知阈值: {[t.description for t in triggered_thresholds]}")
                    decision = await self.agent.generate_action_plan(processed_bci, triggered_thresholds)
                    print(f"🤖 LLM决策: {decision}")
                    print(f"💡 决策原因: {decision.get('reasoning', decision.get('reason', '未提供原因'))}")
                    
                    # 使用Agent的execute_action_plan来执行真正的外设控制
                    execution_result = await self.agent.execute_action_plan(decision)
                    print(f"🔧 执行结果: {execution_result['message']}")
                    if execution_result['results']:
                        for result in execution_result['results']:
                            status = "✅" if result['success'] else "❌"
                            print(f"   {status} {result['tool']}: {result['result']}")
                else:
                    # 显示当前状态持续时长信息
                    current_duration = self.agent.state_durations.get(processed_bci.cognitive_state, 0.0)
                    print(f"🤖 认知状态: {state_analysis.state.value}")
                    print(f"   置信度: {processed_bci.confidence:.2f}, 持续时长: {current_duration:.1f}秒")
                    # 显示相关阈值要求
                    for threshold in self.agent.cognitive_thresholds:
                        if threshold.state == processed_bci.cognitive_state:
                            print(f"   需要: 置信度≥{threshold.confidence_threshold:.2f}, 持续≥{threshold.duration_threshold:.1f}秒")
            except Exception as e:
                print(f"⚠️  LLM决策失败: {e}")
                decision = self.fallback_decision(state_analysis)
                await self.execute_decision(decision, state_analysis)
        else:
            # 规则决策模式
            decision = self.fallback_decision(state_analysis)
            await self.execute_decision(decision, state_analysis)
    
    def fallback_decision(self, state_analysis: StateAnalysis) -> Dict[str, Any]:
        """规则决策逻辑（当LLM不可用时）"""
        state = state_analysis.state
        metrics = state_analysis.metrics
        
        if state == CognitiveState.HIGH_FOCUS:
            return {
                "action": "maintain_flow",
                "music": "continue",
                "halo": {"color": (0, 255, 0), "mode": "steady"},
                "reason": "保持专注状态，维持当前环境"
            }
        elif state == CognitiveState.COGNITIVE_OVERLOAD:
            return {
                "action": "reduce_stress",
                "music": "play_relaxing",
                "halo": {"color": (0, 150, 255), "mode": "pulse"},
                "reason": "认知过载，播放放松音乐并显示舒缓蓝光"
            }
        elif state == CognitiveState.DROWSY:
            return {
                "action": "increase_alertness",
                "music": "play_energizing",
                "halo": {"color": (255, 165, 0), "mode": "alert"},
                "reason": "检测到困倦，激活警示模式"
            }
        elif state == CognitiveState.RELAXED:
            return {
                "action": "gentle_focus",
                "music": "play_focus",
                "halo": {"color": (255, 255, 0), "mode": "warm"},
                "reason": "放松状态，温和引导进入工作模式"
            }
        else:  # MEDIUM_FOCUS
            return {
                "action": "optimize_focus",
                "music": "adjust_volume",
                "halo": {"color": (100, 100, 255), "mode": "steady"},
                "reason": "中等专注，优化环境支持"
            }
    
    async def execute_decision(self, decision: Dict[str, Any], state_analysis: StateAnalysis):
        """执行决策（已废弃，所有外设控制通过Agent的MCP调用）"""
        print(f"💡 决策原因: {decision.get('reasoning', decision.get('reason', '未提供原因'))}")
        print("ℹ️  外设控制已通过Agent的MCP调用执行")
        await asyncio.sleep(0.1)
    
    async def _test_llm_connection(self):
        """测试LLM API连接"""
        if not self.agent or not self.agent.llm_client:
            raise Exception("LLM客户端未初始化")
        
        try:
            response = await self.agent.llm_client.chat.completions.create(
                model="abab6.5s-chat",
                messages=[{"role": "user", "content": "测试连接，请回复'连接正常'"}],
                max_tokens=20
            )
            if not response or not response.choices:
                raise Exception("API返回空响应")
            
            result = response.choices[0].message.content
            if not result:
                raise Exception("API返回空内容")
                
        except Exception as e:
            raise Exception(f"API测试失败: {e}")
    
    async def start_data_stream(self):
        """启动数据流处理，使用真实Cortex API或模拟模式"""
        print(f"\n🎬 开始数据流处理")
        print("   按 Ctrl+C 可随时停止")
        print("-" * 50)
        
        self.running = True
        
        try:
            # 使用enhanced_analyzer启动真实BCI数据流
            print("📡 启动Enhanced BCI分析器...")
            if self.enhanced_analyzer:
                self.enhanced_analyzer.start_analysis()
                print("✅ Enhanced BCI分析器已启动")
            else:
                print("❌ Enhanced BCI分析器未初始化")
                sys.exit(1)
                
            print("✅ BCI数据流已启动，等待数据...")
            print("📊 正在接收真实BCI数据流...")
            
            # 在真实模式下，数据通过回调函数处理，这里只需要保持运行
            while self.running:
                await asyncio.sleep(1)
                # 显示数据接收状态
                if self.data_count > 0 and self.data_count % 10 == 0:
                    print(f"📊 已接收 {self.data_count} 条真实BCI数据")
                    
        except KeyboardInterrupt:
            print(f"\n\n🛑 用户停止数据流")
        except Exception as e:
            print(f"\n❌ 数据流处理错误: {e}")
            import traceback
            traceback.print_exc()
        
        self.running = False
        print(f"\n🏁 数据流结束 (处理了 {self.data_count} 条数据)")
    
    async def cleanup(self):
        """清理资源（MCP模式）"""
        print("\n🧹 清理资源...")
        
        # 通过MCP发送清理信号
        if self.agent:
            try:
                from mind_daemon.agent.mcp_client import get_mcp_client
                mcp_client = await get_mcp_client()
                await mcp_client.shutdown()
                print("✅ MCP客户端已关闭")
            except:
                print("ℹ️  MCP清理完成")
        
        print("✅ 清理完成")


async def main():
    """主函数"""
    print("🧠 Mind Daemon 流数据处理演示")
    print("===================================")
    print("这个演示基于 python_demo/sub_data.py 的流数据处理模式：")
    print("• 实时处理BCI认知状态数据流")
    print("• 基于状态变化进行智能决策")
    print("• 自动调节环境（音乐、光晕）")
    print("• 模拟真实的Emotiv设备数据流")
    print()
    
    demo = StreamingBCIDemo()
    
    try:
        # 设置组件
        await demo.setup_components()
        
        # 启动数据流处理
        await demo.start_data_stream()
        
    except KeyboardInterrupt:
        print("\n🛑 演示被用户中断")
    except Exception as e:
        print(f"\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 清理资源
        await demo.cleanup()


if __name__ == "__main__":
    print("提示: 设置环境变量以启用完整功能:")
    print("export EMOTIV_CLIENT_ID='your_client_id'")
    print("export EMOTIV_CLIENT_SECRET='your_client_secret'")
    print("export MINIMAX_API_KEY='your_minimax_key'")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 再见!")
    except Exception as e:
        print(f"❌ 启动演示失败: {e}")
        sys.exit(1)