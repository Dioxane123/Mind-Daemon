# BCI外设使用指南

Mind Daemon系统集成了光晕效果和音乐播放功能，可以根据BCI检测到的认知状态自动调节，为用户提供沉浸式的专注体验。

## 🎯 功能概述

### 光晕效果 (Halo Effects)
- **位置**: 屏幕边缘柔光效果
- **响应**: 根据认知状态自动变色
- **技术**: PyQt6 + 跨平台窗口管理

### 音乐播放 (Music Player)
- **音源**: 本地音乐文件 (`music/` 目录)
- **智能**: 根据专注水平自动调节音量
- **支持**: MP3, WAV, M4A 格式

## 🚀 快速开始

### 1. 基础演示 (推荐)
```bash
# 运行基础功能测试 (无需BCI设备)
python3 demos/run_demo.py basic
```

### 2. 外设控制演示 (需要BCI设备)
```bash
# 运行完整的BCI外设控制演示
python3 demos/run_demo.py peripherals
```

### 3. 分模块测试
```bash
# CSV数据记录
python3 demos/run_demo.py csv

# 完整集成测试
python3 demos/run_demo.py integration
```

## 🎛️ 外设功能详解

### 光晕效果映射

| 认知状态 | 光晕颜色 | 含义 | 特殊效果 |
|---------|---------|------|----------|
| `high_focus` | 🟢 绿色 | 高度专注 | 稳定发光 |
| `medium_focus` | 🟡 黄色 | 中等专注 | 柔和呼吸 |
| `low_focus` | 🟠 橙色 | 注意力不集中 | 提醒闪烁 |
| `relaxed` | 🔵 青色 | 放松状态 | 舒缓呼吸 |
| `drowsy` | 🟣 紫色 | 困倦/疲劳 | 慢速脉冲 |
| `cognitive_overload` | 🔴 红色 | 认知过载 | 快速闪烁 |
| `neutral` | 🔵 蓝色 | 中性状态 | 默认发光 |

### 音乐播放策略

#### 专注状态 (`high_focus`, `medium_focus`)
- **初始**: 播放专注音乐 (或放松音乐)
- **高专注时**: 逐渐降低音量 (8秒内)
- **目的**: 减少干扰，保持心流状态

#### 放松状态 (`relaxed`, `drowsy`)
- **播放**: 放松音乐
- **音量**: 适中 (0.6)
- **目的**: 舒缓紧张，促进休息

#### 认知过载 (`cognitive_overload`)
- **动作**: 停止音乐播放
- **渐停**: 5秒内渐弱至停止
- **目的**: 减少认知负担

#### 注意力不集中 (`low_focus`)
- **播放**: 轻柔背景音乐
- **音量**: 较低 (0.4)
- **目的**: 帮助重新集中注意力

## 🎵 音乐文件管理

### 文件结构
```
music/
├── BWV 988Aria da capo_relax.mp3      # 放松音乐
├── Gymnopedies 1_relax.mp3            # 放松音乐
├── Gymnopedies 2_relax.mp3            # 放松音乐
├── Gymnopedies 3_relax.mp3            # 放松音乐
├── 音に出来る事_relax.mp3             # 放松音乐
├── Nikolai Kapustin - Etudes (多首)   # 专注音乐
└── ...
```

### 音乐分类规则
- **放松音乐**: 文件名包含 `relax` 或 `_relax`
- **专注音乐**: 文件名包含 `focus` 或无特殊标记
- **自动检测**: 系统自动扫描并分类音乐文件

### 添加新音乐
1. 将音乐文件复制到 `music/` 目录
2. 按命名规则重命名:
   - 放松音乐: `曲名_relax.mp3`
   - 专注音乐: `曲名_focus.mp3` 或 `曲名.mp3`
3. 重启系统自动加载

## 💡 光晕效果技术细节

### 系统要求
- **macOS**: 原生支持
- **Windows**: 需要管理员权限 (某些情况)
- **Linux**: 需要X11支持

### 依赖安装
```bash
# 安装PyQt6 (如果未安装)
pip install PyQt6

# 或使用uv
uv add PyQt6
```

### 配置选项
```python
# 在代码中可以调整的参数
halo_controller = HaloController()
halo_controller.set_color('high_focus')  # 设置颜色
halo_controller.show_notification_halo(duration=5.0)  # 显示5秒
```

## 🔧 故障排除

### 光晕效果不显示
1. **检查PyQt6安装**:
   ```bash
   python -c "import PyQt6; print('PyQt6 已安装')"
   ```

2. **权限问题** (macOS):
   - 允许应用控制屏幕
   - 系统偏好设置 → 安全性与隐私 → 辅助功能

3. **多显示器支持**:
   - 默认在主显示器显示
   - 可以通过代码配置其他显示器

### 音乐播放问题

1. **无音乐播放**:
   ```bash
   # 检查音乐文件
   ls -la music/
   
   # 检查音频系统 (macOS)
   which afplay
   ```

2. **音频格式支持**:
   - ✅ 支持: MP3, WAV, M4A
   - ❌ 不支持: FLAC, OGG (需要额外播放器)

3. **音量控制问题**:
   - 系统音量需要开启
   - 检查应用音频权限

### BCI连接问题

1. **EMOTIV Launcher**:
   - 确保已运行且设备已连接
   - 检查设备电量和连接状态

2. **应用授权**:
   - 首次运行需要授权
   - 在EMOTIV App中管理应用权限

3. **网络连接**:
   - BCI数据处理需要稳定网络
   - 检查防火墙设置

## 📊 性能优化

### 资源使用
- **CPU**: 轻量级处理，通常 < 5%
- **内存**: 约 50-100MB
- **网络**: BCI数据流，约 1-2KB/s

### 优化建议
1. **关闭不必要的可视效果**
2. **调整数据处理频率**
3. **使用SSD存储音乐文件**

## 🎨 自定义配置

### 光晕颜色自定义
```python
# 修改 halo_controller.py 中的颜色映射
state_colors = {
    'high_focus': (0, 255, 0),      # 绿色
    'relaxed': (0, 255, 255),       # 青色
    # 添加自定义颜色...
}
```

### 音乐播放逻辑自定义
```python
# 修改 test_bci_peripherals.py 中的音乐处理逻辑
def _handle_music_for_state(self, state: str):
    # 自定义播放策略
    pass
```

## 🔍 高级用法

### 编程接口
```python
from mind_daemon.peripheral.halo_controller import HaloController
from mind_daemon.peripheral.music_player import MusicPlayer

# 初始化控制器
halo = HaloController()
music = MusicPlayer(music_dir="./music")

# 手动控制
halo.show_cognitive_state_halo('high_focus')
music.play_focus_music()

# 获取状态
print(halo.get_status())
print(music.get_status())
```

### 与其他系统集成
- **MIDI设备**: 可扩展支持MIDI音频设备
- **智能家居**: 集成HomeKit/Alexa控制
- **生产力工具**: 与日历、任务管理器联动

## 📈 效果评估

### 用户体验指标
- **专注时长**: 通过BCI数据量化
- **状态切换频率**: 评估认知稳定性
- **主观感受**: 用户反馈问卷

### 数据分析
```bash
# 查看CSV记录数据
python -c "import pandas as pd; print(pd.read_csv('bci_data/latest.csv').describe())"
```

通过这个全面的外设控制系统，Mind Daemon 能够为用户提供智能化的专注环境，根据实时的认知状态自动调节光晕效果和背景音乐，创造最佳的工作和学习体验！