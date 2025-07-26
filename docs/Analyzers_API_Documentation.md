# Mind-Daemon Analyzers 模块 API 文档

## 概述

Analyzers模块是Mind-Daemon的核心分析引擎，负责BCI数据处理、精神状态判断和LLM智能分析。

## 核心组件

### 1. StateAnalyzer (状态分析器)

**导入:** `from mind_daemon.analyzers.state_analyzer import StateAnalyzer, MentalState`

#### 初始化
```python
analyzer = StateAnalyzer(data_dir=None)  # 自动从环境变量DATA_PATH读取
```

#### 主要方法

##### `analyze_current_state() -> StateAnalysisResult`
**主入口方法** - 执行完整的精神状态分析。

**返回值:**
```python
StateAnalysisResult(
    state=MentalState.FOCUSED,     # 精神状态枚举
    confidence=0.85,               # 置信度(0-1)
    details="检测到专注状态",       # 详细描述
    metrics={                      # 关键指标
        'attention': 0.85,
        'stress': 0.3,
        'relaxation': 0.7
    },
    timestamp="2025-07-26T10:30:00"
)
```

##### `load_latest_data() -> Tuple[DataFrame, DataFrame]`
加载最新的met和pow CSV数据文件。

**返回:** `(met_data, pow_data)` 元组

##### `extract_metrics(met_data, pow_data, window_size=5) -> BCIMetrics`
从原始数据中提取BCI指标。

**参数:**
- `met_data`: 性能指标DataFrame
- `pow_data`: 频段功率DataFrame  
- `window_size`: 滑动窗口大小

#### 支持的精神状态
```python
class MentalState(Enum):
    FOCUSED = 1      # 专注状态
    RELAXED = 2      # 放松状态
    EXCITED = 3      # 兴奋状态
    STRESSED = 4     # 压力状态
    DISTRACTED = 5   # 分心状态
    NEUTRAL = 6      # 中性状态
    FATIGUED = 7     # 疲劳状态
```

---

### 2. LLMAnalyzer (LLM分析器)

**导入:** `from mind_daemon.analyzers.llm_analyzer import LLMAnalyzer`

#### 环境变量配置
```bash
MINIMAX_API_KEY=your_api_key
MINIMAX_BASE_URL=https://api.minimaxi.com/v1/text/chatcompletion_v2
OPENAI_API_KEY=your_openai_key  # 可选
```

#### 初始化
```python
analyzer = LLMAnalyzer(data_dir=None, llm_config=None)
```

#### 主要方法

##### `analyze_mental_state(window_minutes=30, llm_type="generic") -> LLMAnalysisResult`
**主入口方法** - 执行完整的LLM精神状态分析。

**参数:**
- `window_minutes`: 分析时间窗口(分钟)
- `llm_type`: LLM类型 ("generic", "minimax", "openai")

**返回值:**
```python
LLMAnalysisResult(
    summary="用户处于良好的专注状态...",
    mental_state_assessment="平衡的认知状态",
    key_insights=[
        "注意力保持稳定",
        "压力水平适中"
    ],
    recommendations=[
        "保持当前工作节奏",
        "适当安排休息"
    ],
    risk_factors=["长时间工作可能导致疲劳"],
    positive_indicators=["稳定的注意力水平"],
    confidence_level="中",  # "高"/"中"/"低"
    analysis_timestamp="2025-07-26T10:30:00"
)
```

##### `collect_metrics_statistics(window_minutes=30) -> Tuple[List, AnalysisPeriod]`
收集指定时间窗口内的指标统计数据。

**返回:** `(统计数据列表, 分析时间段信息)`

##### `call_llm_api(prompt, llm_type="generic") -> str`
直接调用LLM API。

**参数:**
- `prompt`: 分析提示文本
- `llm_type`: API类型

##### `save_analysis_report(result, filename=None) -> str`
保存分析报告到JSON文件。

**返回:** 保存的文件路径

---

### 3. RealtimeAlgorithms (实时算法)

**导入:** `from mind_daemon.analyzers.realtime_algorithms import get_algorithm_analyzer`

#### 使用方法
```python
analyzer = get_algorithm_analyzer()

# 执行算法分析
analysis = analyzer.get_algorithm_analysis(
    pow_values=[0.5, 0.3, ...],    # 功率数据列表
    pow_labels=['AF3/theta', ...]  # 对应的电极/频段标签
)

# 返回格式
{
    "clinical_analysis": {
        "state": "NOMINAL_STABLE",     # 临床状态
        "confidence": 0.75
    },
    "cognitive_analysis": {
        "state": "RELAXED_IDLE",       # 认知状态  
        "confidence": 0.82
    }
}
```

#### 支持的分析类型
- **Clinical Analysis**: 临床级别的状态判断
- **Cognitive Analysis**: 认知功能评估

---

## 完整使用示例

### 单独使用状态分析器
```python
from mind_daemon.analyzers.state_analyzer import StateAnalyzer

# 创建分析器
analyzer = StateAnalyzer()

# 执行分析
result = analyzer.analyze_current_state()

print(f"状态: {result.state.name}")
print(f"置信度: {result.confidence:.2f}")
print(f"详情: {result.details}")
```

### 使用LLM深度分析
```python
from mind_daemon.analyzers.llm_analyzer import LLMAnalyzer

# 创建LLM分析器
llm_analyzer = LLMAnalyzer()

# 执行深度分析
result = llm_analyzer.analyze_mental_state(
    window_minutes=30,
    llm_type="minimax"
)

print(f"评估: {result.mental_state_assessment}")
print(f"建议: {result.recommendations}")

# 保存报告
filepath = llm_analyzer.save_analysis_report(result)
```

### 集成使用
```python
from mind_daemon.analyzers.state_analyzer import StateAnalyzer
from mind_daemon.analyzers.llm_analyzer import LLMAnalyzer

# 创建分析器
state_analyzer = StateAnalyzer()
llm_analyzer = LLMAnalyzer()

# 执行传统分析
state_result = state_analyzer.analyze_current_state()

# 基于传统分析结果执行LLM分析
if state_result.confidence > 0.6:
    llm_result = llm_analyzer.analyze_mental_state()
    
    print(f"传统分析: {state_result.state.name}")
    print(f"LLM评估: {llm_result.mental_state_assessment}")
```

## 配置要求

### 必需环境变量
- `DATA_PATH`: 数据文件目录路径 (默认: `./data`)

### LLM功能需要的环境变量
- `MINIMAX_API_KEY`: MiniMax API密钥
- `MINIMAX_BASE_URL`: MiniMax API端点
- `OPENAI_API_KEY`: OpenAI API密钥 (可选)

### 数据文件要求
- CSV数据文件需存放在`DATA_PATH`目录下
- 文件名格式: `met_YYYYMMDD_HHMMSS.csv`, `pow_YYYYMMDD_HHMMSS.csv`
- 包含时间戳和相应的BCI指标数据

## 错误处理

所有方法都包含完善的异常处理：

```python
try:
    result = analyzer.analyze_current_state()
except FileNotFoundError as e:
    print(f"数据文件未找到: {e}")
except Exception as e:
    print(f"分析失败: {e}")
```

## 性能说明

- **StateAnalyzer**: 轻量级分析，毫秒级响应
- **LLMAnalyzer**: 依赖API调用，响应时间2-10秒
- **RealtimeAlgorithms**: 实时处理，适合高频数据流

## 注意事项

1. **数据依赖**: 需要有效的BCI数据文件
2. **API配置**: LLM功能需要配置相应的API密钥
3. **时间窗口**: LLM分析建议使用15-60分钟窗口
4. **置信度**: 建议只在置信度>0.6时使用分析结果
5. **资源管理**: LLM分析消耗较多资源，建议控制调用频率

---

*本文档基于测试结果编写，更新时间: 2025-07-26*