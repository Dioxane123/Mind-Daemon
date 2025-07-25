"""
Mind Daemon - BCI-powered focus and productivity system for ADHD patients

This package provides a complete system for monitoring mental states through
BCI devices and providing automated environmental assistance.
"""

import asyncio
import logging

__version__ = "0.1.0"

def main() -> None:
    """Main entry point for the mind-daemon CLI."""
    try:
        print("🧠 Mind Daemon - BCI智能辅助系统启动中...")
        print("   版本:", __version__)
        print("   WebSocket服务器: ws://localhost:8889")
        print("   前端Dashboard: 请打开 dashboard/index.html")
        print("   按 Ctrl+C 停止服务器\n")
        
        # 导入并创建WebSocket接口
        from .interfaces.websocket_interface import WebSocketInterface
        interface = WebSocketInterface()
        asyncio.run(interface.start_server())
        
    except KeyboardInterrupt:
        print("\n👋 Mind Daemon 已停止")
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        logging.error(f"Mind Daemon启动失败: {e}")
