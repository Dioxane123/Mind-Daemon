# Mind Daemon MCP Services

此目录包含Mind Daemon系统的MCP (Model Context Protocol) 服务实现。

## 服务概览

### 1. halo_enhanced_server.py
**屏幕光晕控制服务**
- 控制屏幕边缘光晕效果
- 支持RGB颜色调节和亮度控制
- 认知状态预设颜色
- 脉冲效果支持

**工具 (Tools):**
- `activate_halo` - 激活光晕效果
- `deactivate_halo` - 关闭光晕效果
- `set_halo_color` - 设置光晕颜色
- `set_halo_brightness` - 设置亮度
- `pulse_halo` - 脉冲效果
- `toggle_halo` - 切换开关
- `get_halo_status` - 获取状态

### 2. music_control_server.py
**音乐播放控制服务**
- 播放专注/放松音乐
- 音量控制和淡入淡出
- 曲目切换和暂停恢复

**工具 (Tools):**
- `play_music` - 播放音乐
- `stop_music` - 停止播放
- `set_volume` - 设置音量
- `fade_volume` - 渐变音量
- `skip_track` - 切换曲目
- `pause_resume` - 暂停/恢复
- `get_music_status` - 获取状态

### 3. bci_data_server.py
**BCI数据处理服务**
- 45秒间隔数据平均处理
- CSV数据存储
- 实时认知状态分析

**工具 (Tools):**
- `start_bci_recording` - 开始BCI记录
- `stop_bci_recording` - 停止记录
- `get_current_state` - 获取当前状态
- `get_averaged_data` - 获取平均数据
- `export_csv_data` - 导出CSV数据

### 4. state_monitor_server.py
**状态监控和提醒服务**
- 15分钟间隔数据分析
- 智能状态评估和建议
- 12小时连续压力监控
- 自动休息提醒和邮件警报

**工具 (Tools):**
- `start_monitoring` - 开始监控
- `stop_monitoring` - 停止监控
- `analyze_now` - 立即分析
- `check_stress_alert` - 检查压力警报
- `add_alert_contact` - 添加联系人
- `get_recommendations` - 获取建议

## 使用方法

### 1. 安装依赖
```bash
pip install mcp
```

### 2. 启动服务
```bash
# 启动光晕控制服务
python src/mind_daemon/mcp/halo_enhanced_server.py

# 启动音乐控制服务
python src/mind_daemon/mcp/music_control_server.py

# 启动BCI数据服务
python src/mind_daemon/mcp/bci_data_server.py

# 启动状态监控服务
python src/mind_daemon/mcp/state_monitor_server.py
```

### 3. Claude Desktop配置
在Claude Desktop的配置文件中添加MCP服务：

```json
{
  "mcpServers": {
    "halo-enhanced": {
      "command": "python",
      "args": ["/path/to/Mind-Daemon/src/mind_daemon/mcp/halo_enhanced_server.py"]
    },
    "music-control": {
      "command": "python", 
      "args": ["/path/to/Mind-Daemon/src/mind_daemon/mcp/music_control_server.py"]
    },
    "bci-data": {
      "command": "python",
      "args": ["/path/to/Mind-Daemon/src/mind_daemon/mcp/bci_data_server.py"] 
    },
    "state-monitor": {
      "command": "python",
      "args": ["/path/to/Mind-Daemon/src/mind_daemon/mcp/state_monitor_server.py"]
    }
  }
}
```

## 数据流程

1. **BCI数据采集** - 实时采集脑电数据
2. **45秒平均** - 每45秒计算平均认知状态
3. **CSV存储** - 保存包含光晕和音乐信息的完整记录  
4. **15分钟分析** - 定期分析用户状态趋势
5. **智能提醒** - 根据分析结果提供休息建议
6. **12小时监控** - 检测长期压力状态并发送警报

## 集成方式

Mind Daemon的Agent系统可以通过MCP协议调用这些服务：

- 根据认知状态自动调节光晕颜色和亮度
- 智能选择和控制背景音乐
- 监控用户状态并提供个性化建议
- 在压力过大时自动触发休息提醒

## 安全说明

- 所有邮件警报功能都有占位实现，不会发送真实邮件
- CSV数据存储在本地，不会上传到外部服务
- MCP服务只在本地运行，保护用户隐私