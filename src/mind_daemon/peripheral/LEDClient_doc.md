# LED控制类使用说明

## 概述

`LEDClient` 类提供了与远程LED开发板进行通信的完整接口。该类将原本的命令行交互功能封装成了方法，使其可以更方便地在代码中使用。

## 类初始化

```python
from src.mind_daemon.peripheral.light import LEDClient

# 创建LED客户端实例
client = LEDClient(host="192.168.1.100", port=8898)
```

### 参数
- `host`: LED开发板的IP地址
- `port`: 通信端口，默认为8898

## 连接管理

### `connect()`
连接到远程LED服务器

```python
if client.connect():
    print("连接成功")
else:
    print("连接失败")
```

### `disconnect()`
断开与服务器的连接

```python
client.disconnect()
```

## 基础LED控制方法

### `set_color_hex(color)`
使用十六进制颜色值设置LED颜色

```python
# 设置为红色
response = client.set_color_hex("#FF0000")

# 设置为绿色
response = client.set_color_hex("#00FF00")

# 设置为蓝色
response = client.set_color_hex("#0000FF")
```

### `set_color_name(color_name)`
使用颜色名称设置LED颜色

```python
# 支持的颜色名称
colors = ["red", "green", "blue", "white", "yellow", "cyan", 
          "magenta", "orange", "purple", "pink", "lime", "off"]

response = client.set_color_name("red")
response = client.set_color_name("off")  # 关闭LED
```

### `change_light(r, g, b)`
使用RGB值设置LED颜色

```python
# 设置RGB值 (0-255)
response = client.change_light(255, 0, 0)    # 红色
response = client.change_light(0, 255, 0)    # 绿色
response = client.change_light(0, 0, 255)    # 蓝色
response = client.change_light(255, 255, 255) # 白色
```

### `set_brightness(brightness)`
设置LED亮度

```python
# 设置亮度 (0-100)
response = client.set_brightness(50)   # 50%亮度
response = client.set_brightness(100)  # 100%亮度
response = client.set_brightness(10)   # 10%亮度
```

## 特效控制方法

### `start_breathing()`
开启呼吸灯效果

```python
response = client.start_breathing()
```

### `stop_breathing()`
关闭呼吸灯效果

```python
response = client.stop_breathing()
```

## 状态查询方法

### `get_status()`
获取LED当前状态

```python
response = client.get_status()
if response['status'] == 'success':
    print("LED状态:", response['data'])
```

### `ping()`
测试与服务器的连接

```python
response = client.ping()
if response['status'] == 'success':
    print("连接正常")
```

## 演示方法

### `rainbow_demo()`
执行彩虹颜色演示

```python
client.rainbow_demo()  # 自动循环显示彩虹色
```

### `brightness_demo()`
执行亮度变化演示

```python
client.brightness_demo()  # 自动演示亮度渐变效果
```

## 交互模式

### `run_interactive_mode()`
运行交互式命令行模式

```python
client.run_interactive_mode()
```

此方法会启动一个交互式命令行界面，支持以下命令：
- `hex #RRGGBB` - 设置十六进制颜色
- `color 颜色名` - 设置颜色名称
- `rgb R G B` - 设置RGB值
- `bright 数值` - 设置亮度
- `breath` - 开启呼吸灯
- `stop` - 关闭呼吸灯
- `status` - 获取状态
- `ping` - 测试连接
- `demo rainbow` - 彩虹演示
- `demo bright` - 亮度演示
- `quit` - 退出

## 响应处理

### `print_response(response)`
美化打印服务器响应

```python
response = client.set_color_hex("#FF0000")
client.print_response(response)
```

## 完整使用示例

```python
from src.mind_daemon.peripheral.light import LEDClient

# 创建客户端
client = LEDClient("192.168.1.100")

try:
    # 连接到服务器
    if client.connect():
        # 设置为红色
        response = client.set_color_hex("#FF0000")
        client.print_response(response)
        
        # 设置亮度为50%
        response = client.set_brightness(50)
        client.print_response(response)
        
        # 开启呼吸灯
        response = client.start_breathing()
        client.print_response(response)
        
        # 等待一段时间
        import time
        time.sleep(5)
        
        # 关闭呼吸灯
        response = client.stop_breathing()
        client.print_response(response)
        
        # 执行彩虹演示
        client.rainbow_demo()
        
finally:
    # 断开连接
    client.disconnect()
```

## 在Mind Daemon系统中的应用

在Mind Daemon的BCI系统中，可以根据用户的专注状态来控制LED：

```python
# 根据专注度调整LED颜色
def adjust_led_by_focus(client, focus_level):
    if focus_level > 0.8:
        # 高专注度 - 绿色
        client.set_color_name("green")
    elif focus_level > 0.5:
        # 中等专注度 - 黄色
        client.set_color_name("yellow")
    else:
        # 低专注度 - 红色呼吸灯
        client.set_color_name("red")
        client.start_breathing()

# 休息模式 - 柔和蓝色
def relax_mode(client):
    client.set_color_name("blue")
    client.set_brightness(30)
    client.start_breathing()
```

## 错误处理

所有方法都会返回包含状态信息的字典：

```python
response = client.set_color_hex("#FF0000")

if response['status'] == 'success':
    print("操作成功:", response['message'])
elif response['status'] == 'error':
    print("操作失败:", response['message'])
```

## 注意事项

1. 使用前必须先调用 `connect()` 方法连接到服务器
2. 使用完毕后建议调用 `disconnect()` 断开连接
3. RGB值范围为0-255，亮度值范围为0-100
4. 十六进制颜色值必须以#开头，如"#FF0000"
5. 网络异常时方法会返回错误状态，应进行适当的错误处理