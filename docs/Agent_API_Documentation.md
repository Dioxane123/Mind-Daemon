# Mind-Daemon Agent 模块 API 文档

## 概述

Mind-Daemon Agent模块包含三个核心类，提供基于BCI数据的智能环境控制和决策功能。

## 核心类

### 1. MindDaemonSystem (控制中心)

**导入:** `from mind_daemon.agent.control_center import MindDaemonSystem`

#### 初始化
```python
system = MindDaemonSystem(config={
    'analysis_interval': 60,      # 分析间隔(秒)
    'llm_analysis_interval': 300, # LLM分析间隔(秒)  
    'enable_autonomous_agent': True
})
```

#### 主要方法

##### `run_single_analysis(include_llm=True, include_agent=True)`
执行单次完整的精神状态分析和干预决策。

**返回值:**
```json
{
  "success": true,
  "timestamp": "2025-07-26T10:30:00",
  "state_analysis": {
    "state": "FOCUSED",
    "confidence": 0.85,
    "details": "检测到专注状态"
  },
  "llm_analysis": {
    "assessment": "用户处于良好的专注状态",
    "recommendations": ["保持当前工作节奏"]
  },
  "agent_summary": {
    "triggered_actions_count": 2,
    "executed_actions_count": 2
  }
}
```

##### `run_continuous_monitoring(duration_minutes=0)`
启动持续监控模式，0表示无限运行。

---

### 2. EnvironmentAgent (环境控制智能体)

**导入:** `from mind_daemon.agent.environment_agent import EnvironmentAgent`

#### 环境变量配置
```bash
MUSIC_DIR=music
WINDOW_PY_PATH=src/mind_daemon/peripheral/window.py
MINIMAX_API_KEY=your_api_key
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/text/chatcompletion_v2
```

#### 初始化
```python
agent = EnvironmentAgent()
```

#### 主要方法

##### `analyze_and_control(current_state, confidence, metrics)`
**核心方法** - 分析状态并执行环境控制。

**参数:**
- `current_state`: 精神状态 ("FOCUSED", "STRESSED", "FATIGUED"等)
- `confidence`: 置信度 (0.0-1.0)
- `metrics`: 性能指标字典

**示例:**
```python
result = agent.analyze_and_control(
    current_state="STRESSED",
    confidence=0.8,
    metrics={"stress": 0.8, "attention": 0.3}
)

# 返回格式
{
  "decisions": {
    "light": {"action": "soft", "color": "#FFE4B5", "lightness": 60},
    "music": {"action": "switch", "type": "relax"},
    "halo": {"action": "activate", "color": [255, 228, 181]}
  },
  "actions_performed": ["切换至放松音乐", "激活软光晕效果"]
}
```

##### `get_current_environment_state()`
获取所有环境设备当前状态。

**返回值:**
```json
{
  "light": {"is_on": true, "color_hex": "#FFFFFF", "lightness": 80},
  "music": {"is_playing": true, "name": "Gymnopedies 1", "type": "relax"},
  "curtain": {"state": 0},
  "halo": {"is_active": false, "color_rgb": [0, 0, 0]}
}
```

##### `cleanup()`
清理资源，停止音乐和光晕效果。

---

### 3. MiniMaxAgent (智能决策引擎)

**导入:** `from mind_daemon.agent.minimax_agent import MiniMaxAgent`

#### 环境变量配置
```bash
MINIMAX_API_KEY=your_api_key
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/text/chatcompletion_v2
MINIMAX_MODEL=MiniMax-Text-01
```

#### 初始化
```python
agent = MiniMaxAgent()
```

#### 主要方法

##### `run_autonomous_cycle()`
**主入口方法** - 执行完整的自主决策循环。

**返回值:**
```json
{
  "current_state": "FOCUSED",
  "confidence": 0.85,
  "triggered_actions_count": 3,
  "executed_actions_count": 2,
  "successful_actions": 2,
  "strategy_generated": true
}
```

##### `generate_action_strategy(state_result, llm_result=None)`
生成个性化的行为策略建议。

**参数:**
- `state_result`: StateAnalysisResult对象
- `llm_result`: LLMAnalysisResult对象(可选)

**返回:** 策略建议文本

##### `call_minimax_api(prompt, temperature=0.7)`
直接调用MiniMax API。

**参数:**
- `prompt`: 输入提示文本
- `temperature`: 创造性控制(0.0-1.0)

**返回:** API响应内容

## 支持的行为类型

| 行为类型 | 描述 | 触发条件 |
|---------|-----|---------|
| `PLAY_MUSIC` | 播放音乐 | 压力/疲劳状态 |
| `SHOW_NOTIFICATION` | 显示通知 | 注意力分散 |
| `ADJUST_ENVIRONMENT` | 调节环境 | 状态变化 |
| `SUGGEST_BREAK` | 建议休息 | 疲劳检测 |
| `FOCUS_REMINDER` | 专注提醒 | 分心状态 |
| `RELAXATION_GUIDE` | 放松指导 | 高压力状态 |

## 完整使用示例

```python
from mind_daemon.agent.control_center import MindDaemonSystem

# 1. 创建系统实例
system = MindDaemonSystem()

# 2. 执行单次分析
result = system.run_single_analysis(
    include_llm=True,    # 包含LLM深度分析
    include_agent=True   # 包含智能体决策
)

# 3. 处理结果
if result['success']:
    print(f"当前状态: {result['state_analysis']['state']}")
    print(f"置信度: {result['state_analysis']['confidence']}")
    
    if 'llm_analysis' in result:
        print(f"LLM评估: {result['llm_analysis']['assessment']}")
    
    if 'agent_summary' in result:
        print(f"执行了 {result['agent_summary']['executed_actions_count']} 个行为")

# 4. 启动持续监控
system.run_continuous_monitoring(duration_minutes=30)
```

## 错误处理

所有方法都包含完善的异常处理，失败时返回包含 `error` 字段的字典：

```json
{
  "success": false,
  "error": "API调用失败",
  "timestamp": "2025-07-26T10:30:00"
}
```

## 配置要求

### 必需环境变量
- `MINIMAX_API_KEY`: MiniMax API密钥
- `MINIMAX_BASE_URL`: API服务端点

### 可选环境变量  
- `MUSIC_DIR`: 音乐目录 (默认: `music`)
- `WINDOW_PY_PATH`: 光晕程序路径 (默认: `src/mind_daemon/peripheral/window.py`)
- `LOG_FILE`: 日志文件 (默认: `mind_daemon.log`)

## 注意事项

1. **API密钥**: MiniMax API密钥是必需的，未配置时使用模拟响应
2. **文件路径**: 音乐目录和窗口程序路径需要存在
3. **资源清理**: 使用`EnvironmentAgent`后建议调用`cleanup()`
4. **并发安全**: 所有类都是线程安全的

---

*本文档基于 Mind-Daemon v1.0 编写，更新时间: 2025-07-26*