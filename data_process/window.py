import sys
import math
import time
from PyQt6.QtWidgets import QApplication, QWidget, QGraphicsBlurEffect
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QColor, QScreen, QPainterPath, QBrush

if sys.platform == "win32":
    import win32gui
    import win32con
    import win32api
    from ctypes import Structure, windll, c_uint, c_ulong, byref, sizeof
    
    class LASTINPUTINFO(Structure):
        _fields_ = [("cbSize", c_uint), ("dwTime", c_ulong)]
        
elif sys.platform == "darwin":
    from AppKit import NSWindow, NSScreenSaverWindowLevel, \
                       NSWindowCollectionBehaviorCanJoinAllSpaces, \
                       NSWindowCollectionBehaviorStationary, \
                       NSWindowCollectionBehaviorIgnoresCycle
    import objc
    from Quartz import CGEventSourceSecondsSinceLastEventType, kCGEventSourceStateCombinedSessionState, kCGAnyInputEventType

class IdleMonitor:
    """跨平台的用户活动监测类"""
    
    @staticmethod
    def get_idle_time():
        """获取用户空闲时间（秒）"""
        if sys.platform == "win32":
            lii = LASTINPUTINFO()
            lii.cbSize = sizeof(lii)
            windll.user32.GetLastInputInfo(byref(lii))
            return (win32api.GetTickCount() - lii.dwTime) / 1000.0
        elif sys.platform == "darwin":
            return CGEventSourceSecondsSinceLastEventType(
                kCGEventSourceStateCombinedSessionState, 
                kCGAnyInputEventType
            )
        else:
            return 0

class GlowWindow(QWidget):
    def __init__(self, idle_timeout=5):  # 默认5s空闲时间
        super().__init__()
        
        # --- 空闲检测参数 ---
        self.idle_timeout = idle_timeout  # 空闲超时时间（秒）
        self.is_auto_mode = True  # 是否启用自动模式
        self.is_glow_active = False  # 光晕是否激活

        # --- 新增：模糊效果 ---
        # 创建一个高斯模糊效果的实例
        self.blur_effect = QGraphicsBlurEffect()
        # 设置模糊半径，这个值越大，光晕越柔和、范围越广
        self.blur_effect.setBlurRadius(60) 
        self.setGraphicsEffect(self.blur_effect)

        # --- 修改：使用屏幕尺寸定位，避免在macOS上创建新桌面 ---
        # 获取主屏幕的几何尺寸
        primary_screen = QApplication.primaryScreen()
        screen_geometry = primary_screen.geometry()
        
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            # Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        # 手动设置窗口位置和大小以覆盖全屏
        self.setGeometry(screen_geometry)

        # --- 光晕效果参数 ---
        # 现在颜色不需要设置初始透明度，因为呼吸效果会控制它
        self.glow_color = QColor(153, 153, 255) 
        # 边框的厚度，可以根据喜好调整
        self.glow_thickness = 50
        self.animation_step = 0
        
        # --- 用于绘制的路径和画刷 (预先计算) ---
        self.glow_path = QPainterPath()
        self.glow_brush = QBrush(self.glow_color)
        
        # 预先计算光晕的形状路径，避免在每次重绘时都计算
        self.calculate_glow_path()

        # --- 动画计时器 ---
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self.update_animation)
        self.animation_timer.start(30)
        
        # --- 空闲检测计时器 ---
        self.idle_timer = QTimer(self)
        self.idle_timer.timeout.connect(self.check_idle_status)
        self.idle_timer.start(1000)  # 每秒检查一次
        
        # 初始状态：隐藏窗口
        self.hide()

    def showEvent(self, event):
        """This method is called when the widget is shown."""
        super().showEvent(event)  # Call the parent class's event handler
        self.force_behavior_and_stay_on_top() # Now call our native function

    def force_behavior_and_stay_on_top(self):
        """Uses platform-native APIs to force the window on top and set its behavior."""
        win_id = self.winId() # Get the handle here, now that it's valid

        if sys.platform == "win32":
            win32gui.SetWindowPos(win_id, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                                  win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
            print("Windows: Set top-most and ensured visibility.")
        elif sys.platform == "darwin":
            # The winId is the address of the NSView. We need its parent NSWindow.
            from ctypes import c_void_p
            # 1. 将窗口ID转换为ctypes的void指针
            view_pointer = c_void_p(int(win_id))
            address = int(win_id)
            view = objc.objc_object(c_void_p=view_pointer)
            window = view.window()
            if window:
                window.setLevel_(NSScreenSaverWindowLevel)
                
                behavior = (NSWindowCollectionBehaviorCanJoinAllSpaces |
                            NSWindowCollectionBehaviorStationary |
                            NSWindowCollectionBehaviorIgnoresCycle)
                window.setCollectionBehavior_(behavior)
                
                print("macOS: Set window level and collection behavior.")

    def check_idle_status(self):
        """检查用户空闲状态并控制光晕显示"""
        if not self.is_auto_mode:
            return
            
        idle_time = IdleMonitor.get_idle_time()
        
        # 如果空闲时间超过阈值且光晕未激活，则显示光晕
        if idle_time >= self.idle_timeout and not self.is_glow_active:
            self.activate_glow()
            print(f"用户空闲 {idle_time:.1f} 秒，激活光晕效果")
            
        # 如果用户恢复活动且光晕已激活，则隐藏光晕
        elif idle_time < 5 and self.is_glow_active:  # 5秒内有活动视为恢复
            self.deactivate_glow()
            print("检测到用户活动，隐藏光晕效果")
    
    def activate_glow(self):
        """激活光晕效果"""
        self.is_glow_active = True
        self.show()
        self.force_behavior_and_stay_on_top()
    
    def deactivate_glow(self):
        """取消光晕效果"""
        self.is_glow_active = False
        self.hide()
    
    def set_auto_mode(self, enabled):
        """启用/禁用自动模式"""
        self.is_auto_mode = enabled
        if not enabled and self.is_glow_active:
            self.deactivate_glow()
    
    def set_idle_timeout(self, seconds):
        """设置空闲超时时间"""
        self.idle_timeout = seconds
    
    def manual_toggle(self):
        """手动切换光晕显示状态"""
        if self.is_glow_active:
            self.deactivate_glow()
        else:
            self.activate_glow()

    def set_glow_color(self, r, g, b):
        """外部调用此函数来更新光晕颜色"""
        self.glow_color.setRgb(r, g, b)

    def update_animation(self):
        """更新动画的当前状态并重绘窗口"""
        self.animation_step += 0.05
        self.update()

    def calculate_glow_path(self):
        """计算用于绘制光晕的“画框”路径"""
        # 我们要绘制一个带有“空心”的矩形
        # QPainterPath的OddEvenFill规则可以轻松实现这一点
        self.glow_path = QPainterPath()
        self.glow_path.setFillRule(Qt.FillRule.OddEvenFill)
        
        # 外部大矩形就是整个窗口
        outer_rect = QRectF(self.rect())
        # 内部小矩形，通过向内收缩glow_thickness得到
        inner_rect = outer_rect.adjusted(
            self.glow_thickness, 
            self.glow_thickness, 
            -self.glow_thickness, 
            -self.glow_thickness
        )
        
        self.glow_path.addRect(outer_rect)
        self.glow_path.addRect(inner_rect)

    def paintEvent(self, event):
        """新的绘制方法：绘制带模糊的路径"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 使用sin函数计算当前呼吸周期的不透明度 (0.5到1.0之间)
        opacity_factor = 0.75 + 0.25 * math.sin(self.animation_step)
        
        # 将颜色和呼吸不透明度应用到画刷上
        current_color = QColor(self.glow_color)
        current_color.setAlphaF(opacity_factor)
        self.glow_brush.setColor(current_color)
        
        # 用设置好的画刷填充我们预先计算好的“画框”路径
        # QGraphicsBlurEffect 会自动处理模糊效果
        painter.fillPath(self.glow_path, self.glow_brush)

    def resizeEvent(self, event):
        """当窗口大小改变时（虽然我们是全屏，但这是个好习惯），重新计算路径"""
        super().resizeEvent(event)
        self.calculate_glow_path()

# 主程序入口 (可以和你的 MainController 结合使用)
if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # 创建光晕窗口，设置5分钟空闲超时
    window = GlowWindow(idle_timeout=1)
    
    # 可选：设置不同的空闲超时时间（例如30秒用于测试）
    # window.set_idle_timeout(30)
    
    # 可选：禁用自动模式，改为手动控制
    # window.set_auto_mode(False)
    
    # 可选：手动显示光晕（仅在禁用自动模式时有效）
    # window.manual_toggle()
    
    print("光晕效果已启动，自动检测用户空闲状态...")
    print(f"空闲超时设置: {window.idle_timeout} 秒")
    print("按 Ctrl+C 退出程序")
    
    try:
        sys.exit(app.exec())
    except KeyboardInterrupt:
        print("\n程序已退出")
        sys.exit(0)
