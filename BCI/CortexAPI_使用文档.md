# Emotiv Cortex API 使用文档

## 目录
1. [概述](#概述)
2. [API核心架构](#api核心架构)
3. [环境配置与准备](#环境配置与准备)
4. [基础工作流程](#基础工作流程)
5. [心理指令训练API](#心理指令训练api)
6. [数据流订阅](#数据流订阅)
7. [会话和记录管理](#会话和记录管理)
8. [高级功能](#高级功能)
9. [错误处理](#错误处理)
10. [代码示例](#代码示例)

---

## 概述

Emotiv Cortex API 是一个强大的脑机接口(BCI)平台，支持多种编程语言和框架：
- **Python** - 基于WebSocket的事件驱动架构
- **C#** - 完整的.NET示例套件
- **Node.js** - 异步JavaScript实现
- **C++/Qt** - 跨平台桌面应用
- **Unity** - 游戏和VR应用集成

### 主要功能
- **脑电图(EEG)数据采集**
- **心理指令(Mental Command)训练和检测**
- **面部表情(Facial Expression)识别**
- **性能指标(Performance Metrics)监测**
- **数据记录和导出**
- **实时数据流处理**

---

## API核心架构

### 核心类说明

#### Cortex类 (`cortex.py`)
```python
class Cortex(Dispatcher):
    """
    Cortex API的核心包装器类
    
    主要功能:
    - WebSocket连接管理
    - JSON-RPC请求构建和发送
    - 事件分发和回调处理
    - 会话和设备管理
    """
```

#### Train类 (`mental_command_train.py`)
```python
class Train():
    """
    心理指令训练控制类
    
    主要功能:
    - 控制心理指令检测训练过程
    - 管理训练配置文件
    - 处理训练事件回调
    """
```

### 事件系统
API采用事件驱动架构，主要事件包括：
- `create_session_done` - 会话创建完成
- `query_profile_done` - 配置文件查询完成
- `load_unload_profile_done` - 配置文件加载/卸载完成
- `new_data_labels` - 新数据标签
- `new_sys_data` - 系统事件数据
- `inform_error` - 错误信息

---

## 环境配置与准备

### 1. 系统要求
```bash
# Python依赖
pip install websocket-client
pip install python-dispatch

# 或使用requirements.txt
pip install -r requirements.txt
```

### 2. EMOTIV环境配置
1. **下载并安装EMOTIV Launcher**
   - 官方下载地址：https://www.emotiv.com/products/emotiv-launcher
   - 使用Emotiv ID登录
   - 接受服务条款和隐私政策

2. **获取设备**
   - 购买EMOTIV头戴设备，或
   - 在Launcher中创建虚拟设备进行测试

3. **获取API凭证**
   - 访问：https://www.emotiv.com/my-account/cortex-apps/
   - 创建Cortex应用
   - 获取`Client ID`和`Client Secret`

### 3. 应用配置
```python
# 在代码中配置API凭证
your_app_client_id = 'YOUR_CLIENT_ID'
your_app_client_secret = 'YOUR_CLIENT_SECRET'
```

---

## 基础工作流程

### 1. 连接和授权流程
```python
def basic_workflow():
    """基础API工作流程"""
    
    # 1. 创建Cortex实例
    c = Cortex(client_id, client_secret, debug_mode=True)
    
    # 2. 打开WebSocket连接
    c.open()
    
    # 3. 自动执行以下步骤:
    #    - 检查访问权限 (has_access_right)
    #    - 请求访问授权 (request_access) 
    #    - 获取授权令牌 (authorize)
    #    - 查询可用设备 (query_headset)
    #    - 连接设备 (connect_headset)
    #    - 创建会话 (create_session)
```

### 2. 设备连接状态
```python
# 设置特定设备ID（可选）
c.set_wanted_headset(headset_id)

# 查询设备状态
c.query_headset()

# 连接设备
c.connect_headset(headset_id)

# 断开设备
c.disconnect_headset()
```

---

## 心理指令训练API

### 1. 训练类初始化
```python
class Train():
    def __init__(self, app_client_id, app_client_secret, **kwargs):
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=True, **kwargs)
        
        # 绑定事件回调
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(query_profile_done=self.on_query_profile_done)
        self.c.bind(load_unload_profile_done=self.on_load_unload_profile_done)
        self.c.bind(save_profile_done=self.on_save_profile_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_sys_data=self.on_new_sys_data)
        self.c.bind(inform_error=self.on_inform_error)
```

### 2. 开始训练流程
```python
def start_training(profile_name, actions, headset_id=''):
    """
    开始心理指令训练
    
    参数:
    - profile_name: 配置文件名称
    - actions: 要训练的动作列表，如['neutral', 'push', 'pull']
    - headset_id: 设备ID（可选）
    """
    
    t = Train(client_id, client_secret)
    t.start(profile_name, actions, headset_id)
```

### 3. 训练动作控制
```python
def train_mc_action(self, status):
    """
    控制心理指令训练
    
    参数:
    - status: 训练状态
      - 'start': 开始训练
      - 'accept': 接受训练结果
      - 'reject': 拒绝训练结果
      - 'erase': 删除训练数据
      - 'reset': 重置训练
    """
    action = self.actions[self.action_idx]
    self.c.train_request(detection='mentalCommand',
                        action=action,
                        status=status)
```

### 4. 配置文件管理
```python
# 加载配置文件
def load_profile(self, profile_name):
    self.c.setup_profile(profile_name, 'load')

# 卸载配置文件
def unload_profile(self, profile_name):
    self.c.setup_profile(profile_name, 'unload')

# 保存配置文件
def save_profile(self, profile_name):
    self.c.setup_profile(profile_name, 'save')

# 创建配置文件
def create_profile(self, profile_name):
    self.c.setup_profile(profile_name, 'create')
```

### 5. 训练事件回调处理
```python
def on_new_sys_data(self, *args, **kwargs):
    """处理训练系统事件"""
    data = kwargs.get('data')
    train_event = data[1]
    action = self.actions[self.action_idx]
    
    if train_event == 'MC_Succeeded':
        # 训练成功，可以接受或拒绝
        self.train_mc_action('accept')
    elif train_event == 'MC_Failed':
        # 训练失败，拒绝结果
        self.train_mc_action("reject")
    elif train_event == 'MC_Completed' or train_event == 'MC_Rejected':
        # 训练完成，进入下一个动作
        self.action_idx += 1
        self.train_mc_action('start')
```

---

## 数据流订阅

### 1. 可用数据流类型
```python
AVAILABLE_STREAMS = {
    'eeg': '原始脑电图数据',
    'mot': '运动数据',
    'dev': '设备数据（接触质量等）',
    'met': '性能指标',
    'pow': '频段功率',
    'com': '心理指令数据',
    'fac': '面部表情数据',
    'sys': '系统事件（训练事件）'
}
```

### 2. 订阅数据流
```python
def subscribe_data(self, streams):
    """
    订阅数据流
    
    参数:
    - streams: 数据流列表，如['com', 'dev', 'sys']
    """
    self.c.sub_request(streams)

# 示例
c.sub_request(['com'])  # 订阅心理指令数据
c.sub_request(['dev'])  # 订阅设备状态数据
c.sub_request(['sys'])  # 订阅系统事件（用于训练）
```

### 3. 数据处理回调
```python
# 心理指令数据回调
c.bind(new_com_data=self.on_new_com_data)

# 设备数据回调  
c.bind(new_dev_data=self.on_new_dev_data)

# 系统事件回调
c.bind(new_sys_data=self.on_new_sys_data)

def on_new_com_data(self, *args, **kwargs):
    """处理心理指令数据"""
    data = kwargs.get('data')
    # 处理实时心理指令检测结果
    
def on_new_dev_data(self, *args, **kwargs):
    """处理设备状态数据"""
    data = kwargs.get('data')
    # 处理接触质量等设备信息
```

---

## 会话和记录管理

### 1. 会话管理
```python
# 创建会话
c.create_session(auth_token, headset_id)

# 查询会话信息
c.query_session_info()

# 更新会话
c.update_session(session_id, status)
```

### 2. 数据记录
```python
# 开始记录
c.create_record(title="我的记录", description="描述")

# 注入标记
c.inject_marker_request(time, value="事件", label="标签")

# 停止记录
c.stop_record()

# 导出记录
c.export_record(folder="/path/to/export", 
               stream_types=['eeg', 'motion'], 
               export_format='CSV',
               record_ids=[record_id])
```

---

## 高级功能

### 1. 心理指令高级设置
```python
# 获取活跃动作
c.get_mental_command_active_action(profile_name)

# 设置活跃动作
c.set_mental_command_active_action(['push', 'pull'])

# 获取动作敏感度
c.get_mental_command_action_sensitivity(profile_name)

# 设置动作敏感度
c.set_mental_command_action_sensitivity(profile_name, [1, 5, 5])

# 获取脑图
c.get_mental_command_brain_map(profile_name)

# 获取训练阈值
c.get_mental_command_training_threshold(profile_name)
```

### 2. 设备控制
```python
# 刷新设备列表
c.refresh_headset_list()

# 控制设备
c.control_device(headset_id, command='connect')
c.control_device(headset_id, command='disconnect')
```

---

## 错误处理

### 1. 常见错误代码
```python
# cortex.py中定义的错误代码
ERR_PROFILE_ACCESS_DENIED = 104  # 配置文件访问被拒绝

def on_inform_error(self, *args, **kwargs):
    """错误处理回调"""
    error_data = kwargs.get('error_data')
    error_code = error_data['code']
    error_message = error_data['message']
    
    if error_code == cortex.ERR_PROFILE_ACCESS_DENIED:
        print(f"配置文件访问被拒绝: {error_message}")
        # 断开设备以便下次使用
        self.c.disconnect_headset()
```

### 2. 连接和授权问题
```python
def handle_authorization_issues():
    """处理常见授权问题"""
    
    # 1. 确保在EMOTIV Launcher中已登录
    # 2. 首次运行时需要在Launcher中手动批准访问
    # 3. 检查Client ID和Secret是否正确
    # 4. 确保设备已正确连接
```

---

## 代码示例

### 1. 完整的心理指令训练示例
```python
import cortex
from cortex import Cortex

def main():
    # API凭证
    your_app_client_id = 'YOUR_CLIENT_ID'
    your_app_client_secret = 'YOUR_CLIENT_SECRET'
    
    # 初始化训练
    t = Train(your_app_client_id, your_app_client_secret)
    
    # 配置文件名称
    profile_name = 'MyProfile'
    
    # 要训练的动作（必须先训练neutral）
    actions = ['neutral', 'push', 'pull']
    
    # 开始训练
    t.start(profile_name, actions)

if __name__ == '__main__':
    main()
```

### 2. 实时数据订阅示例
```python
class DataSubscriber:
    def __init__(self, client_id, client_secret):
        self.c = Cortex(client_id, client_secret)
        self.c.bind(new_com_data=self.on_mental_command_data)
        self.c.bind(new_dev_data=self.on_device_data)
        
    def start_stream(self):
        """开始数据流订阅"""
        self.c.open()
        # 连接建立后会自动订阅数据流
        
    def on_mental_command_data(self, *args, **kwargs):
        """处理心理指令数据"""
        data = kwargs.get('data')
        # 实时处理心理指令检测结果
        print(f"心理指令数据: {data}")
        
    def on_device_data(self, *args, **kwargs):
        """处理设备状态数据"""
        data = kwargs.get('data')
        # 监控设备接触质量等
        print(f"设备状态: {data}")
```

### 3. 配置文件管理示例
```python
class ProfileManager:
    def __init__(self, client_id, client_secret):
        self.c = Cortex(client_id, client_secret)
        self.c.bind(query_profile_done=self.on_profile_query)
        
    def list_profiles(self):
        """列出所有配置文件"""
        self.c.query_profile()
        
    def on_profile_query(self, *args, **kwargs):
        """处理配置文件查询结果"""
        profiles = kwargs.get('data')
        print(f"可用配置文件: {profiles}")
        
    def create_new_profile(self, name):
        """创建新配置文件"""
        self.c.setup_profile(name, 'create')
        
    def load_profile(self, name):
        """加载配置文件"""
        self.c.setup_profile(name, 'load')
```

---

## 最佳实践

### 1. 训练建议
- **总是先训练'neutral'动作**，这是所有其他动作的基础
- **保持良好的设备接触质量**，确保信号稳定
- **训练时保持专注**，每次训练持续8秒
- **在相同环境条件下进行训练和使用**

### 2. 开发建议
- **使用调试模式**（`debug_mode=True`）来查看详细的API交互
- **妥善处理异步事件**，所有API操作都是异步的
- **实现适当的错误处理**和重连机制
- **定期保存训练配置文件**

### 3. 性能优化
- **只订阅需要的数据流**，避免不必要的数据传输
- **合理设置数据处理频率**，避免阻塞主线程
- **及时释放资源**，关闭不需要的连接

---

## 相关资源

- **官方API文档**: https://emotiv.gitbook.io/cortex-api/
- **EMOTIV开发者门户**: https://www.emotiv.com/my-account/cortex-apps/
- **EMOTIV Launcher下载**: https://www.emotiv.com/products/emotiv-launcher
- **社区支持**: https://emotiv.zendesk.com/

---

*文档版本: 1.0*  
*最后更新: 2024年7月24日*
