#!/usr/bin/env python3
"""
BCI模块测试脚本

测试Mind Daemon项目中的BCI模块功能：
1. 数据流服务的基本功能
2. 数据订阅和存储到CSV
3. 开发模式和生产模式

作者：Mind Daemon Test Suite
"""

import time
import sys
import os
import logging
from datetime import datetime

# 添加项目路径到系统路径
sys.path.insert(0, os.path.abspath('.'))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_bci_data_stream_service():
    """测试BCI数据流服务"""
    print("=" * 60)
    print("测试 BCI 数据流服务")
    print("=" * 60)
    
    from src.mind_daemon.bci import BCIDataStreamService
    
    # 创建数据流服务实例
    service = BCIDataStreamService()
    
    # 检查服务状态
    status = service.get_service_status()
    print(f"服务状态: {status}")
    
    # 添加数据回调
    data_count = {'count': 0}
    
    def data_callback(data):
        data_count['count'] += 1
        scores = data.get('scores', {})
        timestamp = data.get('timestamp')
        source = data.get('source', 'unknown')
        print(f"[回调 #{data_count['count']}] 时间: {timestamp[:19]} | 来源: {source}")
        print(f"   认知分数: At={scores.get('At', 0)} Ex={scores.get('Ex', 0)} Re={scores.get('Re', 0)} St={scores.get('St', 0)}")
        
        # 检查是否有BCI数据
        if 'met_data' in data:
            met_data = data.get('met_data', [])
            print(f"   Met数据长度: {len(met_data)}")
        if 'pow_data' in data:
            pow_data = data.get('pow_data', [])
            print(f"   Pow数据长度: {len(pow_data)}")
        
        print()
    
    # 注册回调
    service.add_data_callback(data_callback)
    
    try:
        # 启动服务
        print("启动BCI数据流服务...")
        service.start_service()
        
        # 获取当前数据
        current_data = service.get_current_data()
        print(f"当前数据: {current_data}")
        
        # 运行10秒测试，并自动停止
        print("运行10秒数据流测试（自动停止）...")
        start_time = time.time()
        test_duration = 10  # 测试持续时间（秒）
        
        while time.time() - start_time < test_duration:
            time.sleep(1)
            scores = service.get_current_scores()
            elapsed = int(time.time() - start_time)
            remaining = test_duration - elapsed
            print(f"[{elapsed}s] 当前分数: {scores} | 剩余时间: {remaining}s")
        
        print(f"\n✓ 测试完成 - 共收到 {data_count['count']} 个数据包，测试时长 {test_duration} 秒")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("停止服务...")
        service.stop_service()
        print("BCI数据流服务测试完成")

def test_bci_data_store():
    """测试BCI数据存储功能"""
    print("=" * 60)
    print("测试 BCI 数据存储功能")
    print("=" * 60)
    
    from src.mind_daemon.bci import AveragingLogger
    
    # 使用默认的API凭证进行测试（这里使用项目中的测试凭证）
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    print("注意：这个测试需要连接Emotiv设备才能获取真实数据")
    print("如果没有设备，测试将失败，这是正常现象")
    print()
    
    try:
        # 测试追加模式数据存储
        print("创建AveragingLogger实例（追加模式）...")
        logger_append = AveragingLogger(
            client_id, 
            client_secret, 
            interval_sec=2,  # 2秒间隔
            rolling_window_size=None  # 追加模式
        )
        
        print("尝试启动数据订阅（需要Emotiv设备）...")
        # 这里会失败如果没有设备，但我们可以测试初始化
        streams = ['met', 'pow']
        
        # 设置5秒超时自动停止
        import threading
        import signal
        
        timeout_duration = 5  # 超时时间（秒）
        print(f"设置 {timeout_duration} 秒超时自动停止...")
        
        def timeout_handler():
            time.sleep(timeout_duration)
            print(f"\n⏰ {timeout_duration}秒超时，自动关闭logger...")
            try:
                logger_append.close()
            except:
                pass
        
        timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
        timeout_thread.start()
        
        print("尝试启动数据订阅...")
        start_time = time.time()
        try:
            logger_append.start(streams)
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"数据订阅在 {elapsed:.1f} 秒后失败: {e}")
        
        # 等待超时线程完成
        timeout_thread.join(timeout=timeout_duration + 1)
        print("✓ 数据存储测试完成（超时停止）")
        
    except Exception as e:
        print(f"数据存储测试失败（这在没有Emotiv设备时是正常的）: {e}")
        logger.info("如果要进行完整测试，请确保：")
        logger.info("1. 已安装Emotiv Launcher")
        logger.info("2. 已连接Emotiv设备")
        logger.info("3. 已在Emotiv账户中授权应用")

def test_simple_subscription():
    """测试简单的数据订阅"""
    print("=" * 60)
    print("测试简单数据订阅")
    print("=" * 60)
    
    from src.mind_daemon.bci import Subcribe
    
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    try:
        print("创建Subcribe实例...")
        subscriber = Subcribe(client_id, client_secret)
        
        print("测试实例创建成功")
        print("注意：实际数据订阅需要Emotiv设备连接")
        
        # 测试实例方法是否存在
        print("检查必要方法...")
        methods = ['start', 'sub', 'unsub', 'on_new_met_data', 'on_new_pow_data']
        for method in methods:
            if hasattr(subscriber, method):
                print(f"✓ {method} 方法存在")
            else:
                print(f"✗ {method} 方法缺失")
        
    except Exception as e:
        print(f"简单订阅测试失败: {e}")

def main():
    """主测试函数"""
    print("Mind Daemon BCI模块测试")
    print(f"测试时间: {datetime.now()}")
    print("=" * 60)
    
    # 设置环境变量
    os.environ['DEV_MODE'] = 'true'  # 使用开发模式避免需要真实设备
    os.environ['DATA_DIR'] = './test_data'  # 设置测试数据目录
    
    # 设置总体超时时间
    total_timeout = 30  # 总测试时间不超过30秒
    start_time = time.time()
    
    try:
        print(f"⏱️  设置总体超时时间: {total_timeout} 秒")
        print()
        
        # 测试1: BCI数据流服务
        if time.time() - start_time < total_timeout:
            print(f"[{int(time.time() - start_time)}s] 开始测试1: BCI数据流服务")
            test_bci_data_stream_service()
        
        # 等待一下
        if time.time() - start_time < total_timeout:
            time.sleep(2)
        
        # 测试2: 简单数据订阅
        if time.time() - start_time < total_timeout:
            print(f"[{int(time.time() - start_time)}s] 开始测试2: 简单数据订阅")
            test_simple_subscription()
        
        # 测试3: 数据存储（需要设备，可能失败）
        # if time.time() - start_time < total_timeout:
        #     print(f"[{int(time.time() - start_time)}s] 开始测试3: 数据存储")
        #     test_bci_data_store()
        
        elapsed_total = time.time() - start_time
        print("=" * 60)
        print(f"✓ 所有测试完成 - 总耗时: {elapsed_total:.1f} 秒")
        print("=" * 60)
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️  测试被用户中断 (运行了 {elapsed:.1f} 秒)")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"测试过程中发生错误 (运行了 {elapsed:.1f} 秒): {e}")
        import traceback
        traceback.print_exc()
    
    # 确保程序能够正常退出
    print("\n程序即将退出...")
    time.sleep(1)

if __name__ == "__main__":
    main()