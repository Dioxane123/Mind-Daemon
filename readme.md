# Mind Daemon - BCI智能辅助系统

🧠 **基于脑机接口(BCI)的专注力和生产力辅助系统，专为ADHD患者设计**

Mind Daemon 通过 Emotiv BCI 设备监测用户的认知状态，并通过智能环境控制提供自动化辅助，帮助用户维持专注、减少分心、优化工作状态。

## ✨ 核心功能

- **🧠 实时BCI监测**: 使用Emotiv头戴设备监测脑电信号
- **📊 认知状态分析**: AI分析专注度、压力、疲劳、放松等状态  
- **🎵 智能音乐控制**: 根据状态自动切换专注/放松音乐
- **💡 环境光控制**: 智能调节灯光颜色和亮度
- **🌈 屏幕光晕提醒**: 柔和的视觉提醒和状态指示
- **📱 实时Dashboard**: Web界面显示所有数据和状态
- **🤖 MiniMax AI决策**: 基于LLM的智能干预建议

## 🏗️ 项目架构

```
Mind-Daemon/
├── src/mind_daemon/           # 核心Python包
│   ├── agent/                 # 智能体模块
│   │   ├── minimax_agent.py   # MiniMax决策智能体
│   │   ├── environment_agent.py # 环境控制智能体  
│   │   └── control_center.py  # 控制中心
│   ├── analyzers/             # 数据分析模块
│   │   ├── state_analyzer.py  # 认知状态分析器
│   │   ├── llm_analyzer.py    # LLM深度分析
│   │   └── algorithms.py      # 分析算法文档
│   ├── bci/                   # BCI数据处理模块
│   │   ├── cortex.py         # Emotiv Cortex API
│   │   ├── sub_data.py       # 数据订阅
│   │   ├── data_store.py     # 数据存储
│   │   └── realtime_service.py # 实时BCI服务
│   ├── interfaces/            # 通信接口模块
│   │   └── websocket_interface.py # WebSocket服务器
│   ├── peripheral/            # 外设控制模块
│   │   └── window.py         # 屏幕光晕控制
│   └── utils/                 # 工具模块
│       ├── config.py         # 配置管理
│       └── state_manager.py  # 状态管理
├── dashboard/                 # 前端Dashboard
│   ├── index.html            # 主页面
│   ├── script.js             # JavaScript逻辑
│   └── style.css             # 样式表
├── music/                     # 背景音乐
│   ├── focus/                # 专注音乐
│   └── relax/                # 放松音乐
├── .env.example              # 配置模板
├── pyproject.toml            # 项目配置
└── README.md                 # 本文档
```

## 🚀 快速开始

### 1. 环境准备

**系统要求:**
- Python 3.12+
- macOS/Linux/Windows
- Emotiv BCI设备（可选，支持开发模式）

**安装uv包管理器:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. 项目设置

**克隆项目:**
```bash
git clone <repository-url>
cd Mind-Daemon
```

**安装依赖:**
```bash
uv sync
```

**配置检查:**
项目已包含基础配置文件 `.env`，默认启用开发模式。如需自定义：
```bash
# 查看配置模板
cat .env.example
# 编辑实际配置
nano .env
```

### 3. 配置说明

在 `.env` 文件中配置以下关键参数:

```bash
# BCI设备配置 (如有Emotiv设备)
EMOTIV_CLIENT_ID=your_client_id
EMOTIV_CLIENT_SECRET=your_client_secret

# LLM API配置 (用于智能决策)
MINIMAX_API_KEY=your_minimax_key

# 开发模式 (无BCI设备时启用)
DEV_MODE=true

# 系统路径 (通常不需要修改)
MUSIC_DIR=/path/to/Mind-Daemon/music
```

### 4. 启动系统

**启动后端服务:**
```bash
uv run mind-daemon
```

服务器启动后会显示:
- WebSocket服务器: `ws://localhost:8889` 
- BCI数据处理服务
- 环境控制服务

**打开前端Dashboard:**
```bash
# 在浏览器中打开
open dashboard/index.html
```

## 📊 前后端数据交互

### WebSocket通信协议

**连接地址:** `ws://localhost:8889`

**数据格式:**
```javascript
{
  "basic": {
    "light": {
      "is_on": true,
      "color_hex": "#FF5733", 
      "lightness": 75
    },
    "music": {
      "is_playing": true,
      "name": "Aria De Capo",
      "type": "Relaxing"
    },
    "curtain": {
      "state": 0  // 0: 开, 1: 关
    },
    "Scores": {
      "At": 68,  // 专注度 (0-100)
      "Ex": 45,  // 兴奋度 (0-100) 
      "Re": 72,  // 放松度 (0-100)
      "St": 35   // 压力值 (0-100)
    },
    "timestamp": "2024-01-01T12:00:00"
  },
  "advanced": {
    "State": "Relaxed",           // 当前状态
    "Summary": "用户当前处于放松状态...", // AI分析摘要
    "Action": "Adjusting Light & Music", // 当前动作
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

### 前端JavaScript集成

```javascript
// 连接WebSocket
const socket = new WebSocket('ws://localhost:8889');

socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // 更新基础数据
    if (data.basic) {
        updateScores(data.basic.Scores);
        updateEnvironment(data.basic.light, data.basic.music);
    }
    
    // 更新高级数据  
    if (data.advanced) {
        updateState(data.advanced.State);
        updateSummary(data.advanced.Summary);
    }
};
```

## 🔧 开发模式

当没有BCI设备时，系统会自动使用模拟数据:

```bash
# 启用开发模式
echo "DEV_MODE=true" >> .env

# 运行系统
uv run mind-daemon
```

开发模式特性:
- 📈 模拟BCI数据生成
- 🎲 随机认知状态变化
- 🔄 完整的系统功能测试
- 📱 前端界面正常工作

## 🧪 测试系统

**运行集成测试:**
```bash
uv run python test_integration.py
```

**测试WebSocket连接:**
```bash
# 先启动服务器
uv run mind-daemon

# 在另一个终端测试连接
uv run python test_integration.py --test-websocket
```

**测试输出示例:**
```
🔄 测试WebSocket连接...
✅ WebSocket连接成功

📊 接收到数据 #1:
  💡 灯光: 开启
  🎵 音乐: 播放中  
  📊 分数: At=68 Ex=45
  🧠 状态: Relaxed
  ⚡ 动作: Adjusting Light & Music
```

## 🎵 音乐系统

**音乐目录结构:**
```
music/
├── focus/      # 专注音乐 (古典、器乐)
└── relax/      # 放松音乐 (环境音、慢节奏)
```

**支持格式:** `.mp3`, `.wav`, `.m4a`, `.flac`

**自动播放逻辑:**
- 🧠 检测到压力 → 自动切换放松音乐
- 🎯 检测到分心 → 自动切换专注音乐  
- 🔄 连续播放，智能选曲避重复
- 🔇 60秒切换冷却时间

## 💡 光晕系统

屏幕边缘光晕效果用于:
- 🔴 压力提醒 (红色/橙色)
- 🔵 专注辅助 (蓝色)
- 🟢 放松指示 (绿色)
- 🟡 注意力提醒 (黄色)

**控制逻辑:**
- 30秒激活冷却时间
- 15秒颜色变化冷却时间
- 心理学颜色原理指导

## 🤖 AI智能决策

**决策流程:**
1. **BCI数据采集** → 实时脑电信号
2. **状态分析** → 传统算法 + AI分析
3. **阈值判断** → 触发条件检测
4. **MiniMax决策** → LLM生成干预策略
5. **环境控制** → 执行具体调节动作

**支持的状态:**
- 🎯 `FOCUSED` - 专注状态
- 😌 `RELAXED` - 放松状态  
- 😰 `STRESSED` - 压力状态
- 😴 `FATIGUED` - 疲劳状态
- 😵 `DISTRACTED` - 分心状态

## 📱 Dashboard功能

**实时监控面板包含:**

1. **基础数据标签页:**
   - 💡 灯光状态和控制
   - 🎵 音乐播放状态
   - 🪟 窗帘状态
   - 📊 认知分数实时图表

2. **高级分析标签页:**
   - 🧠 当前精神状态
   - 📝 AI生成的状态摘要
   - ⚡ 系统执行的动作
   - 📈 历史趋势分析

3. **实时数据流:**
   - 🔄 每秒更新数据
   - 📈 动态图表显示
   - 🎨 状态颜色编码
   - ⏰ 时间戳显示

## 🔧 故障排除

**常见问题:**

1. **WebSocket连接失败**
   ```bash
   # 检查端口占用
   lsof -i :8889
   
   # 重启服务
   uv run mind-daemon
   ```

2. **BCI设备连接问题**
   ```bash
   # 检查Emotiv Launcher是否运行
   # 确认设备配对和权限
   # 启用开发模式测试: DEV_MODE=true
   ```

3. **音乐播放问题**
   ```bash
   # 检查音乐目录
   ls music/focus/ music/relax/
   
   # 检查音频权限 (macOS)
   # 系统偏好设置 -> 安全性与隐私 -> 麦克风
   ```

4. **前端显示问题**
   ```bash
   # 检查浏览器控制台错误
   # 确认WebSocket连接正常
   # 检查防火墙设置
   ```

## 🔒 隐私与安全

- 🔐 所有BCI数据本地处理，不上传云端
- 🔑 API密钥安全存储在.env文件中
- 📊 可选择关闭数据记录功能
- 🏠 完全离线运行（除LLM API调用外）

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -m 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

- 📧 Email: aster@hdu.edu.cn
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)
- 📖 文档: 查看项目Wiki

---

**Mind Daemon - 让AI成为你专注力的守护者** 🧠✨
EOF < /dev/null