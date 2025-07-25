# Mind Daemon Dashboard

一个美观的实时数据监控仪表板，用于展示Mind Daemon系统的基本数据和高级分析结果。

## 功能特性

### 🏠 基本数据页面
- **灯光控制**: 显示灯光开关状态、RGB颜色值和亮度
- **背景音乐**: 显示当前播放的音乐信息和状态
- **窗帘状态**: 显示窗帘的开关状态
- **精神状态指标**: 实时显示专注值、兴奋值、放松度、紧张度

### 📊 高级数据页面
- **当前状态**: 显示用户的整体精神状态
- **AI分析建议**: 大模型给出的具体分析和建议
- **系统操作**: 显示系统当前执行的操作
- **数据趋势图**: 实时图表显示各项指标的变化趋势

## 技术栈

- **HTML5** - 现代语义化标记
- **CSS3** - Grid布局、Flexbox、CSS变量、现代设计
- **Vanilla JavaScript** - 无依赖的原生JS
- **Chart.js** - 数据可视化图表库
- **Font Awesome** - 图标库

## 文件结构

```
dashboard/
├── index.html      # 主页面
├── demo.html       # 演示页面（带交互控制）
├── style.css       # 样式文件
├── script.js       # JavaScript逻辑
└── README.md       # 说明文档
```

## 使用方法

### 1. 基本使用

直接在浏览器中打开 `index.html` 即可查看仪表板。页面会自动加载示例数据并每5秒更新一次模拟数据。

### 2. 演示模式

打开 `demo.html` 可以体验交互式演示，右上角有控制面板可以：
- 模拟不同的精神状态（压力、放松、专注）
- 切换灯光和音乐状态
- 更改灯光颜色
- 生成随机数据

### 3. 数据更新API

可以通过JavaScript API更新数据：

```javascript
// 更新基本数据
const basicData = {
    "light": { 
        "is_on": true,           // 灯光开关 (boolean)
        "color_hex": "#FF5733",  // RGB颜色值 (string)
        "lightness": 75          // 亮度 0-100 (number)
    },
    "music": { 
        "is_playing": true,      // 音乐播放状态 (boolean)
        "name": "Aria De Capo",  // 歌曲名称 (string)
        "type": "Relaxing"       // 音乐类型 (string)
    },
    "curtain": { 
        "state": 0               // 窗帘状态 0:开启 1:关闭 (number)
    },
    "Scores": {
        "At": 68,                // 专注值 0-100 (number)
        "Ex": 45,                // 兴奋值 0-100 (number)
        "Re": 72,                // 放松度 0-100 (number)
        "St": 35                 // 紧张度 0-100 (number)
    }
};

// 更新高级数据
const advancedData = {
    "State": "Relaxed",                    // 用户状态 (string)
    "Summary": "用户当前处于放松状态...",    // AI分析 (string)
    "Action": "Adjusting Light & Music"   // 系统操作 (string)
};

// 调用更新函数
updateDashboardData(basicData, advancedData);
```

### 4. Python集成示例

```python
import json
from pathlib import Path

def update_dashboard(basic_params, advanced_params):
    """
    更新dashboard数据
    """
    # 将数据写入JSON文件或通过WebSocket发送
    # 这里是一个简单的文件更新示例
    
    data = {
        'basic': basic_params,
        'advanced': advanced_params,
        'timestamp': time.time()
    }
    
    with open('dashboard_data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 使用示例
basic_params = {
    "light": {"is_on": True, "color_hex": "#FF5733", "lightness": 50},
    "music": {"is_playing": True, "name": "Aria De Capo", "type": "Relaxing"},
    "curtain": {"state": 0},
    "Scores": {"At": 50, "Ex": 50, "Re": 50, "St": 50}
}

advanced_params = {
    "State": "Relaxed",
    "Summary": "LLM分析结果...",
    "Action": "Notify"
}

update_dashboard(basic_params, advanced_params)
```

## 设计特点

### 🎨 现代UI设计
- 深色主题配色方案
- 卡片式布局
- 圆角和阴影效果
- 平滑的动画过渡

### 📱 响应式设计
- 支持桌面端和移动端
- 自适应网格布局
- 优化的移动端体验

### 🔄 实时更新
- 自动数据刷新
- 平滑的动画过渡
- 实时图表更新

### ⚡ 高性能
- 无框架依赖
- 优化的渲染性能
- 轻量级代码

## 浏览器兼容性

- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## 自定义配置

### 修改颜色主题

在 `style.css` 中的 `:root` 选择器内修改CSS变量：

```css
:root {
    --primary-color: #6366f1;     /* 主色调 */
    --secondary-color: #8b5cf6;   /* 辅助色 */
    --bg-color: #0f172a;          /* 背景色 */
    /* ... 其他颜色变量 */
}
```

### 修改更新频率

在 `script.js` 中修改定时器间隔：

```javascript
// 修改数据更新频率（毫秒）
setInterval(() => this.updateRandomData(), 3000); // 3秒更新一次
```

## 故障排除

### 图表不显示
确保Chart.js库正确加载：
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
```

### 图标不显示
确保Font Awesome库正确加载：
```html
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
```

### 样式异常
确保CSS文件路径正确：
```html
<link rel="stylesheet" href="style.css">
```

## 扩展功能

可以轻松扩展更多功能：
- 添加更多数据卡片
- 集成WebSocket实时通信
- 添加数据导出功能
- 增加用户设置面板
- 添加历史数据查看

## 许可证

此项目遵循MIT许可证。