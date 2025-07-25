# 与RDK X5开发板通信的模块

## 已实现功能
- 在本机控制远程开发板启动ROS, Socket等等服务。
- 在config.py文件中配置连接到开发板的各个必要参数。
- 通过socket和开发板交互得到手势检测的结果。

## 文件介绍
- **[config.py](src/mind_daemon/detect/config.py)**: 配置远程连接到开发板的各个必要参数。
- **[socket_client.py](src/mind_daemon/detect/socket_client.py)**: 实现了本机通过socket和开发板通信，获取手势识别的结果。
- **[gesture_detector.py](src/mind_daemon/detect/gesture_detector.py)**: 实现了一系列方法，让开发者可以通过调用类方法实现操作远程开发板。

## 部分类与变量
### config.py
- remote_config: 连接开发板的必要参数
### gesture_detector.py
- GestureDetector
    - 实例化前务必传入remote_config
    - connect/disconnect: 连接/断开连接到开发板
    - start_services/stop_services: 启动/停止开发板上ros和socket服务
    - restart_services: 重启开发板上ros和socket服务
    - get_status: 检查开发板上各服务的状态
    - start_monitoring: 持续监控开发板上各个服务状态
    - stop_monitoring: 停止持续监控开发板上各个服务状态
### socket_client.py
- SocketClient
    - 不需要传入remote_config也可以实例化
    - connect/reconnect: 连接/重连开发板上socket服务
    - is_connect: 返回本机是否与开发板建立socket连接
    - wait_gesture: 从开发板上接收一个手势消息，若收到消息则关闭socket连接

## 通过socket从开发板收到的消息示例
{'timestamp': 1753429493.9387152, 'gestures': [{'name': 'ThumbUp', 'value': 2, 'confidence': 0.0}]}
