# BCI 数据流 API 快速参考

## 快速开始

```python
from src.mind_daemon.bci import BCIDataStreamService

# 1. 初始化服务
service = BCIDataStreamService()

# 2. 添加数据回调
def handle_data(data):
    scores = data['scores']
    print(f"专注度: {scores['At']}, 压力: {scores['St']}")

service.add_data_callback(handle_data)

# 3. 启动服务（自动存储CSV）
service.start_service()

# 4. 停止服务
service.stop_service()
```

## 核心API

### BCIDataStreamService

| 方法 | 功能 |
|------|------|
| `start_service()` | 启动数据流和CSV存储 |
| `stop_service()` | 停止服务并关闭文件 |
| `add_data_callback(func)` | 添加数据处理回调 |
| `get_current_scores()` | 获取认知分数字典 |
| `get_service_status()` | 获取服务状态 |

### 数据回调格式

```python
def callback(data):
    # data = {
    #     'timestamp': '2025-07-26T22:40:35',
    #     'source': 'production_mode',  # 或 'dev_mode'
    #     'scores': {'At': 65, 'Ex': 45, 'Re': 78, 'St': 23},
    #     'met_data': [...],  # 性能指标原始数据
    #     'pow_data': [...]   # 频段功率原始数据
    # }
```

### 认知分数说明

| 指标 | 含义 | 范围 |
|------|------|------|
| `At` | 专注度 (Attention) | 0-100 |
| `Ex` | 兴奋度 (Excitement) | 0-100 |
| `Re` | 放松度 (Relaxation) | 0-100 |
| `St` | 压力值 (Stress) | 0-100 |

## 数据格式

### MET 数据（性能指标）
```python
# met_data[13个值]:
# [att_active, attention, eng_active, engagement, exc_active, excitement, 
#  lex, str_active, stress, rel_active, relaxation, int_active, interest]
```

### POW 数据（脑电频段功率）
```python
# pow_data[70个值]: 14个电极 × 5个频段
# 电极: AF3,F7,F3,FC5,T7,P7,O1,O2,P8,T8,FC6,F4,F8,AF4
# 频段: theta,alpha,betaL,betaH,gamma
```

## CSV存储

### 自动存储位置
- 目录: `.env` 中的 `DATA_DIR`（默认 `./data`）
- 文件: `{stream}_{timestamp}.csv`
- 格式: `time,timestamp,field1,field2,...`

### 存储的数据流
- `met_*.csv`: 性能指标数据
- `pow_*.csv`: 频段功率数据  
- `pow_5s_avg_*.csv`: 5秒平均功率数据

## 配置

### .env 文件
```env
EMOTIV_CLIENT_ID=your_client_id
EMOTIV_CLIENT_SECRET=your_client_secret
DATA_DIR=./data
DEV_MODE=false  # true=模拟数据, false=真实设备
```

## 简单示例

### 监控专注度
```python
service = BCIDataStreamService()

def focus_monitor(data):
    attention = data['scores']['At']
    if attention > 80:
        print("🔥 高度专注")
    elif attention < 40:
        print("😴 注意力不集中")

service.add_data_callback(focus_monitor)
service.start_service()
```

### 压力检测
```python
def stress_detector(data):
    stress = data['scores']['St']
    relaxation = data['scores']['Re']
    
    if stress > 70:
        print("⚠️  压力过高，建议休息")
    elif relaxation > 80:
        print("😌 状态良好")

service.add_data_callback(stress_detector)
```

## 注意事项

- ✅ 需要Emotiv设备和Emotiv Launcher
- ✅ CSV文件自动创建和存储
- ✅ 无设备时自动切换模拟数据
- ⚠️  大量数据时注意磁盘空间
- ⚠️  数据回调在独立线程执行