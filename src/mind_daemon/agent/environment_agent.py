"""
环境控制智能体 - 基于用户精神状态的智能环境控制系统

功能：
- 基于精神状态分析结果控制环境设备
- 使用LLM进行智能决策
- 控制灯光、音乐、窗帘、屏幕光晕
- 平滑过渡和渐变效果
- 音乐自动选择和播放

作者：Mind Daemon Project
"""

import os
import sys
import json
import random
import threading
import time
import subprocess
import requests
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import logging

# 尝试导入psutil，如果不可用则使用fallback机制
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False
    logging.warning("psutil未安装，将使用简化的进程管理功能")

# 添加路径以导入其他模块
sys.path.append(os.path.dirname(__file__))

# 配置日志
logger = logging.getLogger(__name__)

class EnvironmentDevice(Enum):
    """环境设备枚举"""
    LIGHT = "light"
    MUSIC = "music"
    CURTAIN = "curtain"
    HALO = "halo"

@dataclass
class LightState:
    """灯光状态"""
    is_on: bool = False
    color_hex: str = "#FFFFFF"
    lightness: int = 50  # 0-100
    transition_duration: float = 2.0  # 过渡时间（秒）

@dataclass
class MusicState:
    """音乐状态"""
    is_playing: bool = False
    name: str = ""
    music_type: str = ""  # "focus" or "relax"
    volume: float = 0.5  # 0.0-1.0
    fade_duration: float = 3.0  # 淡入淡出时间（秒）

@dataclass
class CurtainState:
    """窗帘状态"""
    state: int = 0  # 0: open, 1: closed
    transition_duration: float = 5.0

@dataclass
class HaloState:
    """光晕状态"""
    is_active: bool = False
    color_rgb: Tuple[int, int, int] = (255, 255, 255)
    intensity: float = 0.8  # 0.0-1.0
    transition_duration: float = 1.5

class MusicPlayer:
    """音乐播放器类 - 支持持续播放和平滑切换（修复多重播放问题）"""
    
    def __init__(self, music_dir: str):
        """
        初始化音乐播放器
        
        Args:
            music_dir: 音乐文件目录
        """
        self.music_dir = music_dir
        self.focus_dir = os.path.join(music_dir, "focus")
        self.relax_dir = os.path.join(music_dir, "relax")
        
        # 当前播放状态
        self.current_process = None
        self.current_pid = None  # 跟踪当前播放器进程ID
        self.current_file = None
        self.current_type = "relax"  # 默认播放放松音乐
        self.is_playing = False
        self.target_type = "relax"  # 目标音乐类型
        
        # 播放器进程名称（用于全局清理）
        self.player_processes = {
            'darwin': ['afplay'],
            'win32': ['powershell'],
            'linux': ['mpg123', 'alsamixer', 'pulseaudio']
        }
        
        # 线程锁防止并发播放
        self.playback_lock = threading.Lock()
        
        # 音乐文件列表
        self.focus_tracks = self._get_music_files(self.focus_dir)
        self.relax_tracks = self._get_music_files(self.relax_dir)
        
        # 播放历史（避免重复）
        self.recent_tracks: List[str] = []
        self.max_recent = 3
        
        # 切换控制
        self.last_switch_time = 0
        self.switch_cooldown = 60  # 60秒切换冷却时间
        self.fade_duration = 3.0  # 淡入淡出时间
        
        # 监控线程
        self.monitor_thread = None
        self.should_monitor = False
        
        logger.info(f"音乐播放器初始化完成")
        logger.info(f"专注音乐: {len(self.focus_tracks)}首")
        logger.info(f"放松音乐: {len(self.relax_tracks)}首")
        
        # 在启动前先清理所有音乐播放器进程
        self._force_kill_all_music_players()
        
        # 自动开始播放
        self.start_continuous_play()

    def _get_music_files(self, directory: str) -> List[str]:
        """获取目录下的音乐文件"""
        try:
            if not os.path.exists(directory):
                logger.warning(f"音乐目录不存在: {directory}")
                return []
            
            music_files = []
            for file in os.listdir(directory):
                if file.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
                    music_files.append(os.path.join(directory, file))
            
            return music_files
        except Exception as e:
            logger.error(f"获取音乐文件失败: {e}")
            return []

    def select_track(self, music_type: str) -> Optional[str]:
        """
        选择音乐文件
        
        Args:
            music_type: 音乐类型 ("focus" 或 "relax")
            
        Returns:
            选中的音乐文件路径
        """
        try:
            if music_type == "focus":
                available_tracks = self.focus_tracks.copy()
            elif music_type == "relax":
                available_tracks = self.relax_tracks.copy()
            else:
                logger.warning(f"未知音乐类型: {music_type}")
                return None
            
            if not available_tracks:
                logger.warning(f"没有可用的{music_type}音乐")
                return None
            
            # 排除最近播放的音乐
            for recent in self.recent_tracks:
                if recent in available_tracks:
                    available_tracks.remove(recent)
            
            # 如果过滤后没有音乐了，清空历史记录重新选择
            if not available_tracks:
                self.recent_tracks.clear()
                available_tracks = self.focus_tracks if music_type == "focus" else self.relax_tracks
            
            # 随机选择
            selected = random.choice(available_tracks)
            
            # 更新播放历史
            self.recent_tracks.append(selected)
            if len(self.recent_tracks) > self.max_recent:
                self.recent_tracks.pop(0)
            
            return selected
            
        except Exception as e:
            logger.error(f"选择音乐失败: {e}")
            return None

    def start_continuous_play(self):
        """开始持续播放音乐"""
        try:
            self.should_monitor = True
            self.monitor_thread = threading.Thread(target=self._monitor_playback, daemon=True)
            self.monitor_thread.start()
            
            # 立即开始播放第一首音乐
            self._play_next_track()
            
            logger.info("持续播放模式已启动")
            
        except Exception as e:
            logger.error(f"启动持续播放失败: {e}")

    def _monitor_playback(self):
        """监控播放状态的后台线程"""
        while self.should_monitor:
            try:
                # 检查当前播放状态
                if not self.is_track_playing():
                    # 如果音乐停止了，播放下一首
                    self._play_next_track()
                
                time.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                logger.error(f"播放监控异常: {e}")
                time.sleep(5)

    def _play_next_track(self) -> bool:
        """播放下一首音乐（防止多重播放）"""
        with self.playback_lock:
            try:
                # 选择音乐文件
                track_path = self.select_track(self.current_type)
                if not track_path:
                    logger.warning(f"没有可用的{self.current_type}音乐")
                    return False
                
                # 强制清理所有音乐播放器进程（防止多重播放）
                self._force_kill_all_music_players()
                
                # 短暂延迟确保进程完全清理
                time.sleep(0.5)
                
                # 使用系统默认播放器播放（跨平台）
                if sys.platform == "darwin":  # macOS
                    cmd = ["afplay", track_path]
                elif sys.platform == "win32":  # Windows
                    cmd = ["powershell", "-c", f"(New-Object Media.SoundPlayer '{track_path}').PlaySync()"]
                else:  # Linux
                    cmd = ["mpg123", "-q", track_path]
                
                # 启动播放进程
                self.current_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL
                )
                
                # 跟踪进程ID
                self.current_pid = self.current_process.pid
                
                # 更新状态
                self.current_file = track_path
                self.is_playing = True
                
                track_name = os.path.basename(track_path)
                logger.info(f"开始播放: {track_name} ({self.current_type}) [PID: {self.current_pid}]")
                
                return True
                
            except Exception as e:
                logger.error(f"播放音乐失败: {e}")
                return False

    def switch_music_type(self, new_type: str) -> bool:
        """
        切换音乐类型（平滑切换）
        
        Args:
            new_type: 新的音乐类型 ("focus" 或 "relax")
            
        Returns:
            是否成功切换
        """
        try:
            current_time = time.time()
            
            # 检查切换冷却时间
            if (current_time - self.last_switch_time) < self.switch_cooldown:
                logger.info(f"音乐切换冷却中，剩余{self.switch_cooldown - (current_time - self.last_switch_time):.0f}秒")
                return False
            
            # 如果已经是目标类型，不需要切换
            if self.current_type == new_type:
                return True
            
            # 更新目标类型
            self.target_type = new_type
            self.current_type = new_type
            self.last_switch_time = current_time
            
            # 立即切换到新类型的音乐
            self._play_next_track()
            
            logger.info(f"音乐类型已切换到: {new_type}")
            return True
            
        except Exception as e:
            logger.error(f"切换音乐类型失败: {e}")
            return False

    def _stop_current_track(self):
        """停止当前播放的音乐"""
        try:
            if self.current_process:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.current_process.kill()
                    self.current_process.wait()
                self.current_process = None
                self.current_pid = None
        except Exception as e:
            logger.error(f"停止音乐播放失败: {e}")
    
    def _force_kill_all_music_players(self):
        """强制杀死所有音乐播放器进程（防止多重播放）"""
        try:
            platform = sys.platform
            player_names = self.player_processes.get(platform, [])
            
            killed_count = 0
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    cmdline = ' '.join(proc_info['cmdline'] or []).lower()
                    
                    # 检查是否是音乐播放器进程
                    is_music_player = False
                    
                    # 检查进程名
                    for player_name in player_names:
                        if player_name.lower() in proc_name:
                            is_music_player = True
                            break
                    
                    # 检查命令行参数中是否包含音乐文件
                    if not is_music_player:
                        for ext in ['.mp3', '.wav', '.m4a', '.flac']:
                            if ext in cmdline:
                                is_music_player = True
                                break
                    
                    # 检查是否在我们的音乐目录
                    if not is_music_player and self.music_dir.lower() in cmdline:
                        is_music_player = True
                    
                    if is_music_player:
                        logger.info(f"终止音乐播放器进程: {proc_name} [PID: {proc_info['pid']}]")
                        proc.terminate()
                        try:
                            proc.wait(timeout=2)
                        except psutil.TimeoutExpired:
                            proc.kill()
                        killed_count += 1
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    # 进程已不存在或无权限访问
                    continue
                except Exception as e:
                    logger.error(f"处理进程时出错: {e}")
                    continue
            
            if killed_count > 0:
                logger.info(f"已清理 {killed_count} 个音乐播放器进程")
                
        except Exception as e:
            logger.error(f"强制清理音乐播放器进程失败: {e}")
    
    def _has_other_music_players(self) -> bool:
        """检查系统中是否有其他音乐播放器进程"""
        try:
            platform = sys.platform
            player_names = self.player_processes.get(platform, [])
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    proc_info = proc.info
                    proc_name = proc_info['name'].lower()
                    cmdline = ' '.join(proc_info['cmdline'] or []).lower()
                    
                    # 跳过当前进程
                    if self.current_pid and proc_info['pid'] == self.current_pid:
                        continue
                    
                    # 检查是否是音乐播放器进程
                    for player_name in player_names:
                        if player_name.lower() in proc_name:
                            # 进一步检查是否在播放我们的音乐
                            if self.music_dir.lower() in cmdline:
                                return True
                    
                    # 检查命令行参数中是否包含我们目录的音乐文件
                    if self.music_dir.lower() in cmdline:
                        for ext in ['.mp3', '.wav', '.m4a', '.flac']:
                            if ext in cmdline:
                                return True
                                
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                except Exception as e:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"检查其他音乐播放器进程失败: {e}")
            return False

    def stop_continuous_play(self):
        """停止持续播放模式"""
        try:
            # 停止监控线程
            self.should_monitor = False
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=3)
            
            # 强制清理所有音乐播放器进程
            self._force_kill_all_music_players()
            
            # 重置状态
            self.current_process = None
            self.current_pid = None
            self.current_file = None
            self.is_playing = False
            
            logger.info("持续播放模式已停止，所有音乐播放器进程已清理")
            
        except Exception as e:
            logger.error(f"停止持续播放失败: {e}")

    def get_current_track_name(self) -> str:
        """获取当前播放音乐的名称"""
        if self.current_file:
            return os.path.splitext(os.path.basename(self.current_file))[0]
        return ""

    def is_track_playing(self) -> bool:
        """检查是否正在播放（改进的进程检测）"""
        # 检查当前进程
        if self.current_process and self.current_pid:
            try:
                # 检查进程是否还在运行
                if self.current_process.poll() is None:
                    # 双重检查：使用psutil验证进程存在（如果可用）
                    if HAS_PSUTIL and psutil.pid_exists(self.current_pid):
                        return True
                    elif not HAS_PSUTIL:
                        # 没有psutil时直接返回True（进程poll()为None表示还在运行）
                        return True
                
                # 进程已结束，更新状态
                self.is_playing = False
                self.current_process = None
                self.current_pid = None
                
            except Exception as e:
                logger.error(f"检查播放状态失败: {e}")
                self.is_playing = False
                self.current_process = None
                self.current_pid = None
        
        # 额外检查：确保系统中没有其他音乐播放器进程
        if self._has_other_music_players():
            logger.warning("检测到其他音乐播放器进程，可能存在多重播放")
            return True
            
        return False

    def get_current_music_type(self) -> str:
        """获取当前音乐类型"""
        return self.current_type

class HaloController:
    """光晕控制器"""
    
    def __init__(self, window_py_path: str):
        """
        初始化光晕控制器
        
        Args:
            window_py_path: window.py文件路径
        """
        self.window_py_path = window_py_path
        self.current_process = None
        self.is_active = False
        self.current_color = (255, 255, 255)
        
        # 光晕控制冷却时间
        self.last_activation_time = 0
        self.activation_cooldown = 30  # 30秒冷却时间
        self.last_color_change_time = 0
        self.color_change_cooldown = 15  # 15秒颜色变化冷却时间
        
        logger.info(f"光晕控制器初始化完成")

    def activate(self, color_rgb: Tuple[int, int, int] = (255, 255, 255)) -> bool:
        """
        激活光晕效果（支持颜色传递）
        
        Args:
            color_rgb: RGB颜色值
            
        Returns:
            是否成功激活
        """
        try:
            current_time = time.time()
            
            # 检查激活冷却时间
            if self.is_active and (current_time - self.last_activation_time) < self.activation_cooldown:
                # 如果在冷却时间内，只检查颜色变化
                if (color_rgb != self.current_color and 
                    (current_time - self.last_color_change_time) >= self.color_change_cooldown):
                    self.set_color(color_rgb)
                    self.last_color_change_time = current_time
                return True
            
            # 如果已经激活相同颜色，不重复激活
            if self.is_active and color_rgb == self.current_color:
                return True
            
            # 如果已经激活，先停止
            if self.is_active:
                self.deactivate()
            
            # 启动光晕窗口，传递颜色参数
            if os.path.exists(self.window_py_path):
                # 将RGB元组转换为字符串格式
                color_str = f"{color_rgb[0]},{color_rgb[1]},{color_rgb[2]}"
                
                self.current_process = subprocess.Popen([
                    sys.executable, self.window_py_path,
                    "--color", color_str,
                    "--disable-auto"  # 禁用自动空闲检测，仅响应环境控制
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                
                self.is_active = True
                self.current_color = color_rgb
                self.last_activation_time = current_time
                
                logger.info(f"光晕效果已激活，颜色: RGB{color_rgb}")
                return True
            else:
                logger.error(f"光晕程序不存在: {self.window_py_path}")
                return False
                
        except Exception as e:
            logger.error(f"激活光晕失败: {e}")
            return False

    def deactivate(self):
        """停用光晕效果"""
        try:
            if self.current_process:
                self.current_process.terminate()
                try:
                    self.current_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    # 强制杀死进程
                    self.current_process.kill()
                    self.current_process.wait()
                self.current_process = None
            
            self.is_active = False
            logger.info("光晕效果已停用")
            
        except Exception as e:
            logger.error(f"停用光晕失败: {e}")

    def force_kill(self):
        """强制终止光晕进程"""
        try:
            if self.current_process:
                self.current_process.kill()
                self.current_process.wait()
                self.current_process = None
                self.is_active = False
                logger.info("光晕进程已强制终止")
        except Exception as e:
            logger.error(f"强制终止光晕进程失败: {e}")

    def set_color(self, color_rgb: Tuple[int, int, int]):
        """
        设置光晕颜色
        
        Args:
            color_rgb: RGB颜色值
        """
        # 目前的window.py不支持动态颜色变化
        # 这里需要重启光晕程序来改变颜色
        if self.is_active:
            self.deactivate()
            time.sleep(0.5)
            self.activate(color_rgb)

class EnvironmentAgent:
    """环境控制智能体"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化环境控制智能体
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        
        # 设备状态
        self.light_state = LightState()
        self.music_state = MusicState()
        self.curtain_state = CurtainState()
        self.halo_state = HaloState()
        
        # 导入配置系统
        from ..utils.config import config as global_config
        self.global_config = global_config
        
        # 音乐播放器配置
        music_dir = global_config.get('MUSIC_DIR')
        self.music_player = MusicPlayer(music_dir)
        
        # 光晕控制器配置
        window_py_path = global_config.get('WINDOW_PY_PATH')
        self.halo_controller = HaloController(window_py_path)
        
        # LLM API配置
        self.minimax_api_key = global_config.get('MINIMAX_API_KEY')
        self.minimax_base_url = global_config.get('MINIMAX_BASE_URL')
        
        # 状态变化历史
        self.state_history: List[str] = []
        self.max_history = 5
        
        logger.info("环境控制智能体初始化完成")

    def call_minimax_api(self, prompt: str) -> str:
        """调用MiniMax API进行决策"""
        try:
            # 检查API配置
            if not self.minimax_api_key or not self.minimax_base_url:
                logger.warning("MiniMax API未配置，使用模拟响应")
                return self._generate_mock_decision(prompt)
            
            
            # 构建API请求
            headers = {
                'Authorization': f'Bearer {self.minimax_api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.global_config.get('MINIMAX_MODEL', 'MiniMax-Text-01'),
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 500,
                'temperature': 0.3  # 较低的温度确保决策的一致性
            }
            
            # 发送API请求
            response = requests.post(
                self.minimax_base_url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                # 提取LLM的响应内容
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # 尝试从响应中提取JSON部分
                if '```json' in content:
                    start = content.find('```json') + 7
                    end = content.find('```', start)
                    json_content = content[start:end].strip()
                    logger.info("成功调用MiniMax API获取环境控制决策")
                    return json_content
                else:
                    # 如果没有找到JSON格式，尝试直接解析
                    import json
                    try:
                        json.loads(content)  # 验证是否为有效JSON
                        logger.info("成功调用MiniMax API获取环境控制决策")
                        return content
                    except json.JSONDecodeError:
                        logger.warning("LLM响应格式不正确，使用模拟响应")
                        return self._generate_mock_decision(prompt)
            else:
                logger.error(f"MiniMax API请求失败: HTTP {response.status_code}")
                return self._generate_mock_decision(prompt)
                
        except requests.exceptions.Timeout:
            logger.error("MiniMax API请求超时，使用模拟响应")
            return self._generate_mock_decision(prompt)
        except requests.exceptions.RequestException as e:
            logger.error(f"MiniMax API请求异常: {e}，使用模拟响应")
            return self._generate_mock_decision(prompt)
        except Exception as e:
            logger.error(f"调用MiniMax API失败: {e}")
            return self._generate_fallback_decision()

    def _generate_mock_decision(self, prompt: str) -> str:
        """生成模拟的智能决策（改进的光晕控制）"""
        if "STRESSED" in prompt or "PRESSURE" in prompt:
            return json.dumps({
                "light": {"action": "dim", "color": "#FFE4B5", "lightness": 30},
                "music": {"action": "switch", "type": "relax"},
                "curtain": {"action": "close"},
                "halo": {"action": "activate", "reason": "压力缓解，与灯光同步"}
            })
        elif "FOCUSED" in prompt:
            return json.dumps({
                "light": {"action": "brighten", "color": "#FFFFFF", "lightness": 80},
                "music": {"action": "switch", "type": "focus"},
                "curtain": {"action": "open"},
                "halo": {"action": "deactivate", "reason": "专注状态，停用光晕减少干扰"}
            })
        elif "FATIGUED" in prompt:
            return json.dumps({
                "light": {"action": "dim", "color": "#FFB6C1", "lightness": 20},
                "music": {"action": "switch", "type": "relax"},
                "curtain": {"action": "close"},
                "halo": {"action": "activate", "color": [255, 182, 193], "reason": "疲劳恢复，温暖色调"}
            })
        elif "RELAXED" in prompt:
            return json.dumps({
                "light": {"action": "soft", "color": "#E6E6FA", "lightness": 60},
                "music": {"action": "maintain", "type": "relax"},
                "curtain": {"action": "open"},
                "halo": {"action": "soft", "reason": "柔和光晕，与灯光协调"}
            })
        elif "DISTRACTED" in prompt:
            return json.dumps({
                "light": {"action": "brighten", "color": "#F0F8FF", "lightness": 75},
                "music": {"action": "switch", "type": "focus"},
                "curtain": {"action": "open"},
                "halo": {"action": "attention", "color": [255, 215, 0], "reason": "注意力提醒"}
            })
        elif "NEUTRAL" in prompt:
            return json.dumps({
                "light": {"action": "maintain"},
                "music": {"action": "maintain"},
                "curtain": {"action": "maintain"},
                "halo": {"action": "deactivate", "reason": "中性状态，停用光晕"}
            })
        else:
            return json.dumps({
                "light": {"action": "maintain"},
                "music": {"action": "maintain"},
                "curtain": {"action": "maintain"},
                "halo": {"action": "maintain"}
            })

    def _generate_fallback_decision(self) -> str:
        """生成备用决策"""
        return json.dumps({
            "light": {"action": "maintain"},
            "music": {"action": "maintain"},
            "curtain": {"action": "maintain"},
            "halo": {"action": "maintain"}
        })

    def analyze_and_control(self, current_state: str, confidence: float, 
                          metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        分析当前状态并执行环境控制
        
        Args:
            current_state: 当前精神状态
            confidence: 置信度
            metrics: 相关指标
            
        Returns:
            执行的控制动作
        """
        try:
            # 更新状态历史
            self.state_history.append(current_state)
            if len(self.state_history) > self.max_history:
                self.state_history.pop(0)
            
            # 构建决策prompt
            prompt = self._build_decision_prompt(current_state, confidence, metrics)
            
            # 调用LLM获取决策
            decision_json = self.call_minimax_api(prompt)
            decision = json.loads(decision_json)
            
            # 执行控制动作
            actions_performed = self._execute_decisions(decision)
            
            logger.info(f"环境控制决策完成，状态: {current_state}")
            
            return {
                'state': current_state,
                'confidence': confidence,
                'decisions': decision,
                'actions_performed': actions_performed,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"环境控制分析失败: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

    def _build_decision_prompt(self, state: str, confidence: float, 
                             metrics: Dict[str, float]) -> str:
        """构建决策prompt"""
        
        # 状态历史摘要
        history_text = " -> ".join(self.state_history[-3:]) if self.state_history else "无历史"
        
        prompt = f"""你是一个专业的智能环境控制系统，负责根据用户的精神状态调节环境设备。

当前状态分析：
- 精神状态: {state}
- 置信度: {confidence:.2f}
- 状态变化历史: {history_text}

性能指标：
"""
        
        for key, value in metrics.items():
            prompt += f"- {key}: {value:.3f}\n"
        
        prompt += f"""
请基于以上信息，为以下设备制定控制策略。注意：音乐系统是持续播放的，您只需要决定是否切换音乐类型；光晕效果有冷却时间，请谨慎使用。

1. 灯光控制：
   - action: "brighten"(调亮), "dim"(调暗), "soft"(柔和), "maintain"(保持)
   - color: 十六进制颜色代码，选择有助于当前状态的颜色
   - lightness: 0-100的亮度值

2. 音乐控制（持续播放模式）：
   - action: "switch"(切换), "maintain"(保持当前类型)
   - type: "focus"(专注音乐) 或 "relax"(放松音乐)
   - 注意：音乐会自动持续播放，您只需要决定音乐类型

3. 窗帘控制：
   - action: "open"(打开), "close"(关闭), "maintain"(保持)

4. 光晕控制（智能颜色选择与开关控制）：
   - action: "activate"(激活), "soft"(柔和显示), "attention"(注意力提醒), "minimal"(最小化), "deactivate"(停用), "maintain"(保持)
   - color: [R, G, B] RGB颜色数组，如果不指定将自动同步灯光颜色
   - reason: 简短说明使用此颜色的原因

颜色心理学指导：
- 红色系(255,0,0)：警告、紧急、激活
- 蓝色系(0,100,255)：冷静、专注、理性
- 绿色系(0,255,100)：平衡、舒适、恢复
- 紫色系(200,100,255)：创造、放松、神秘
- 黄色系(255,215,0)：注意、警觉、提醒
- 粉色系(255,182,193)：温暖、安慰、柔和
- 橙色系(255,165,0)：活力、温暖、友好

控制原则：
- 压力/焦虑状态：温暖色调灯光，切换放松音乐，关闭窗帘，激活舒缓色光晕（与灯光同色或温暖色）
- 专注状态：明亮白光，切换专注音乐，打开窗帘，停用光晕或使用最小化蓝色光晕
- 疲劳状态：柔和粉色灯光，保持或切换到放松音乐，关闭窗帘，激活温暖色光晕帮助恢复
- 放松状态：柔和紫色灯光，保持放松音乐，适当开窗，使用柔和光晕或停用光晕
- 分心状态：清爽灯光，切换专注音乐，打开窗帘，激活黄色注意力提醒光晕
- 中性/正常状态：停用光晕，避免过度刺激

光晕使用指导：
- 当用户需要情绪调节或注意力提醒时使用光晕
- 当用户处于专注工作状态时，考虑停用光晕减少干扰
- 光晕颜色应与灯光颜色协调，营造和谐的环境氛围
- 避免在不必要时激活光晕，防止视觉疲劳

请返回JSON格式的控制指令：
```json
{{
    "light": {{"action": "...", "color": "...", "lightness": ...}},
    "music": {{"action": "...", "type": "..."}},
    "curtain": {{"action": "..."}},
    "halo": {{"action": "...", "color": [R, G, B], "reason": "..."}}
}}
```"""

        return prompt

    def _execute_decisions(self, decisions: Dict[str, Any]) -> List[str]:
        """执行控制决策"""
        actions_performed = []
        
        try:
            # 灯光控制
            if 'light' in decisions:
                light_action = self._execute_light_control(decisions['light'])
                if light_action:
                    actions_performed.append(light_action)
            
            # 音乐控制
            if 'music' in decisions:
                music_action = self._execute_music_control(decisions['music'])
                if music_action:
                    actions_performed.append(music_action)
            
            # 窗帘控制
            if 'curtain' in decisions:
                curtain_action = self._execute_curtain_control(decisions['curtain'])
                if curtain_action:
                    actions_performed.append(curtain_action)
            
            # 光晕控制
            if 'halo' in decisions:
                halo_action = self._execute_halo_control(decisions['halo'])
                if halo_action:
                    actions_performed.append(halo_action)
            
        except Exception as e:
            logger.error(f"执行控制决策失败: {e}")
            actions_performed.append(f"执行失败: {str(e)}")
        
        return actions_performed

    def _execute_light_control(self, light_decision: Dict[str, Any]) -> Optional[str]:
        """执行灯光控制"""
        try:
            action = light_decision.get('action', 'maintain')
            
            if action == 'maintain':
                return None
            
            # 更新灯光状态
            if action in ['brighten', 'dim', 'soft']:
                self.light_state.is_on = True
                
                if 'color' in light_decision:
                    self.light_state.color_hex = light_decision['color']
                
                if 'lightness' in light_decision:
                    self.light_state.lightness = max(0, min(100, light_decision['lightness']))
                
                return f"灯光调节: {action}, 颜色: {self.light_state.color_hex}, 亮度: {self.light_state.lightness}%"
            
        except Exception as e:
            logger.error(f"灯光控制失败: {e}")
            return f"灯光控制失败: {str(e)}"

    def _execute_music_control(self, music_decision: Dict[str, Any]) -> Optional[str]:
        """执行音乐控制"""
        try:
            action = music_decision.get('action', 'maintain')
            
            if action == 'maintain':
                return None
            elif action == 'switch':
                music_type = music_decision.get('type', 'relax')
                current_type = self.music_player.get_current_music_type()
                
                if current_type == music_type:
                    return f"音乐已经是{music_type}类型，无需切换"
                
                if self.music_player.switch_music_type(music_type):
                    self.music_state.is_playing = True
                    self.music_state.name = self.music_player.get_current_track_name()
                    self.music_state.music_type = music_type
                    return f"音乐已切换到{music_type}类型: {self.music_state.name}"
                else:
                    return f"音乐类型切换失败（可能在冷却期）"
            
        except Exception as e:
            logger.error(f"音乐控制失败: {e}")
            return f"音乐控制失败: {str(e)}"

    def _execute_curtain_control(self, curtain_decision: Dict[str, Any]) -> Optional[str]:
        """执行窗帘控制"""
        try:
            action = curtain_decision.get('action', 'maintain')
            
            if action == 'maintain':
                return None
            elif action == 'open':
                self.curtain_state.state = 0
                return "窗帘已打开"
            elif action == 'close':
                self.curtain_state.state = 1
                return "窗帘已关闭"
            
        except Exception as e:
            logger.error(f"窗帘控制失败: {e}")
            return f"窗帘控制失败: {str(e)}"

    def _execute_halo_control(self, halo_decision: Dict[str, Any]) -> Optional[str]:
        """执行光晕控制（与灯光颜色同步）"""
        try:
            action = halo_decision.get('action', 'maintain')
            
            if action == 'maintain':
                return None
            elif action == 'deactivate' or action == 'off':
                # 明确停用光晕
                if self.halo_state.is_active:
                    self.halo_controller.deactivate()
                    self.halo_state.is_active = False
                    return "光晕已停用"
                return None
            elif action in ['activate', 'soft', 'attention', 'minimal']:
                color = halo_decision.get('color', [255, 255, 255])
                reason = halo_decision.get('reason', '环境调节')
                
                # 如果没有明确指定光晕颜色，使用灯光颜色
                if color == [255, 255, 255] and hasattr(self, 'light_state'):
                    try:
                        # 从灯光的十六进制颜色转换为RGB
                        hex_color = self.light_state.color_hex
                        if hex_color.startswith('#') and len(hex_color) == 7:
                            r = int(hex_color[1:3], 16)
                            g = int(hex_color[3:5], 16)
                            b = int(hex_color[5:7], 16)
                            color = [r, g, b]
                            reason += f" (同步灯光颜色: {hex_color})"
                    except Exception as e:
                        logger.warning(f"无法同步灯光颜色: {e}")
                
                if isinstance(color, list) and len(color) == 3:
                    color_rgb = (int(color[0]), int(color[1]), int(color[2]))
                    if self.halo_controller.activate(color_rgb):
                        self.halo_state.is_active = True
                        self.halo_state.color_rgb = color_rgb
                        
                        action_desc = {
                            'activate': '激活',
                            'soft': '柔和显示',
                            'attention': '注意力提醒',
                            'minimal': '最小化显示'
                        }.get(action, '激活')
                        
                        return f"光晕{action_desc}: RGB{color_rgb} ({reason})"
                    else:
                        return f"光晕{action}失败（可能在冷却期）"
            
        except Exception as e:
            logger.error(f"光晕控制失败: {e}")
            return f"光晕控制失败: {str(e)}"

    def get_current_environment_state(self) -> Dict[str, Any]:
        """获取当前环境状态"""
        # 更新音乐播放状态
        if self.music_player.is_track_playing():
            # 如果音乐正在播放，更新状态和歌名
            self.music_state.is_playing = True
            current_track_name = self.music_player.get_current_track_name()
            if current_track_name and self.music_state.name != current_track_name:
                self.music_state.name = current_track_name
                logger.info(f"更新音乐歌名: {current_track_name}")
        elif self.music_state.is_playing and not self.music_player.is_track_playing():
            self.music_state.is_playing = False
            self.music_state.name = ""
            logger.info("音乐播放停止")
        
        return {
            'light': {
                'is_on': self.light_state.is_on,
                'color_hex': self.light_state.color_hex,
                'lightness': self.light_state.lightness
            },
            'music': {
                'is_playing': self.music_state.is_playing,
                'name': self.music_state.name,
                'type': self.music_state.music_type
            },
            'curtain': {
                'state': self.curtain_state.state
            },
            'halo': {
                'is_active': self.halo_state.is_active,
                'color_rgb': self.halo_state.color_rgb
            }
        }

    def cleanup(self):
        """清理资源"""
        try:
            # 停止持续播放模式
            self.music_player.stop_continuous_play()
            
            # 强制终止光晕进程
            self.halo_controller.force_kill()
            
            logger.info("环境控制智能体资源清理完成")
        except Exception as e:
            logger.error(f"资源清理失败: {e}")

def main():
    """测试函数"""
    try:
        print("🌟 环境控制智能体测试")
        
        # 创建智能体
        config = {
            'music_dir': '/Users/m3airmima0000/Mind-Daemon/music',
            'window_py_path': '/Users/m3airmima0000/Desktop/window.py'
        }
        
        agent = EnvironmentAgent(config)
        
        # 模拟不同状态的环境控制
        test_states = [
            ("STRESSED", 0.8, {"stress": 0.8, "attention": 0.3}),
            ("FOCUSED", 0.9, {"attention": 0.9, "engagement": 0.8}),
            ("FATIGUED", 0.7, {"fatigue_index": 2.5, "attention": 0.2}),
            ("RELAXED", 0.8, {"relaxation": 0.8, "stress": 0.2})
        ]
        
        for state, confidence, metrics in test_states:
            print(f"\n{'='*50}")
            print(f"测试状态: {state}")
            
            result = agent.analyze_and_control(state, confidence, metrics)
            
            print(f"置信度: {confidence}")
            print(f"执行动作:")
            for action in result.get('actions_performed', []):
                print(f"  • {action}")
            
            # 显示当前环境状态
            env_state = agent.get_current_environment_state()
            print(f"\n当前环境状态:")
            print(f"  灯光: {'开启' if env_state['light']['is_on'] else '关闭'} "
                  f"({env_state['light']['color_hex']}, {env_state['light']['lightness']}%)")
            print(f"  音乐: {'播放中' if env_state['music']['is_playing'] else '停止'} "
                  f"({env_state['music']['name']})")
            print(f"  窗帘: {'打开' if env_state['curtain']['state'] == 0 else '关闭'}")
            print(f"  光晕: {'激活' if env_state['halo']['is_active'] else '停用'}")
            
            time.sleep(2)  # 短暂等待
        
        print(f"\n✅ 测试完成")
        
        # 清理资源
        agent.cleanup()
        
    except KeyboardInterrupt:
        print("\n用户中断测试")
    except Exception as e:
        print(f"测试失败: {e}")

if __name__ == "__main__":
    main()