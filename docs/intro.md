# Mind Daemon项目的完整运行指南

## 🚀 快速开始

1. 环境设置

```python
# 确保在项目根目录
cd /Users/m3airmima0000/Mind-Daemon

# 安装依赖（如果还没有安装）
uv sync

# 验证安装
uv run python --version
```

2. 基础功能测试

```python
# 运行基础集成测试（推荐首次运行）
python3 demos/run_demo.py basic

# 或者使用完整的uv命令
uv run python demos/run_demo.py basic
```

3. CSV数据记录演示

```python
# 运行CSV数据记录演示
python3 demos/run_demo.py csv

# 手动运行CSV演示
python3 demos/csv_logging_demo.py
```

4. 完整系统运行

如果有Emotiv设备：
```python
# BCI状态分析器
python3 demos/run_demo.py bci

# Agent集成测试
python3 demos/run_demo.py agent

# 完整集成测试
python3 demos/run_demo.py integration
```

模拟模式（无设备）：
```python
# 运行所有可用的演示
python3 demos/run_demo.py all
```

## 📁 项目结构

```
Mind-Daemon/
├── src/mind_daemon/           # 主要源代码
│   ├── agent/                # Agent系统
│   ├── bci/                  # BCI数据处理
│   ├── detect/               # 手势检测
│   └── peripheral/           # 硬件控制
├── demos/                    # 演示程序
├── docs/                     # 文档
├── bci_data/                 # CSV数据输出
└── python/                   # Emotiv API示例
```

## 🎛️ 可用的演示模式

| 模式          | 命令                                    | 说明              |
|-------------|---------------------------------------|-----------------|
| basic       | python3 demos/run_demo.py basic       | 基础Agent功能测试     |
| csv         | python3 demos/run_demo.py csv         | CSV数据记录演示       |
| bci         | python3 demos/run_demo.py bci         | BCI状态分析器（需要设备）  |
| agent       | python3 demos/run_demo.py agent       | Agent决策系统（需要设备） |
| integration | python3 demos/run_demo.py integration | 完整集成测试          |
| all         | python3 demos/run_demo.py all         | 运行所有演示          |

## 🧠 BCI设备设置（可选）

如果要使用真实的BCI功能：

1. 安装EMOTIV Launcher
2. 获取Emotiv设备或创建虚拟设备
3. 从emotiv.com获取Client ID & Secret
4. 首次运行时授权应用

## 📊 数据输出

- CSV文件位置: bci_data/ 目录
- 文件格式: bci_data_[用户ID]_[会话ID]_[时间戳].csv
- 包含数据: EEG通道数据、认知状态、性能指标、事件标记

## 🛠 故障排除

如果遇到问题：

```python
# 重新同步依赖
uv sync

# 清理缓存
find . -name "__pycache__" -type d -exec rm -rf {} +

# 检查Python路径
uv run python -c "import sys; print(sys.path)"
```

现在你可以开始使用Mind Daemon系统了！推荐从 basic 模式开始测试。