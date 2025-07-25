"""
WebSocket接口 - 为前端dashboard提供实时数据传输

功能：
- WebSocket服务器监听端口8889
- 每秒发送basic_params和advanced_params到前端
- 集成环境控制智能体
- 实时状态更新和同步

作者：Mind Daemon Project
"""

import asyncio
import websockets
import json
import time
import threading
from typing import Dict, Any, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# 导入其他模块
from ..analyzers.state_analyzer import StateAnalyzer, MentalState, StateAnalysisResult
from ..analyzers.llm_analyzer import LLMAnalyzer, LLMAnalysisResult
from ..agent.environment_agent import EnvironmentAgent
from ..bci.data_stream_service import get_data_stream_service
from ..utils.config import config

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class BasicParams:
    """基础参数结构"""
    light: Dict[str, Any]
    music: Dict[str, Any] 
    curtain: Dict[str, Any]
    Scores: Dict[str, int]  # 注意大写S
    timestamp: str

@dataclass 
class AdvancedParams:
    """高级参数结构"""
    State: str  # 注意大写S
    Summary: str  # 注意大写S
    Action: str  # 注意大写A
    timestamp: str

class WebSocketInterface:
    """WebSocket接口服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8889):
        """
        初始化WebSocket接口
        
        Args:
            host: 服务器主机地址
            port: 服务器端口
        """
        self.host = host
        self.port = port
        self.clients = set()
        self.running = False
        
        # 核心分析组件
        self.state_analyzer = StateAnalyzer()
        self.llm_analyzer = LLMAnalyzer()
        self.environment_agent = EnvironmentAgent()
        self.data_stream_service = get_data_stream_service()
        
        # 状态变量
        self.last_basic_params: Optional[BasicParams] = None
        self.last_advanced_params: Optional[AdvancedParams] = None
        self.last_analysis_time = 0
        
        # BCI实时数据缓存
        self.latest_bci_scores = {"At": 50, "Ex": 50, "Re": 50, "St": 50}
        self.bci_data_updated = False
        
        # 数据发送线程
        self.data_thread = None
        
        # 注册BCI数据流回调
        self.data_stream_service.add_data_callback(self._on_bci_data_update)
        
        logger.info(f"WebSocket接口初始化完成 - {host}:{port}")

    async def register_client(self, websocket):
        """注册新的WebSocket客户端"""
        self.clients.add(websocket)
        logger.info(f"新客户端连接: {websocket.remote_address}")
        
        # 发送最新数据给新客户端
        if self.last_basic_params and self.last_advanced_params:
            await self.send_to_client(websocket, {
                'basic': asdict(self.last_basic_params),
                'advanced': asdict(self.last_advanced_params)
            })

    async def unregister_client(self, websocket):
        """注销WebSocket客户端"""
        self.clients.discard(websocket)
        logger.info(f"客户端断开连接: {websocket.remote_address}")

    async def send_to_client(self, websocket, data: Dict[str, Any]):
        """向单个客户端发送数据"""
        try:
            await websocket.send(json.dumps(data))
        except websockets.exceptions.ConnectionClosed:
            await self.unregister_client(websocket)
        except Exception as e:
            logger.error(f"发送数据到客户端失败: {e}")

    async def broadcast_data(self, data: Dict[str, Any]):
        """向所有连接的客户端广播数据"""
        if not self.clients:
            return
        
        # 创建发送任务列表
        tasks = []
        for client in self.clients.copy():
            tasks.append(self.send_to_client(client, data))
        
        # 同时发送给所有客户端
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def handle_client(self, websocket, path=None):
        """处理客户端连接"""
        await self.register_client(websocket)
        try:
            async for message in websocket:
                # 处理来自客户端的消息（如果需要）
                try:
                    data = json.loads(message)
                    logger.info(f"收到客户端消息: {data}")
                except json.JSONDecodeError:
                    logger.warning(f"无效的JSON消息: {message}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    def _on_bci_data_update(self, data: Dict[str, Any]):
        """BCI数据更新回调函数"""
        try:
            scores = data.get('scores', {})
            logger.info(f"收到BCI数据回调: {data.keys()}")
            logger.info(f"提取的分数: {scores}")
            if scores:
                self.latest_bci_scores = scores.copy()
                self.bci_data_updated = True
                logger.info(f"BCI分数已更新: At={scores.get('At')} Ex={scores.get('Ex')} Re={scores.get('Re')} St={scores.get('St')}")
            else:
                logger.warning("BCI数据包中没有scores字段")
        except Exception as e:
            logger.error(f"BCI数据更新回调失败: {e}")

    def generate_basic_params(self) -> BasicParams:
        """生成基础参数"""
        try:
            # 获取当前环境状态
            env_state = self.environment_agent.get_current_environment_state()
            
            # 使用实时BCI数据
            scores = self.latest_bci_scores.copy()
            
            return BasicParams(
                light=env_state["light"],
                music=env_state["music"],
                curtain=env_state["curtain"],
                Scores=scores,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"生成基础参数失败: {e}")
            # 返回默认参数
            return BasicParams(
                light={"is_on": True, "color_hex": "#FFFFFF", "lightness": 50},
                music={"is_playing": True, "name": "Default", "type": "Relaxing"},
                curtain={"state": 0},
                Scores={"At": 50, "Ex": 50, "Re": 50, "St": 50},
                timestamp=datetime.now().isoformat()
            )

    def generate_advanced_params(self, state_result: StateAnalysisResult) -> AdvancedParams:
        """生成高级参数"""
        try:
            # 尝试获取LLM分析结果
            llm_result = None
            try:
                llm_result = self.llm_analyzer.analyze_mental_state(window_minutes=30)
            except Exception as e:
                logger.warning(f"LLM分析失败: {e}")
            
            # 生成状态摘要
            if llm_result:
                summary = llm_result.mental_state_assessment
                if len(llm_result.key_insights) > 0:
                    summary += f" 关键洞察: {llm_result.key_insights[0]}"
            else:
                # 生成基于传统分析的摘要
                confidence_desc = "高" if state_result.confidence > 0.7 else "中" if state_result.confidence > 0.4 else "低"
                summary = f"用户当前处于{state_result.state.value}状态，置信度{confidence_desc}({state_result.confidence:.2f})。"
                
                if state_result.state == MentalState.STRESSED:
                    summary += "建议播放放松音乐并调暗灯光以缓解压力。"
                elif state_result.state == MentalState.FOCUSED:
                    summary += "专注状态良好，建议保持当前环境设置。"
                elif state_result.state == MentalState.FATIGUED:
                    summary += "检测到疲劳，建议适当休息。"
                elif state_result.state == MentalState.RELAXED:
                    summary += "放松状态，适合继续当前活动。"
                else:
                    summary += "建议调整环境以优化状态。"
            
            # 生成当前动作描述
            action_mapping = {
                MentalState.STRESSED: "Relaxation Mode",
                MentalState.FOCUSED: "Focus Enhancement", 
                MentalState.FATIGUED: "Rest Suggestion",
                MentalState.RELAXED: "Maintain State",
                MentalState.DISTRACTED: "Attention Restoration",
                MentalState.NEUTRAL: "Environment Monitoring"
            }
            
            action = action_mapping.get(state_result.state, "Environment Adjustment")
            
            return AdvancedParams(
                State=state_result.state.name if hasattr(state_result.state, 'name') else str(state_result.state),
                Summary=summary,
                Action=action,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"生成高级参数失败: {e}")
            # 返回默认参数
            return AdvancedParams(
                State="Neutral",
                Summary="系统正在分析用户状态，请稍候...",
                Action="Monitoring",
                timestamp=datetime.now().isoformat()
            )

    def data_generation_loop(self):
        """数据生成循环（在单独线程中运行）"""
        while self.running:
            try:
                current_time = time.time()
                
                # 每秒生成新数据
                if current_time - self.last_analysis_time >= 1.0:
                    # 生成状态分析
                    state_result = self.state_analyzer.analyze_current_state()
                    
                    # 执行环境控制（每10秒一次）
                    if int(current_time) % 10 == 0:
                        try:
                            state_value = state_result.state.name if hasattr(state_result.state, 'name') else str(state_result.state)
                            env_control_result = self.environment_agent.analyze_and_control(
                                state_value,
                                state_result.confidence,
                                state_result.metrics
                            )
                            logger.info(f"环境控制执行: {len(env_control_result.get('actions_performed', []))}个动作")
                        except Exception as e:
                            logger.error(f"环境控制失败: {e}")
                    
                    # 生成参数
                    self.last_basic_params = self.generate_basic_params()
                    self.last_advanced_params = self.generate_advanced_params(state_result)
                    
                    self.last_analysis_time = current_time
                    
                    # 输出到终端
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 状态更新:")
                    print(f"  状态: {self.last_advanced_params.State} ({state_result.confidence:.2f})")
                    print(f"  分数: At={self.last_basic_params.Scores['At']} Ex={self.last_basic_params.Scores['Ex']} Re={self.last_basic_params.Scores['Re']} St={self.last_basic_params.Scores['St']}")
                    print(f"  动作: {self.last_advanced_params.Action}")
                
                time.sleep(0.1)  # 避免过高的CPU使用率
                
            except Exception as e:
                logger.error(f"数据生成循环错误: {e}")
                time.sleep(1)

    async def data_broadcast_loop(self):
        """数据广播循环（异步）"""
        while self.running:
            try:
                if self.last_basic_params and self.last_advanced_params and self.clients:
                    data = {
                        'basic': asdict(self.last_basic_params),
                        'advanced': asdict(self.last_advanced_params)
                    }
                    logger.info(f"广播数据到 {len(self.clients)} 个客户端: 分数={data['basic'].get('Scores', {})}, 状态={data['advanced'].get('State', 'Unknown')}")
                    await self.broadcast_data(data)
                elif not self.clients:
                    logger.debug("没有连接的客户端")
                elif not (self.last_basic_params and self.last_advanced_params):
                    logger.debug("数据参数未准备就绪") 
                
                await asyncio.sleep(1)  # 每秒广播一次
                
            except Exception as e:
                logger.error(f"数据广播循环错误: {e}")
                await asyncio.sleep(1)

    async def start_server(self):
        """启动WebSocket服务器"""
        try:
            self.running = True
            
            # 先启动WebSocket服务器
            server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=20,
                ping_timeout=10
            )
            
            logger.info(f"WebSocket服务器已启动 - ws://{self.host}:{self.port}")
            
            # 在后台线程启动BCI数据流服务（避免阻塞）
            def start_bci_service():
                try:
                    logger.info("后台线程启动BCI数据流服务...")
                    self.data_stream_service.start_service()
                    logger.info("BCI数据流服务启动完成")
                except Exception as e:
                    logger.error(f"BCI数据流服务启动失败: {e}")
            
            bci_thread = threading.Thread(target=start_bci_service, daemon=True)
            bci_thread.start()
            
            # 启动数据生成线程
            self.data_thread = threading.Thread(target=self.data_generation_loop, daemon=True)
            self.data_thread.start()
            
            # 启动数据广播循环
            broadcast_task = asyncio.create_task(self.data_broadcast_loop())
            
            # 等待服务器关闭
            await asyncio.gather(
                server.wait_closed(),
                broadcast_task
            )
            
        except Exception as e:
            logger.error(f"WebSocket服务器启动失败: {e}")
            raise

    def stop_server(self):
        """停止WebSocket服务器"""
        self.running = False
        logger.info("WebSocket服务器已停止")
        
        # 停止BCI数据流服务
        try:
            self.data_stream_service.stop_service()
        except Exception as e:
            logger.error(f"BCI数据流服务停止失败: {e}")
        
        # 清理环境智能体
        try:
            self.environment_agent.cleanup()
        except Exception as e:
            logger.error(f"环境智能体清理失败: {e}")

async def main():
    """主函数"""
    interface = WebSocketInterface()
    
    try:
        await interface.start_server()
    except KeyboardInterrupt:
        logger.info("收到停止信号")
    finally:
        interface.stop_server()

if __name__ == "__main__":
    asyncio.run(main())