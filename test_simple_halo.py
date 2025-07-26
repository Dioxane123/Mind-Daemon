#!/usr/bin/env python3
"""
简单光晕测试 - 测试基本的PyQt6窗口显示
"""

import sys
import os
import time

# 添加项目路径
project_root = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(project_root, 'src'))

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor

class SimpleHaloWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # 设置窗口属性
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # 设置窗口大小和位置（小窗口用于测试）
        self.setGeometry(100, 100, 400, 300)
        
        # 设置背景颜色（红色，半透明）
        self.setStyleSheet("background-color: rgba(255, 0, 0, 128);")
        
        print("🔴 创建简单红色测试窗口")
        
        # 5秒后自动关闭
        QTimer.singleShot(5000, self.close)
        
    def paintEvent(self, event):
        """绘制事件"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 0, 0, 128))

def main():
    print("🧪 开始简单光晕测试...")
    
    app = QApplication(sys.argv)
    
    window = SimpleHaloWindow()
    window.show()
    
    print("✅ 窗口应该已显示，如果看到红色半透明窗口说明GUI正常")
    print("⏰ 窗口将在5秒后自动关闭")
    
    # 运行应用程序
    try:
        return app.exec()
    except KeyboardInterrupt:
        print("\n程序被中断")
        return 0

if __name__ == "__main__":
    sys.exit(main())