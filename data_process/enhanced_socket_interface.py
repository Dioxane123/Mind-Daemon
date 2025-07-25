"""
增强Socket接口 - 支持basic_params和advanced_params双参数发送

功能：
- 每秒发送basic_params和advanced_params
- 终端打印参数信息
- 集成环境控制智能体
- 实时状态更新和同步
- 支持定时LLM摘要生成

作者：Mind Daemon Project
"""

import socket
import json
import time
import threading
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging

# 导入其他模块
from state_analyzer import StateAnalyzer, MentalState, StateAnalysisResult
from llm_analyzer import LLMAnalyzer, LLMAnalysisResult
from environment_agent import EnvironmentAgent

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

class EnhancedSocketInterface:
    """增强Socket接口"""
    
    def __init__(self, host: str = "localhost", port: int = 8888, 
                 protocol: str = "UDP", config: Dict[str, Any] = None):
        """
        初始化增强Socket接口
        
        Args:
            host: 目标主机地址
            port: 目标端口
            protocol: 协议类型 ("TCP" 或 "UDP")
            config: 系统配置
        """
        self.host = host
        self.port = port
        self.protocol = protocol.upper()
        self.config = config or {}
        
        # Socket连接
        self.connected = False
        self.socket = None
        
        # 核心模块
        self.state_analyzer = StateAnalyzer()
        self.llm_analyzer = LLMAnalyzer()
        self.environment_agent = EnvironmentAgent(config)
        
        # 状态数据
        self.current_state = MentalState.NEUTRAL
        self.current_confidence = 0.5
        self.current_metrics = {}
        self.current_summary = "系统启动中..."
        self.current_action = "None"
        
        # 运行控制
        self.running = False
        self.main_thread = None
        
        # 时间控制
        self.last_llm_analysis_time = datetime.now() - timedelta(minutes=5)
        self.llm_analysis_interval = timedelta(minutes=3)  # LLM分析间隔
        
        # 线程锁
        self.data_lock = threading.Lock()
        
        logger.info(f"增强Socket接口初始化完成: {protocol}://{host}:{port}")

    def connect(self) -> bool:
        """建立Socket连接"""
        try:
            if self.protocol == "TCP":
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((self.host, self.port))
            else:  # UDP
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            self.connected = True
            logger.info(f"Socket连接成功: {self.protocol}://{self.host}:{self.port}")
            return True
            
        except Exception as e:
            logger.error(f"Socket连接失败: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """断开Socket连接"""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            logger.info("Socket连接已断开")
        except Exception as e:
            logger.error(f"断开连接失败: {e}")

    def analyze_current_state(self) -> bool:
        """分析当前精神状态"""
        try:
            # 执行状态分析
            state_result = self.state_analyzer.analyze_current_state()
            
            with self.data_lock:
                self.current_state = state_result.state
                self.current_confidence = state_result.confidence
                self.current_metrics = state_result.metrics
            
            # 执行环境控制
            control_result = self.environment_agent.analyze_and_control(
                state_result.state.name,
                state_result.confidence,
                state_result.metrics
            )
            
            # 更新Action
            if control_result.get('actions_performed'):
                actions_text = "; ".join(control_result['actions_performed'])
                with self.data_lock:
                    self.current_action = actions_text[:100]  # 限制长度
            else:
                with self.data_lock:
                    self.current_action = "维持当前状态"
            
            return True
            
        except Exception as e:
            logger.error(f"状态分析失败: {e}")
            with self.data_lock:
                self.current_action = f"分析失败: {str(e)[:50]}"
            return False

    def update_llm_summary(self) -> bool:
        """更新LLM摘要"""
        try:
            current_time = datetime.now()
            
            # 检查是否需要更新摘要
            if current_time - self.last_llm_analysis_time < self.llm_analysis_interval:
                return True
            
            logger.info("开始LLM深度分析...")
            
            # 执行LLM分析
            llm_result = self.llm_analyzer.analyze_mental_state(window_minutes=30)
            
            # 构建摘要文本
            summary_parts = []
            summary_parts.append(f"状态: {llm_result.mental_state_assessment}")
            
            if llm_result.key_insights:
                key_insight = llm_result.key_insights[0]  # 取第一个洞察
                summary_parts.append(f"洞察: {key_insight}")
            
            if llm_result.recommendations:
                recommendation = llm_result.recommendations[0]  # 取第一个建议
                summary_parts.append(f"建议: {recommendation}")
            
            summary_text = " | ".join(summary_parts)
            
            with self.data_lock:
                self.current_summary = summary_text[:200]  # 限制长度
                self.last_llm_analysis_time = current_time
            
            logger.info("LLM分析完成")
            return True
            
        except Exception as e:
            logger.error(f"LLM分析失败: {e}")
            with self.data_lock:
                self.current_summary = f"LLM分析失败: {str(e)[:100]}"
            return False

    def build_current_params(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        """构建当前参数"""
        timestamp = datetime.now().isoformat()
        
        # 获取环境状态
        env_state = self.environment_agent.get_current_environment_state()
        
        with self.data_lock:
            # 构建basic_params
            basic_params = {
                "light": env_state['light'],
                "music": env_state['music'], 
                "curtain": env_state['curtain'],
                "Scores": {
                    "At": int(self.current_metrics.get('attention', 0.5) * 100),
                    "Ex": int(self.current_metrics.get('excitement', 0.5) * 100),
                    "Re": int(self.current_metrics.get('relaxation', 0.5) * 100),
                    "St": int(self.current_metrics.get('stress', 0.5) * 100)
                }
            }
            
            # 构建advanced_params
            advanced_params = {
                "State": self.current_state.name,
                "Summary": self.current_summary,
                "Action": self.current_action
            }
        
        return basic_params, advanced_params

    def send_data(self) -> bool:
        """发送一次数据"""
        try:
            if not self.connected:
                return False
            
            basic_params, advanced_params = self.build_current_params()
            
            # 构建发送数据包
            data_packet = {
                "basic_params": basic_params,
                "advanced_params": advanced_params
            }
            
            json_data = json.dumps(data_packet, ensure_ascii=False, indent=2)
            
            if self.protocol == "TCP":
                self.socket.sendall(json_data.encode('utf-8'))
            else:  # UDP
                self.socket.sendto(json_data.encode('utf-8'), (self.host, self.port))
            
            return True
            
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            return False

    def print_current_status(self):
        """在终端打印当前状态"""
        basic_params, advanced_params = self.build_current_params()
        
        current_time = datetime.now().strftime("%H:%M:%S")
        
        print(f"\n{'='*80}")
        print(f"🧠 Mind Daemon 实时状态 [{current_time}]")
        print(f"{'='*80}")
        
        # Basic Parameters
        print("📊 Basic Parameters:")
        light = basic_params["light"]
        music = basic_params["music"]
        curtain = basic_params["curtain"]
        scores = basic_params["Scores"]
        
        # 灯光状态
        light_status = "🟢 ON" if light["is_on"] else "🔴 OFF"
        light_info = f"{light['color_hex']}, {light['lightness']}%" if light["is_on"] else "N/A"
        print(f"  💡 Light: {light_status} ({light_info})")
        
        # 音乐状态
        music_status = "🎵 Playing" if music["is_playing"] else "⏸️ Stopped"
        music_info = f"{music.get('name', 'N/A')} [{music.get('type', 'N/A')}]" if music["is_playing"] else "N/A"
        print(f"  🎼 Music: {music_status} ({music_info})")
        
        # 窗帘状态
        curtain_status = "🪟 Open" if curtain["state"] == 0 else "🚪 Closed"
        print(f"  🏠 Curtain: {curtain_status}")
        
        # 分数
        print(f"  📈 Scores: At:{scores['At']} Ex:{scores['Ex']} Re:{scores['Re']} St:{scores['St']}")
        
        # Advanced Parameters
        print(f"\n🤖 Advanced Parameters:")
        print(f"  🧠 State: {advanced_params['State']}")
        print(f"  📝 Summary: {advanced_params['Summary'][:60]}...")
        print(f"  🎯 Action: {advanced_params['Action'][:50]}...")
        
        # 连接状态
        connection_status = "🟢 Connected" if self.connected else "🔴 Disconnected"
        print(f"  🌐 Socket: {connection_status} ({self.protocol}://{self.host}:{self.port})")

    def main_loop(self):
        """主循环"""
        analysis_counter = 0
        last_summary_update = datetime.now() - timedelta(minutes=10)
        
        while self.running:
            try:
                loop_start = time.time()
                
                # 每次都执行状态分析
                self.analyze_current_state()
                
                # 定期更新LLM摘要（每30秒检查一次）
                analysis_counter += 1
                if analysis_counter % 30 == 0:  # 每30秒检查一次
                    current_time = datetime.now()
                    if current_time - last_summary_update >= self.llm_analysis_interval:
                        if self.update_llm_summary():
                            last_summary_update = current_time
                
                # 发送数据
                if self.connected:
                    self.send_data()
                
                # 打印状态
                self.print_current_status()
                
                # 等待1秒（减去处理时间）
                elapsed = time.time() - loop_start
                sleep_time = max(0.1, 1.0 - elapsed)
                time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"主循环异常: {e}")
                time.sleep(1)

    def start(self):
        """启动系统"""
        if self.running:
            logger.warning("系统已在运行")
            return
        
        # 尝试连接Socket
        if not self.connected:
            self.connect()
        
        self.running = True
        
        # 启动主线程
        self.main_thread = threading.Thread(target=self.main_loop, daemon=True)
        self.main_thread.start()
        
        logger.info("增强Socket接口已启动")

    def stop(self):
        """停止系统"""
        self.running = False
        
        if self.main_thread and self.main_thread.is_alive():
            self.main_thread.join(timeout=3)
        
        # 清理资源
        self.environment_agent.cleanup()
        self.disconnect()
        
        logger.info("增强Socket接口已停止")

def main():
    """主函数"""
    try:
        print("🚀 Mind Daemon 增强Socket接口")
        print("=" * 50)
        
        # 配置
        config = {
            'music_dir': '/Users/m3airmima0000/Mind-Daemon/music',
            'window_py_path': '/Users/m3airmima0000/Desktop/window.py'
        }
        
        # 创建接口（使用UDP避免连接问题）
        interface = EnhancedSocketInterface(
            host="localhost",
            port=8888,
            protocol="UDP",
            config=config
        )
        
        print("注意：如果没有实际的Socket服务器，数据发送会失败但系统仍会正常运行")
        print("按 Ctrl+C 停止系统\n")
        
        # 启动系统
        interface.start()
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\n用户中断，正在停止系统...")
            interface.stop()
            print("系统已停止")
        
    except Exception as e:
        logger.error(f"系统运行失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())