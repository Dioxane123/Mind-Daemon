# Mind Daemon

**目标人群**：所有想要完成某些任务的人群，尤其是容易分心的ADHD患者。

## 🎯 系统概述

Mind Daemon是一个基于脑机接口(BCI)的智能专注辅助系统，通过实时监测用户的认知状态，自动调节环境来优化专注体验。

### 核心功能流程

1. **目标设定**: 用户设定专注目标和预计完成时间
2. **实时监测**: BCI设备实时检测用户专注程度和认知状态  
3. **智能决策**: AI Agent根据认知状态做出环境调节决策
4. **自动调节**: 系统自动控制光晕效果、背景音乐等环境因素
5. **状态切换**: 在专注、放松、心流等状态间智能切换

### 状态转换逻辑

- **低专注 → 放松模式**: 播放放松音乐，显示舒缓光晕
- **准备专注**: 手势控制进入专注准备，播放背景音乐
- **高专注 → 心流状态**: 逐渐降低音乐音量，逐渐降低光晕亮度至0，减少干扰
- **认知过载**: 停止音乐，显示警示光晕

## 🚀 快速开始

### 环境设置

```bash
# 1. 确保已安装uv包管理器
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 同步项目依赖
uv sync

# 3. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的API密钥和凭据
```

### 演示模式

```bash
# 一键运行演示选择器
python3 demos/run_demo.py

# 或直接指定模式:
python3 demos/run_demo.py basic        # 基础功能测试
python3 demos/run_demo.py peripherals  # 外设控制演示
python3 demos/run_demo.py complete     # 完整Agent系统演示
python3 demos/run_demo.py all          # 运行所有演示
```

### 可用演示模式

| 模式 | 说明 | 需求 |
|-----|------|------|
| `basic` | 基础集成测试 | 无 |
| `bci` | BCI状态分析器 | Emotiv设备 |
| `agent` | Agent决策系统 | Emotiv设备 |
| `integration` | 完整集成测试 | 无 (模拟数据) |
| `csv` | CSV数据记录 | 无 |
| `peripherals` | 外设控制 (光晕+音乐) | Emotiv设备, PyQt6 |
| `complete` | 完整Agent系统 | Emotiv设备, 可选LLM API |

## 🧠 系统架构

### 模块结构

```
Mind-Daemon/
├── src/mind_daemon/          # 主要源代码
│   ├── agent/               # 智能Agent系统
│   │   ├── intelligent_agent.py    # MiniMax LLM驱动的智能决策
│   │   ├── control_center.py       # 中央控制协调
│   │   ├── state_manager.py        # 状态管理
│   │   └── bci_interface.py        # BCI-Agent通信接口
│   ├── bci/                 # 脑机接口处理
│   │   ├── state_analyzer.py       # 实时认知状态分析
│   │   ├── csv_logger.py           # BCI数据记录
│   │   └── cortex.py               # Emotiv Cortex API
│   ├── peripheral/          # 外设控制
│   │   ├── halo_controller.py      # 屏幕光晕效果
│   │   ├── halo.py                 # PyQt6光晕实现
│   │   └── music_player.py         # 智能音乐播放
│   └── detect/              # 手势检测
|       ├── config.py               # 连接到开发板的配置文件
|       ├── gesture_detector.py     # 控制开发板上的ros服务和socket服务
|       └── socket_client.py        # 通过socket获取开发板上检测到的手势识别数据
├── demos/                   # 演示程序
├── docs/                    # 文档
├── music/                   # 背景音乐文件
└── tests/                   # 测试用例
```

### 核心组件

#### 1. BCI模块 (`src/mind_daemon/bci/`)
- **认知状态识别**: 7种状态 (高专注、低专注、认知过载、放松、困倦、中性、中等专注)
- **实时数据处理**: EEG信号分析和性能指标计算
- **CSV数据记录**: 完整的BCI数据日志记录

#### 2. Agent模块 (`src/mind_daemon/agent/`)
- **智能决策引擎**: MiniMax LLM驱动的上下文感知决策
- **状态管理**: 工作流状态跟踪和转换验证
- **中央控制**: 协调BCI输入和环境控制输出

#### 3. 外设模块 (`src/mind_daemon/peripheral/`)
- **屏幕光晕**: 基于认知状态的视觉反馈
- **智能音乐**: 根据专注水平自动调节的背景音乐

#### 4. 手势识别模块 (`src/mind_daemon/detect`)
- **控制开发板服务**: 利用控制脚本实现封装完好的开发板上ros的手势识别服务与socket服务控制功能
- **数据通信**: 通过socket将手势识别的数据传递给Agent模块

## 🎛️ 外设控制功能

### 光晕效果映射

| 认知状态 | 光晕颜色 | 视觉效果 | 含义 |
|---------|---------|----------|------|
| 高专注 | 🟢 绿色 | 稳定发光 | 保持心流状态 |
| 中等专注 | 🟡 黄色 | 柔和呼吸 | 专注进行中 |
| 低专注 | 🟠 橙色 | 提醒闪烁 | 注意力分散 |
| 放松 | 🔵 青色 | 舒缓呼吸 | 休息状态 |
| 困倦 | 🟣 紫色 | 慢速脉冲 | 需要休息 |
| 认知过载 | 🔴 红色 | 快速闪烁 | 降低负荷 |
| 中性 | 🔵 蓝色 | 默认发光 | 基线状态 |

### 音乐播放策略

- **专注状态**: 播放专注音乐，高专注时逐渐减音量
- **放松状态**: 播放舒缓音乐，适中音量
- **认知过载**: 停止音乐播放，减少干扰
- **低专注**: 轻柔背景音乐，较低音量

## 📊 数据记录与分析

### CSV数据记录
- **实时记录**: EEG通道数据、性能指标、认知状态
- **事件标记**: 会话开始/结束、状态变化、用户操作
- **完整元数据**: 时间戳、用户ID、会话信息

### 数据格式
```csv
timestamp,datetime_str,cognitive_state,confidence,attention_current,
engagement_score,relaxation_score,AF3,F7,F3,FC5,T7,P7,O1,O2,P8,T8,
FC6,F4,F8,AF4,session_id,user_id,notes
```

## 🔧 硬件要求

### BCI设备
- **Emotiv EPOC/Insight**: 官方支持的EEG头戴设备
- **Emotiv Launcher**: 必须运行的配套软件
- **设备凭证**: 需要Emotiv开发者账号的Client ID/Secret

### 开发板
- **D-Robotics RDK X5**: 由地瓜机器人提供的开发板
- **USB/MIPI 摄像头**: 用于拍摄获取用户当前手势

### 系统要求
- **操作系统**: macOS, Windows, Linux
- **Python**: 3.8+ (推荐3.12)
- **内存**: 至少2GB可用内存
- **显示**: 支持图形界面 (光晕效果)

### 可选组件
- **PyQt6**: 光晕效果支持
- **MiniMax API**: 智能决策增强
- **音频输出**: 音乐播放功能

## 🚀 部署指南

### 基础部署
```bash
# 1. 克隆项目
git clone <repository-url>
cd Mind-Daemon

# 2. 安装依赖
uv sync

# 3. 运行基础测试
python3 demos/run_demo.py basic
```

### 完整部署
```bash
# 1. 安装额外依赖
uv add PyQt6  # 光晕效果

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入以下信息:
# - EMOTIV_CLIENT_ID: 从 emotiv.com 开发者账户获取
# - EMOTIV_CLIENT_SECRET: 从 emotiv.com 开发者账户获取 
# - RDK_HOST: 根据访问开发板的方式不同填入对应的地址 
# - MINIMAX_API_KEY: 从 api.minimax.chat 获取 (可选)

# 3. 配置Emotiv设备
# - 安装EMOTIV Launcher
# - 连接设备或创建虚拟设备

# 4. 运行完整演示
python3 demos/run_demo.py complete
```

## 🔍 故障排除

### 常见问题

1. **BCI连接失败**
   - 确保EMOTIV Launcher已运行
   - 检查设备连接状态
   - 验证Client ID/Secret正确性

2. **光晕效果不显示**
   - 安装PyQt6: `uv add PyQt6`
   - 检查图形界面权限
   - 确认多显示器配置

3. **音乐播放问题**
   - 检查音乐文件存在 (`music/` 目录)
   - 确认音频系统工作正常
   - 验证文件格式支持 (MP3, WAV, M4A)

4. **配置问题**
   - 检查 `.env` 文件是否存在: `ls -la .env`
   - 验证凭据格式正确，无多余空格或引号
   - 确认 Emotiv Client ID/Secret 有效性

5. **依赖问题**
   - 重新同步: `uv sync`
   - 检查Python版本兼容性
   - 查看详细错误日志

### 性能优化

- **降低采样率**: 减少BCI数据处理频率
- **关闭不必要功能**: 禁用光晕或音乐
- **使用SSD**: 提高音乐文件读取速度
- **调整缓冲区**: 优化音频播放延迟

## ⚙️ 配置说明

### 环境变量配置

系统使用 `.env` 文件管理所有配置信息，包括：

#### 必需配置
```bash
# Emotiv BCI 设备凭据
EMOTIV_CLIENT_ID=your_client_id
EMOTIV_CLIENT_SECRET=your_client_secret
RDK_HOST=rdk_x5_host
```

#### 可选配置  
```bash
# MiniMax LLM API (智能决策)
MINIMAX_API_KEY=your_api_key

# 系统参数
USER_ID=your_user_id                  # 数据记录用户标识
CSV_OUTPUT_DIR=bci_data              # CSV数据输出目录
MUSIC_DIR=music                      # 音乐文件目录
HALO_DURATION=5.0                    # 光晕持续时间(秒)
DEFAULT_VOLUME=0.5                   # 默认音量(0.0-1.0)
```

### 配置方法

1. **复制模板**: `cp .env.example .env`
2. **编辑配置**: 使用文本编辑器修改 `.env` 文件
3. **验证配置**: `python3 src/mind_daemon/utils/config.py`

## 📚 开发文档

- [BCI外设使用指南](docs/BCI_外设使用指南.md)
- [Cortex API使用文档](docs/CortexAPI_使用文档.md)
- [RDK开发者手册](https://d-robotics.github.io/rdk_doc/RDK)
- [项目介绍](docs/intro.md)
- [演示指南](docs/DEMO_GUIDE.md)

## 🛣️ 发展路线

### 已完成功能 ✅
- [x] 实时BCI数据处理
- [x] 7种认知状态识别
- [x] 智能Agent决策引擎
- [x] 屏幕光晕效果控制
- [x] 智能音乐播放系统
- [x] 完整CSV数据记录
- [x] 多模态演示系统
- [x] 手势检测集成

### 开发中功能 🚧

- [ ] 长期休息检测
- [ ] 应用程序集成


### 计划功能 📋

- [ ] 高级数据分析(结合Transfer learning等方法改进当前数据分析模型)
- [ ] 主动大脑事件检测（即检测一些较为复杂的任务并将一些任务传输给Agent并返回一个优先任务队列，避免用户分心后重新进入心流困难）
- [ ] 自定义工作流
- [ ] 硬件外设扩展

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出功能建议！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 发起Pull Request

## 📄 许可证

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🙏 致谢

- Emotiv公司提供的BCI技术支持
- 地瓜机器人公司提供的RDK X5开发板支持
- MiniMax团队的LLM服务
- PyQt6团队的UI框架
- 所有贡献者和测试用户

---