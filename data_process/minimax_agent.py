"""
Task 3: MiniMax智能体 - 基于阈值和经验的行为决策系统

功能：
- 基于精神状态分析结果进行阈值判断
- 调用MiniMax API进行智能决策
- 执行预定义的干预行为（音乐、提醒、环境调节等）
- 支持MCP服务调用
- 提供用户通知和建议

作者：Mind Daemon Project
"""

import os
import json
import requests
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import logging

# 导入其他模块
from state_analyzer import StateAnalyzer, MentalState, StateAnalysisResult
from llm_analyzer import LLMAnalyzer, LLMAnalysisResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ActionType(Enum):
    """行为类型枚举"""
    PLAY_MUSIC = "play_music"
    SHOW_NOTIFICATION = "show_notification"
    ADJUST_ENVIRONMENT = "adjust_environment"
    SUGGEST_BREAK = "suggest_break"
    FOCUS_REMINDER = "focus_reminder"
    RELAXATION_GUIDE = "relaxation_guide"
    MCP_SERVICE_CALL = "mcp_service_call"
    CUSTOM_OUTPUT = "custom_output"

class ActionPriority(Enum):
    """行为优先级"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    URGENT = 4

@dataclass
class ActionDefinition:
    """行为定义"""
    action_type: ActionType
    priority: ActionPriority
    description: str
    parameters: Dict[str, Any]
    cooldown_minutes: int = 10  # 冷却时间，避免重复触发
    
@dataclass
class ThresholdRule:
    """阈值规则"""
    rule_name: str
    condition: str  # 条件表达式
    target_states: List[MentalState]
    min_confidence: float
    actions: List[ActionDefinition]
    enabled: bool = True

@dataclass 
class AgentAction:
    """智能体执行的行为记录"""
    action_type: ActionType
    timestamp: str
    trigger_state: MentalState
    description: str
    parameters: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None

class MiniMaxAgent:
    """MiniMax智能体主类"""
    
    def __init__(self, config_path: str = None):
        """
        初始化MiniMax智能体
        
        Args:
            config_path: 配置文件路径，默认读取.env
        """
        # 加载环境配置
        self.config = self._load_config(config_path)
        
        # 初始化分析器
        self.state_analyzer = StateAnalyzer()
        self.llm_analyzer = LLMAnalyzer()
        
        # 初始化行为记录
        self.action_history: List[AgentAction] = []
        
        # 初始化阈值规则
        self.threshold_rules = self._initialize_threshold_rules()
        
        # MiniMax API配置
        self.minimax_api_key = self.config.get('MINIMAX_API_KEY', '')
        self.minimax_base_url = self.config.get('MINIMAX_BASE_URL', 'https://api.minimax.chat/v1/text/chatcompletion_v2')
        
        logger.info("MiniMax智能体初始化完成")

    def _load_config(self, config_path: str = None) -> Dict[str, str]:
        """加载配置文件"""
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), '..', '.env')
        
        config = {}
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
                logger.info(f"配置文件加载成功: {config_path}")
            else:
                logger.warning(f"配置文件不存在: {config_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
        
        return config

    def _initialize_threshold_rules(self) -> List[ThresholdRule]:
        """初始化阈值规则"""
        rules = [
            # 高压力状态规则
            ThresholdRule(
                rule_name="高压力干预",
                condition="state == MentalState.STRESSED and confidence > 0.7",
                target_states=[MentalState.STRESSED],
                min_confidence=0.7,
                actions=[
                    ActionDefinition(
                        action_type=ActionType.PLAY_MUSIC,
                        priority=ActionPriority.HIGH,
                        description="播放放松音乐",
                        parameters={"music_type": "relax", "volume": 0.6},
                        cooldown_minutes=30
                    ),
                    ActionDefinition(
                        action_type=ActionType.RELAXATION_GUIDE,
                        priority=ActionPriority.MEDIUM,
                        description="提供放松指导",
                        parameters={"guide_type": "breathing"},
                        cooldown_minutes=60
                    )
                ]
            ),
            
            # 疲劳状态规则
            ThresholdRule(
                rule_name="疲劳检测",
                condition="state == MentalState.FATIGUED and confidence > 0.6",
                target_states=[MentalState.FATIGUED],
                min_confidence=0.6,
                actions=[
                    ActionDefinition(
                        action_type=ActionType.SUGGEST_BREAK,
                        priority=ActionPriority.HIGH,
                        description="建议休息",
                        parameters={"break_duration": 15},
                        cooldown_minutes=20
                    )
                ]
            ),
            
            # 分心状态规则  
            ThresholdRule(
                rule_name="注意力提醒",
                condition="state == MentalState.DISTRACTED and confidence > 0.6",
                target_states=[MentalState.DISTRACTED],
                min_confidence=0.6,
                actions=[
                    ActionDefinition(
                        action_type=ActionType.FOCUS_REMINDER,
                        priority=ActionPriority.MEDIUM,
                        description="专注力提醒",
                        parameters={"reminder_type": "gentle"},
                        cooldown_minutes=15
                    )
                ]
            ),
            
            # 专注状态维持规则
            ThresholdRule(
                rule_name="专注状态维持",
                condition="state == MentalState.FOCUSED and confidence > 0.8",
                target_states=[MentalState.FOCUSED],
                min_confidence=0.8,
                actions=[
                    ActionDefinition(
                        action_type=ActionType.ADJUST_ENVIRONMENT,
                        priority=ActionPriority.LOW,
                        description="优化环境设置",
                        parameters={"action": "maintain_focus"},
                        cooldown_minutes=45
                    )
                ]
            )
        ]
        
        return rules

    def evaluate_thresholds(self, state_result: StateAnalysisResult) -> List[ActionDefinition]:
        """
        评估阈值条件并返回需要执行的行为
        
        Args:
            state_result: 状态分析结果
            
        Returns:
            需要执行的行为列表
        """
        triggered_actions = []
        
        try:
            state = state_result.state
            confidence = state_result.confidence
            
            for rule in self.threshold_rules:
                if not rule.enabled:
                    continue
                
                # 检查状态匹配
                if state in rule.target_states and confidence >= rule.min_confidence:
                    # 检查冷却时间
                    for action in rule.actions:
                        if self._is_action_cooled_down(action):
                            triggered_actions.append(action)
                            logger.info(f"触发规则: {rule.rule_name}, 行为: {action.description}")
            
            # 按优先级排序
            triggered_actions.sort(key=lambda x: x.priority.value, reverse=True)
            
        except Exception as e:
            logger.error(f"评估阈值失败: {e}")
        
        return triggered_actions

    def _is_action_cooled_down(self, action: ActionDefinition) -> bool:
        """检查行为是否已过冷却时间"""
        try:
            # 查找最后一次执行相同类型行为的时间
            now = datetime.now()
            for history_action in reversed(self.action_history):
                if history_action.action_type == action.action_type:
                    last_time = datetime.fromisoformat(history_action.timestamp)
                    if (now - last_time).total_seconds() < action.cooldown_minutes * 60:
                        return False
                    break
            return True
        except Exception:
            return True

    def call_minimax_api(self, prompt: str, temperature: float = 0.7) -> str:
        """
        调用MiniMax API
        
        Args:
            prompt: 输入prompt
            temperature: 随机性控制
            
        Returns:
            API响应内容
        """
        try:
            if not self.minimax_api_key:
                logger.warning("MiniMax API Key未配置，使用模拟响应")
                return self._generate_mock_minimax_response(prompt)
            
            headers = {
                'Authorization': f'Bearer {self.minimax_api_key}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                "model": "abab6.5s-chat",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature,
                "max_tokens": 1000
            }
            
            response = requests.post(
                self.minimax_base_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                logger.error(f"MiniMax API错误: {response.status_code} - {response.text}")
                return self._generate_mock_minimax_response(prompt)
                
        except Exception as e:
            logger.error(f"调用MiniMax API失败: {e}")
            return self._generate_mock_minimax_response(prompt)

    def _generate_mock_minimax_response(self, prompt: str) -> str:
        """生成模拟的MiniMax响应"""
        if "压力" in prompt or "stress" in prompt.lower():
            return "建议进行深呼吸练习，播放舒缓音乐，并考虑短暂休息10-15分钟。"
        elif "疲劳" in prompt or "fatigue" in prompt.lower():
            return "检测到疲劳状态，建议立即休息15-30分钟，进行轻度运动或眼部按摩。"
        elif "分心" in prompt or "distract" in prompt.lower():
            return "注意力不集中，建议清理工作区域，关闭不必要的应用程序，使用番茄工作法。"
        else:
            return "维持当前状态，继续专注工作。建议每45分钟进行5分钟休息。"

    def generate_action_strategy(self, state_result: StateAnalysisResult, 
                               llm_result: Optional[LLMAnalysisResult] = None) -> str:
        """
        使用MiniMax生成行为策略
        
        Args:
            state_result: 状态分析结果
            llm_result: LLM分析结果（可选）
            
        Returns:
            生成的策略建议
        """
        
        # 构建策略生成prompt
        prompt = f"""你是一个专业的认知辅助系统，基于用户的BCI脑机接口数据分析结果，提供具体的行为建议。

当前用户状态分析：
- 精神状态: {state_result.state.name}
- 置信度: {state_result.confidence:.2f}
- 详细信息: {state_result.details}

关键指标：
"""
        
        for key, value in state_result.metrics.items():
            prompt += f"- {key}: {value:.3f}\n"
        
        if llm_result:
            prompt += f"\nLLM深度分析：\n- 状态评估: {llm_result.mental_state_assessment}\n"
            prompt += f"- 关键洞察: {', '.join(llm_result.key_insights[:2])}\n"
        
        prompt += f"""
请基于以上信息，提供3-5个具体的、可执行的建议来优化用户的精神状态。建议应该：
1. 针对当前状态的具体问题
2. 可以立即执行
3. 考虑用户的工作或生活场景
4. 包含具体的时间建议

请用简洁明确的语言回复，每个建议一行。"""

        return self.call_minimax_api(prompt)

    def execute_action(self, action: ActionDefinition, 
                      context: Dict[str, Any] = None) -> AgentAction:
        """
        执行具体的行为
        
        Args:
            action: 行为定义
            context: 执行上下文
            
        Returns:
            行为执行记录
        """
        context = context or {}
        timestamp = datetime.now().isoformat()
        
        try:
            success = False
            error_message = None
            
            if action.action_type == ActionType.PLAY_MUSIC:
                success = self._execute_play_music(action.parameters)
                
            elif action.action_type == ActionType.SHOW_NOTIFICATION:
                success = self._execute_show_notification(action.parameters)
                
            elif action.action_type == ActionType.ADJUST_ENVIRONMENT:
                success = self._execute_adjust_environment(action.parameters)
                
            elif action.action_type == ActionType.SUGGEST_BREAK:
                success = self._execute_suggest_break(action.parameters)
                
            elif action.action_type == ActionType.FOCUS_REMINDER:
                success = self._execute_focus_reminder(action.parameters)
                
            elif action.action_type == ActionType.RELAXATION_GUIDE:
                success = self._execute_relaxation_guide(action.parameters)
                
            elif action.action_type == ActionType.MCP_SERVICE_CALL:
                success = self._execute_mcp_service_call(action.parameters)
                
            elif action.action_type == ActionType.CUSTOM_OUTPUT:
                success = self._execute_custom_output(action.parameters)
                
            else:
                success = False
                error_message = f"未知的行为类型: {action.action_type}"
            
            # 记录行为
            agent_action = AgentAction(
                action_type=action.action_type,
                timestamp=timestamp,
                trigger_state=context.get('trigger_state', MentalState.NEUTRAL),
                description=action.description,
                parameters=action.parameters,
                success=success,
                error_message=error_message
            )
            
            self.action_history.append(agent_action)
            
            if success:
                logger.info(f"行为执行成功: {action.description}")
            else:
                logger.error(f"行为执行失败: {action.description} - {error_message}")
            
            return agent_action
            
        except Exception as e:
            error_message = str(e)
            logger.error(f"执行行为异常: {action.description} - {error_message}")
            
            agent_action = AgentAction(
                action_type=action.action_type,
                timestamp=timestamp,
                trigger_state=context.get('trigger_state', MentalState.NEUTRAL),
                description=action.description,
                parameters=action.parameters,
                success=False,
                error_message=error_message
            )
            
            self.action_history.append(agent_action)
            return agent_action

    def _execute_play_music(self, params: Dict[str, Any]) -> bool:
        """执行播放音乐行为"""
        try:
            music_type = params.get('music_type', 'focus')
            volume = params.get('volume', 0.5)
            
            # 这里应该调用实际的音乐播放器
            # 现在只是模拟
            logger.info(f"播放{music_type}类型音乐，音量: {volume}")
            
            # 模拟音乐播放命令
            music_dir = self.config.get('MUSIC_DIR', 'music')
            if music_type == 'relax':
                music_path = os.path.join(music_dir, 'relax')
            else:
                music_path = os.path.join(music_dir, 'focus')
            
            logger.info(f"音乐文件路径: {music_path}")
            return True
            
        except Exception as e:
            logger.error(f"播放音乐失败: {e}")
            return False

    def _execute_show_notification(self, params: Dict[str, Any]) -> bool:
        """执行显示通知行为"""
        try:
            message = params.get('message', '系统通知')
            duration = params.get('duration', 5)
            
            print(f"\n🔔 系统通知: {message}")
            print(f"   (显示时长: {duration}秒)")
            
            return True
            
        except Exception as e:
            logger.error(f"显示通知失败: {e}")
            return False

    def _execute_adjust_environment(self, params: Dict[str, Any]) -> bool:
        """执行环境调节行为"""
        try:
            action = params.get('action', 'optimize')
            
            # 这里应该调用光环控制、亮度调节等
            logger.info(f"调节环境: {action}")
            
            # 模拟环境调节
            if action == 'maintain_focus':
                print("🌟 优化专注环境: 调节屏幕亮度，启用专注模式")
            elif action == 'relax_mode':
                print("🌙 切换放松环境: 降低亮度，启用暖色调")
            
            return True
            
        except Exception as e:
            logger.error(f"环境调节失败: {e}")
            return False

    def _execute_suggest_break(self, params: Dict[str, Any]) -> bool:
        """执行休息建议行为"""
        try:
            duration = params.get('break_duration', 15)
            
            print(f"\n⏰ 休息建议: 检测到疲劳状态，建议休息{duration}分钟")
            print("   建议活动: 眼部放松、伸展运动、深呼吸")
            
            return True
            
        except Exception as e:
            logger.error(f"休息建议失败: {e}")
            return False

    def _execute_focus_reminder(self, params: Dict[str, Any]) -> bool:
        """执行专注提醒行为"""
        try:
            reminder_type = params.get('reminder_type', 'gentle')
            
            if reminder_type == 'gentle':
                print("\n🎯 温和提醒: 注意力似乎有些分散，试试深呼吸后重新集中注意力")
            else:
                print("\n⚡ 专注提醒: 请关注当前任务，消除干扰因素")
            
            return True
            
        except Exception as e:
            logger.error(f"专注提醒失败: {e}")
            return False

    def _execute_relaxation_guide(self, params: Dict[str, Any]) -> bool:
        """执行放松指导行为"""
        try:
            guide_type = params.get('guide_type', 'breathing')
            
            if guide_type == 'breathing':
                print("\n🌸 放松指导: 进行4-7-8呼吸法")
                print("   1. 吸气4秒")
                print("   2. 屏气7秒") 
                print("   3. 呼气8秒")
                print("   重复3-5次")
            
            return True
            
        except Exception as e:
            logger.error(f"放松指导失败: {e}")
            return False

    def _execute_mcp_service_call(self, params: Dict[str, Any]) -> bool:
        """执行MCP服务调用行为"""
        try:
            service = params.get('service', 'unknown')
            method = params.get('method', 'call')
            
            # 这里应该调用实际的MCP服务
            logger.info(f"调用MCP服务: {service}.{method}")
            
            # 模拟MCP调用
            print(f"🔗 MCP服务调用: {service}.{method}")
            
            return True
            
        except Exception as e:
            logger.error(f"MCP服务调用失败: {e}")
            return False

    def _execute_custom_output(self, params: Dict[str, Any]) -> bool:
        """执行自定义输出行为"""
        try:
            output = params.get('output', '自定义输出')
            output_type = params.get('type', 'info')
            
            if output_type == 'warning':
                print(f"⚠️  {output}")
            elif output_type == 'success':
                print(f"✅ {output}")
            else:
                print(f"ℹ️  {output}")
            
            return True
            
        except Exception as e:
            logger.error(f"自定义输出失败: {e}")
            return False

    def run_autonomous_cycle(self) -> Dict[str, Any]:
        """
        运行自主决策循环 (主要入口函数)
        
        Returns:
            执行结果摘要
        """
        try:
            logger.info("开始智能体自主决策循环")
            
            # 1. 获取当前状态分析
            state_result = self.state_analyzer.analyze_current_state()
            
            # 2. 获取LLM深度分析（可选）
            llm_result = None
            try:
                llm_result = self.llm_analyzer.analyze_mental_state(window_minutes=30)
            except Exception as e:
                logger.warning(f"LLM分析失败，跳过: {e}")
            
            # 3. 评估阈值并获取触发的行为
            triggered_actions = self.evaluate_thresholds(state_result)
            
            # 4. 生成智能策略
            strategy = self.generate_action_strategy(state_result, llm_result)
            
            # 5. 执行触发的行为
            executed_actions = []
            for action in triggered_actions[:3]:  # 限制同时执行的行为数量
                context = {'trigger_state': state_result.state}
                result = self.execute_action(action, context)
                executed_actions.append(result)
            
            # 6. 输出智能策略
            if strategy:
                print(f"\n🤖 MiniMax智能建议:\n{strategy}")
            
            # 7. 构建执行摘要
            summary = {
                'timestamp': datetime.now().isoformat(),
                'current_state': state_result.state.name,
                'confidence': state_result.confidence,
                'triggered_actions_count': len(triggered_actions),
                'executed_actions_count': len(executed_actions),
                'successful_actions': sum(1 for a in executed_actions if a.success),
                'strategy_generated': bool(strategy),
                'llm_analysis_available': llm_result is not None
            }
            
            logger.info(f"智能体循环完成: 执行了{len(executed_actions)}个行为")
            
            return summary
            
        except Exception as e:
            logger.error(f"智能体决策循环失败: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'success': False
            }

def main():
    """测试函数"""
    try:
        # 创建智能体
        agent = MiniMaxAgent()
        
        print("=== MiniMax智能体测试 ===\n")
        
        # 运行自主决策循环
        result = agent.run_autonomous_cycle()
        
        print(f"\n=== 执行摘要 ===")
        for key, value in result.items():
            print(f"{key}: {value}")
        
        # 显示最近的行为历史
        if agent.action_history:
            print(f"\n=== 行为历史 ===")
            for action in agent.action_history[-3:]:  # 显示最近3个行为
                status = "✅" if action.success else "❌"
                print(f"{status} {action.description} ({action.timestamp})")
        
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()