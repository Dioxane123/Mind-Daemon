# WebSocket接口与前端集成文档

## 概述

本文档说明Mind Daemon WebSocket接口与Dashboard前端的数据格式匹配情况，以及如何扩展前端以支持新的数据项。

## 接口结构分析

### 已删除冗余接口
- ❌ `enhanced_socket_interface.py` - 传统Socket接口（已删除）
- ✅ `websocket_interface.py` - 现代WebSocket接口（保留）

**删除原因**：
1. 功能重复：两个接口提供相同的数据结构
2. 前端使用WebSocket协议：`ws://localhost:8889`
3. WebSocket接口功能更全面，包含算法分析数据

## 数据格式匹配验证

### ✅ WebSocket 输出格式

```json
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
      "state": 0
    },
    "Scores": {
      "At": 68,
      "Ex": 45, 
      "Re": 72,
      "St": 35
    },
    "algorithm_analysis": {
      "clinical_analysis": {
        "state": "NOMINAL_STABLE",
        "faa_z_score": 0.25,
        "theta_z_score": -0.15,
        "details": "No significant deviation from baseline detected."
      },
      "cognitive_analysis": {
        "state": "NEUTRAL",
        "engagement_index": 1.2,
        "fatigue_index": 0.8,
        "details": "Balanced cognitive state."
      }
    },
    "timestamp": "2025-07-26T22:40:35.767000"
  },
  "advanced": {
    "State": "Relaxed",
    "Summary": "用户当前处于放松状态，建议播放轻柔音乐...",
    "Action": "Adjusting Light & Music",
    "clinical_analysis": {...},
    "cognitive_analysis": {...},
    "timestamp": "2025-07-26T22:40:35.767000"
  }
}
```

### ✅ 前端期望格式

前端JavaScript代码期望的数据结构：

```javascript
// Basic数据处理 (script.js:80-92)
if (data.basic.light && data.basic.music && data.basic.curtain && data.basic.Scores) {
    this.updateBasicData(data.basic);
    this.updateChart(data.basic.Scores);
}

// 算法分析数据处理 (script.js:88-91)
if (data.basic.algorithm_analysis) {
    this.updateAlgorithmAnalysis(data.basic.algorithm_analysis);
}

// Advanced数据处理 (script.js:94-100)
if (data.advanced.State && data.advanced.Summary && data.advanced.Action) {
    this.updateAdvancedData(data.advanced);
    this.updateStateHistory(data.advanced.State);
}
```

### 🎯 匹配结果：完全匹配 ✅

| 数据项 | WebSocket提供 | 前端期望 | 匹配状态 |
|--------|---------------|----------|----------|
| `basic.light` | ✅ | ✅ | ✅ |
| `basic.music` | ✅ | ✅ | ✅ |
| `basic.curtain` | ✅ | ✅ | ✅ |
| `basic.Scores` | ✅ | ✅ | ✅ |
| `basic.algorithm_analysis` | ✅ | ✅ | ✅ |
| `advanced.State` | ✅ | ✅ | ✅ |
| `advanced.Summary` | ✅ | ✅ | ✅ |
| `advanced.Action` | ✅ | ✅ | ✅ |
| `clinical_analysis` | ✅ | ✅ | ✅ |
| `cognitive_analysis` | ✅ | ✅ | ✅ |

## 数据字段详细说明

### Basic Parameters

#### Light Control (灯光控制)
```json
{
  "is_on": boolean,        // 灯光开关状态
  "color_hex": string,     // 颜色十六进制值 (如 "#FF5733")
  "lightness": number      // 亮度百分比 (0-100)
}
```

#### Music Control (音乐控制)
```json
{
  "is_playing": boolean,   // 音乐播放状态
  "name": string,          // 歌曲名称
  "type": string           // 音乐类型 (如 "Relaxing")
}
```

#### Curtain Control (窗帘控制)
```json
{
  "state": number          // 窗帘状态 (0=开启, 1=关闭)
}
```

#### Cognitive Scores (认知分数)
```json
{
  "At": number,            // Attention (专注度) 0-100
  "Ex": number,            // Excitement (兴奋度) 0-100
  "Re": number,            // Relaxation (放松度) 0-100
  "St": number             // Stress (压力值) 0-100
}
```

### Advanced Parameters

#### Mental State (精神状态)
- `State`: 当前精神状态 ("Relaxed", "Focused", "Stressed", "Excited")
- `Summary`: AI生成的状态分析文本
- `Action`: 系统执行的操作描述

#### Algorithm Analysis (算法分析)

##### Clinical Analysis (临床分析)
```json
{
  "state": string,         // 抑郁风险状态
  "faa_z_score": number,   // FAA Z-Score值
  "theta_z_score": number, // Theta Z-Score值
  "details": string        // 分析详情
}
```

##### Cognitive Analysis (认知分析)
```json
{
  "state": string,         // 认知状态
  "engagement_index": number, // 参与度指数
  "fatigue_index": number, // 疲劳指数
  "details": string        // 分析详情
}
```

## 如何扩展前端以支持新数据项

### 步骤1：修改WebSocket接口

如果要添加新的数据项，首先在 `websocket_interface.py` 中修改数据结构：

```python
# 在BasicParams或AdvancedParams类中添加新字段
@dataclass
class BasicParams:
    # 现有字段...
    new_field: Dict[str, Any]  # 新增字段

# 在生成方法中提供数据
def generate_basic_params(self) -> BasicParams:
    return BasicParams(
        # 现有字段...
        new_field={"value": 123, "status": "active"},
        timestamp=datetime.now().isoformat()
    )
```

### 步骤2：更新前端HTML结构

在 `dashboard/index.html` 中添加新的UI元素：

```html
<!-- 在适当的位置添加新卡片 -->
<div class="card new-feature-card">
    <div class="card-header">
        <h3><i class="fas fa-new-icon"></i> 新功能</h3>
    </div>
    <div class="card-content">
        <div class="new-feature-info">
            <div class="info-item">
                <span class="label">数值:</span>
                <span class="value" id="new-field-value">0</span>
            </div>
            <div class="info-item">
                <span class="label">状态:</span>
                <span class="value" id="new-field-status">inactive</span>
            </div>
        </div>
    </div>
</div>
```

### 步骤3：更新JavaScript处理逻辑

在 `dashboard/script.js` 中添加数据处理方法：

```javascript
updateBasicDataFromSocket(data) {
    // 现有代码...
    
    // 处理新字段
    if (data.basic.new_field) {
        this.updateNewField(data.basic.new_field);
    }
}

updateNewField(newFieldData) {
    // 更新UI元素
    const valueElement = document.getElementById('new-field-value');
    const statusElement = document.getElementById('new-field-status');
    
    if (valueElement) {
        valueElement.textContent = newFieldData.value;
    }
    
    if (statusElement) {
        statusElement.textContent = newFieldData.status;
        // 根据状态设置样式
        statusElement.className = newFieldData.status === 'active' ? 'status-active' : 'status-inactive';
    }
}
```

### 步骤4：更新CSS样式

在 `dashboard/style.css` 中添加新样式：

```css
.new-feature-card {
    /* 卡片样式 */
}

.new-feature-info {
    /* 信息布局样式 */
}

.status-active {
    color: var(--success-color);
}

.status-inactive {
    color: var(--error-color);
}
```

### 步骤5：添加图表支持（可选）

如果新数据需要图表显示：

```javascript
// 添加新图表初始化
initNewChart() {
    const ctx = document.getElementById('newChart').getContext('2d');
    this.newChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: '新指标',
                data: [],
                borderColor: '#ff6b6b',
                backgroundColor: 'rgba(255, 107, 107, 0.1)'
            }]
        },
        options: {
            // 图表配置
        }
    });
}

// 更新图表数据
updateNewChart(newData) {
    // 图表更新逻辑
}
```

## 最佳实践

### 1. 数据验证
```javascript
updateBasicDataFromSocket(data) {
    // 验证数据完整性
    if (!data || !data.basic) {
        console.warn('Invalid data structure received');
        return;
    }
    
    // 逐项验证
    if (data.basic.new_field && typeof data.basic.new_field === 'object') {
        this.updateNewField(data.basic.new_field);
    }
}
```

### 2. 错误处理
```javascript
updateNewField(newFieldData) {
    try {
        // 数据处理逻辑
        const valueElement = document.getElementById('new-field-value');
        if (valueElement) {
            valueElement.textContent = newFieldData.value || 'N/A';
        }
    } catch (error) {
        console.error('Failed to update new field:', error);
    }
}
```

### 3. 性能优化
```javascript
// 使用防抖避免过频繁更新
const debounce = (func, wait) => {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
};

// 应用到更新方法
this.debouncedUpdate = debounce(this.updateNewField.bind(this), 100);
```

## 调试和测试

### 1. 浏览器开发者工具
- 打开 F12 开发者工具
- 在 Console 中监控 WebSocket 连接状态
- 查看 Network 标签页的 WebSocket 消息

### 2. 数据格式验证
```javascript
// 在 script.js 中添加调试代码
updateBasicDataFromSocket(data) {
    console.log('Received WebSocket data:', data);
    
    // 验证数据结构
    if (data.basic) {
        console.log('Basic data keys:', Object.keys(data.basic));
    }
    if (data.advanced) {
        console.log('Advanced data keys:', Object.keys(data.advanced));
    }
}
```

### 3. 使用CLI监听工具
见下方的 `websocket_monitor.py` 工具，可以独立测试WebSocket数据流。

## 总结

现有的WebSocket接口与前端Dashboard完全匹配，无需修改。如果需要扩展新功能，按照上述步骤进行：

1. ✅ 数据格式完全匹配
2. ✅ 实时通信正常工作  
3. ✅ 算法分析数据支持完整
4. ✅ 图表和UI元素齐全

扩展时遵循：**后端数据结构 → 前端HTML结构 → JavaScript处理 → CSS样式** 的顺序进行开发。