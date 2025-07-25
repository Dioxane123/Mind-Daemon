"""Configuration management for Mind Daemon using environment variables."""

import os
from typing import Optional, Union
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
project_root = Path(__file__).parent.parent.parent.parent
env_file = project_root / '.env'

if env_file.exists():
    load_dotenv(env_file)
    print(f"✅ 已加载配置文件: {env_file}")
else:
    print(f"⚠️  配置文件不存在: {env_file}")

class MindDaemonConfig:
    """Configuration manager for Mind Daemon system."""
    
    # ===== Emotiv BCI 配置 =====
    @property
    def emotiv_client_id(self) -> str:
        return os.getenv('EMOTIV_CLIENT_ID', '')
    
    @property
    def emotiv_client_secret(self) -> str:
        return os.getenv('EMOTIV_CLIENT_SECRET', '')
    
    # ===== MiniMax LLM 配置 =====
    @property
    def minimax_api_key(self) -> str:
        return os.getenv('MINIMAX_API_KEY', '')
    
    @property
    def minimax_base_url(self) -> str:
        return os.getenv('MINIMAX_BASE_URL', 'https://api.minimax.chat/v1/text/chatcompletion_v2')
    
    # ===== 系统配置 =====
    @property
    def user_id(self) -> str:
        return os.getenv('USER_ID', 'default_user')
    
    @property
    def csv_output_dir(self) -> str:
        return os.getenv('CSV_OUTPUT_DIR', 'bci_data')
    
    @property
    def music_dir(self) -> str:
        music_dir = os.getenv('MUSIC_DIR', 'music')
        # Convert to absolute path if relative
        if not os.path.isabs(music_dir):
            return str(project_root / music_dir)
        return music_dir
    
    # ===== 调试配置 =====
    @property
    def debug_mode(self) -> bool:
        return os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    
    @property
    def log_level(self) -> str:
        return os.getenv('LOG_LEVEL', 'INFO').upper()
    
    # ===== BCI 分析参数 =====
    @property
    def bci_window_size(self) -> int:
        return int(os.getenv('BCI_WINDOW_SIZE', '100'))
    
    @property
    def bci_analysis_interval(self) -> float:
        return float(os.getenv('BCI_ANALYSIS_INTERVAL', '1.0'))
    
    @property
    def action_cooldown(self) -> float:
        return float(os.getenv('ACTION_COOLDOWN', '30.0'))
    
    # ===== 外设控制配置 =====
    @property
    def halo_duration(self) -> float:
        return float(os.getenv('HALO_DURATION', '5.0'))
    
    @property
    def music_fade_duration(self) -> float:
        return float(os.getenv('MUSIC_FADE_DURATION', '10.0'))
    
    @property
    def default_volume(self) -> float:
        return float(os.getenv('DEFAULT_VOLUME', '0.5'))
    
    # ===== 辅助方法 =====
    def has_emotiv_credentials(self) -> bool:
        """Check if Emotiv credentials are provided."""
        return bool(self.emotiv_client_id and self.emotiv_client_secret)
    
    def has_minimax_api(self) -> bool:
        """Check if MiniMax API key is provided."""
        return bool(self.minimax_api_key)
    
    def get_absolute_path(self, path: str) -> str:
        """Convert relative path to absolute path based on project root."""
        if os.path.isabs(path):
            return path
        return str(project_root / path)
    
    def print_config_summary(self):
        """Print configuration summary (without sensitive data)."""
        print("🔧 Mind Daemon 配置摘要:")
        print(f"  Emotiv BCI: {'✅ 已配置' if self.has_emotiv_credentials() else '❌ 未配置'}")
        print(f"  MiniMax LLM: {'✅ 已配置' if self.has_minimax_api() else '❌ 未配置'}")
        print(f"  用户ID: {self.user_id}")
        print(f"  音乐目录: {self.music_dir}")
        print(f"  CSV输出: {self.csv_output_dir}")
        print(f"  调试模式: {'开启' if self.debug_mode else '关闭'}")
        print(f"  日志级别: {self.log_level}")

# 全局配置实例
config = MindDaemonConfig()

def get_config() -> MindDaemonConfig:
    """Get the global configuration instance."""
    return config

# 兼容性函数
def get_emotiv_credentials() -> tuple[str, str]:
    """Get Emotiv credentials as a tuple."""
    return config.emotiv_client_id, config.emotiv_client_secret

def get_minimax_api_key() -> str:
    """Get MiniMax API key."""
    return config.minimax_api_key

# 测试配置
if __name__ == '__main__':
    print("🧠 Mind Daemon 配置测试")
    print("=" * 40)
    
    config.print_config_summary()
    
    print(f"\n📂 路径信息:")
    print(f"  项目根目录: {project_root}")
    print(f"  .env文件: {env_file}")
    print(f"  音乐目录: {config.music_dir}")
    print(f"  CSV目录: {config.get_absolute_path(config.csv_output_dir)}")
    
    if config.has_emotiv_credentials():
        print(f"\n🔌 Emotiv配置:")
        print(f"  Client ID: {config.emotiv_client_id[:20]}...")
        print(f"  Client Secret: {config.emotiv_client_secret[:20]}...")
    
    if config.has_minimax_api():
        print(f"\n🤖 MiniMax配置:")
        print(f"  API Key: {config.minimax_api_key[:50]}...")
        print(f"  Base URL: {config.minimax_base_url}")