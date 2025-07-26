#!/usr/bin/env python3
"""
BCI CSV存储功能测试脚本

测试BCI模块的CSV数据存储功能:
1. 验证数据存储目录创建
2. 测试CSV文件生成
3. 验证数据写入格式
4. 测试自动停止和清理

作者：Mind Daemon Test Suite
"""

import time
import sys
import os
import logging
import csv
from datetime import datetime
import threading

# 添加项目路径到系统路径
sys.path.insert(0, os.path.abspath('.'))

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_real_bci_connection():
    """测试真实BCI设备连接和数据订阅"""
    print("=" * 60)
    print("测试真实BCI设备连接")
    print("=" * 60)
    
    from src.mind_daemon.bci import Subcribe
    
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"  
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    print("尝试连接真实BCI设备...")
    print("如果您有Emotiv设备并已安装Emotiv Launcher，将尝试真实连接")
    print("否则将显示连接失败，这是正常现象")
    print()
    
    connection_successful = False
    real_data_received = False
    data_count = 0
    
    try:
        # 创建订阅器
        subscriber = Subcribe(client_id, client_secret)
        
        # 重写数据处理方法来检测真实数据
        original_on_new_met_data = subscriber.on_new_met_data
        original_on_new_pow_data = subscriber.on_new_pow_data
        
        def enhanced_on_new_met_data(*args, **kwargs):
            nonlocal real_data_received, data_count
            data_count += 1
            real_data_received = True
            data = kwargs.get('data')
            print(f"✓ 接收到真实MET数据 #{data_count}: {data}")
            return original_on_new_met_data(*args, **kwargs)
        
        def enhanced_on_new_pow_data(*args, **kwargs):
            nonlocal real_data_received, data_count
            data_count += 1
            real_data_received = True
            data = kwargs.get('data')
            print(f"✓ 接收到真实POW数据 #{data_count}: 长度={len(data.get('pow', []))}")
            return original_on_new_pow_data(*args, **kwargs)
        
        # 替换数据处理方法
        subscriber.on_new_met_data = enhanced_on_new_met_data
        subscriber.on_new_pow_data = enhanced_on_new_pow_data
        
        # 设置超时
        timeout_duration = 10  # 10秒超时
        import threading
        
        connection_timeout = threading.Event()
        
        def timeout_handler():
            time.sleep(timeout_duration)
            print(f"\n⏰ {timeout_duration}秒连接超时")
            connection_timeout.set()
            try:
                if hasattr(subscriber, 'c') and subscriber.c:
                    subscriber.c.close()
            except:
                pass
        
        timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
        timeout_thread.start()
        
        print(f"开始连接（{timeout_duration}秒超时）...")
        start_time = time.time()
        
        try:
            # 尝试启动真实连接
            streams = ['met', 'pow']
            subscriber.start(streams)
            connection_successful = True
            
            # 等待数据或超时
            while not connection_timeout.is_set() and data_count < 5:
                time.sleep(0.5)
                elapsed = time.time() - start_time
                if elapsed > timeout_duration:
                    break
                print(f"等待数据... {elapsed:.1f}s", end='\r')
            
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n连接在 {elapsed:.1f}s 后失败: {e}")
        
        # 报告结果
        print(f"\n{'='*40}")
        print("BCI设备连接测试结果:")
        print(f"连接尝试: {'成功' if connection_successful else '失败'}")
        print(f"真实数据接收: {'是' if real_data_received else '否'}")
        print(f"数据包数量: {data_count}")
        
        if real_data_received:
            print("✅ 检测到真实BCI数据流！")
            return True
        else:
            print("❌ 未检测到真实BCI数据流（使用模拟数据）")
            return False
            
    except Exception as e:
        print(f"BCI连接测试异常: {e}")
        return False

def test_csv_storage_with_real_data():
    """测试真实BCI数据的CSV存储功能"""
    print("=" * 60)
    print("测试真实BCI数据CSV存储功能")
    print("=" * 60)
    
    from src.mind_daemon.bci import BCIDataStreamService
    
    # 使用.env中定义的数据目录
    from dotenv import load_dotenv
    load_dotenv()
    
    data_dir = os.getenv('DATA_DIR', './data')
    if not os.path.isabs(data_dir):
        data_dir = os.path.abspath(data_dir)
    
    print(f"数据存储目录: {data_dir}")
    print(f"目录是否存在: {os.path.exists(data_dir)}")
    
    # 确保使用生产模式
    os.environ['DEV_MODE'] = 'false'
    os.environ['DATA_DIR'] = data_dir
    
    # 创建目录
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"✓ 创建数据目录: {data_dir}")
    
    # 测试凭证
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    try:
        print("创建BCI数据流服务（生产模式）...")
        service = BCIDataStreamService(client_id, client_secret)
        
        # 检查在数据目录创建前的文件数量
        initial_files = []
        if os.path.exists(data_dir):
            initial_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        print(f"初始CSV文件数量: {len(initial_files)}")
        
        # 添加数据回调来监控数据流
        data_received = {'count': 0, 'real_data': False}
        
        def data_monitor_callback(data):
            data_received['count'] += 1
            source = data.get('source', 'unknown')
            if source == 'production_mode':
                data_received['real_data'] = True
            
            if data_received['count'] % 5 == 0:  # 每5个数据包报告一次
                print(f"  数据包 #{data_received['count']} - 来源: {source}")
        
        service.add_data_callback(data_monitor_callback)
        
        print("启动真实BCI数据流服务...")
        service.start_service()
        
        # 等待数据收集
        test_duration = 10  # 测试10秒
        print(f"收集数据 {test_duration} 秒...")
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            elapsed = int(time.time() - start_time)
            remaining = test_duration - elapsed
            print(f"[{elapsed}s] 收集中... 剩余: {remaining}s", end='\r')
            time.sleep(1)
        
        print(f"\n✓ 数据收集完成")
        
        # 停止服务
        print("停止BCI数据流服务...")
        service.stop_service()
        
        # 检查生成的CSV文件
        print(f"\n验证CSV文件生成（目录: {data_dir}）...")
        final_files = []
        if os.path.exists(data_dir):
            final_files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]
        
        new_files = [f for f in final_files if f not in initial_files]
        
        print(f"新生成的CSV文件数量: {len(new_files)}")
        
        for csv_file in new_files:
            file_path = os.path.join(data_dir, csv_file)
            file_size = os.path.getsize(file_path)
            print(f"✓ {csv_file} (大小: {file_size} bytes)")
            
            # 验证文件内容
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                    print(f"  - 行数: {len(lines)}")
                    if len(lines) > 1:
                        print(f"  - 表头: {lines[0].strip()}")
                        print(f"  - 首行数据: {lines[1].strip()[:100]}...")
            except Exception as e:
                print(f"  - 读取失败: {e}")
        
        # 报告结果
        print(f"\n{'='*40}")
        print("真实数据CSV存储测试结果:")
        print(f"数据包接收: {data_received['count']} 个")
        print(f"真实数据流: {'是' if data_received['real_data'] else '否'}")
        print(f"CSV文件生成: {len(new_files)} 个")
        print(f"数据目录: {data_dir}")
        
        if len(new_files) > 0 and data_received['real_data']:
            print("✅ 真实BCI数据CSV存储功能正常！")
        else:
            print("⚠️ CSV存储可能未正常工作（检查设备连接）")
            
    except Exception as e:
        logger.error(f"真实数据CSV存储测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_csv_storage_with_simplified_subscriber():
    """测试简化BCI订阅器的CSV存储功能"""
    print("=" * 60)
    print("测试 BCI CSV 存储功能（使用简化订阅器）")
    print("=" * 60)
    
    from src.mind_daemon.bci import BCIDataStreamService
    from src.mind_daemon.bci.data_stream_service import SimplifiedBCISubscriber
    
    # 配置测试环境
    test_data_dir = './test_data_csv'
    os.environ['DATA_DIR'] = test_data_dir
    os.environ['DEV_MODE'] = 'false'  # 使用生产模式来测试CSV存储
    
    # 创建测试目录
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)
        print(f"创建测试数据目录: {test_data_dir}")
    
    # 测试凭证
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    try:
        print("创建BCI数据流服务...")
        service = BCIDataStreamService(client_id, client_secret)
        
        print("注意：此测试模拟CSV存储功能，不需要真实BCI设备")
        print()
        
        # 创建模拟的SimplifiedBCISubscriber来测试CSV功能
        print("创建简化BCI订阅器实例...")
        subscriber = SimplifiedBCISubscriber(
            client_id, 
            client_secret, 
            data_stream_service=service
        )
        
        # 模拟数据标签初始化（这通常在设备连接时发生）
        print("模拟数据标签初始化...")
        
        # 模拟met数据标签
        met_labels_data = {
            'streamName': 'met',
            'labels': ['eng.isActive', 'eng', 'exc.isActive', 'exc', 'lex', 
                      'str.isActive', 'str', 'rel.isActive', 'rel', 
                      'int.isActive', 'int', 'foc.isActive', 'foc']
        }
        subscriber.on_new_data_labels(data=met_labels_data)
        
        # 模拟pow数据标签  
        pow_labels_data = {
            'streamName': 'pow',
            'labels': ['AF3/theta', 'AF3/alpha', 'AF3/betaL', 'AF3/betaH', 'AF3/gamma',
                      'T7/theta', 'T7/alpha', 'T7/betaL', 'T7/betaH', 'T7/gamma',
                      'Pz/theta', 'Pz/alpha', 'Pz/betaL', 'Pz/betaH', 'Pz/gamma',
                      'T8/theta', 'T8/alpha', 'T8/betaL', 'T8/betaH', 'T8/gamma',
                      'AF4/theta', 'AF4/alpha', 'AF4/betaL', 'AF4/betaH', 'AF4/gamma']
        }
        subscriber.on_new_data_labels(data=pow_labels_data)
        
        print("✓ 数据标签初始化完成")
        
        # 等待一下让CSV文件创建
        time.sleep(1)
        
        # 检查CSV文件是否已创建
        print("\n检查CSV文件创建...")
        csv_files = []
        for filename in os.listdir(test_data_dir):
            if filename.endswith('.csv'):
                csv_files.append(filename)
                print(f"✓ 发现CSV文件: {filename}")
        
        if not csv_files:
            print("⚠️ 未发现CSV文件，这可能是正常的（需要数据写入才创建）")
        
        # 模拟数据写入
        print("\n开始模拟数据写入测试...")
        test_duration = 5  # 测试5秒
        data_count = 0
        
        import random
        start_time = time.time()
        
        while time.time() - start_time < test_duration:
            # 生成模拟met数据
            simulated_met_data = {
                'met': [1, random.uniform(0.3, 0.8), 1, random.uniform(0.2, 0.7), 
                       random.uniform(0.0, 1.0), 1, random.uniform(0.1, 0.6),
                       1, random.uniform(0.4, 0.9), 1, random.uniform(0.3, 0.8),
                       1, random.uniform(0.4, 0.8)],
                'time': time.time()
            }
            subscriber.on_new_met_data(data=simulated_met_data)
            
            # 生成模拟pow数据
            simulated_pow_data = {
                'pow': [random.uniform(0.1, 2.0) for _ in range(25)],
                'time': time.time()
            }
            subscriber.on_new_pow_data(data=simulated_pow_data)
            
            data_count += 1
            elapsed = int(time.time() - start_time)
            remaining = test_duration - elapsed
            print(f"[{elapsed}s] 写入第 {data_count} 组数据 | 剩余: {remaining}s", end='\r')
            
            time.sleep(0.2)  # 5Hz数据频率
        
        print(f"\n✓ 模拟数据写入完成 - 总共写入 {data_count} 组数据")
        
        # 关闭订阅器以确保文件正确关闭
        print("\n关闭订阅器...")
        subscriber.close()
        print("✓ 订阅器已关闭")
        
        # 验证CSV文件内容
        print("\n验证CSV文件内容...")
        final_csv_files = []
        for filename in os.listdir(test_data_dir):
            if filename.endswith('.csv'):
                final_csv_files.append(filename)
        
        for csv_file in final_csv_files:
            file_path = os.path.join(test_data_dir, csv_file)
            try:
                with open(file_path, 'r') as f:
                    reader = csv.reader(f)
                    rows = list(reader)
                    
                if len(rows) > 0:
                    headers = rows[0]
                    data_rows = rows[1:]
                    print(f"✓ {csv_file}:")
                    print(f"  - 列标题: {len(headers)} 个")
                    print(f"  - 数据行: {len(data_rows)} 行")
                    print(f"  - 前3个列标题: {headers[:3]}")
                    
                    if len(data_rows) > 0:
                        print(f"  - 第一行数据: {data_rows[0][:3]}...")
                        print(f"  - 最后一行数据: {data_rows[-1][:3]}...")
                else:
                    print(f"⚠️ {csv_file}: 文件为空")
                    
            except Exception as e:
                print(f"❌ 读取 {csv_file} 失败: {e}")
        
        print(f"\n✓ CSV存储功能测试完成")
        
    except Exception as e:
        logger.error(f"CSV存储测试失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理测试文件
        print("\n清理测试文件...")
        try:
            for filename in os.listdir(test_data_dir):
                if filename.endswith('.csv'):
                    file_path = os.path.join(test_data_dir, filename)
                    file_size = os.path.getsize(file_path)
                    print(f"保留测试文件: {filename} (大小: {file_size} bytes)")
            print("✓ 测试文件已保留以供检查")
        except Exception as e:
            print(f"清理时出错: {e}")

def test_averaging_logger_append_mode():
    """测试AveragingLogger的追加模式"""
    print("=" * 60)
    print("测试 AveragingLogger 追加模式")
    print("=" * 60)
    
    from src.mind_daemon.bci import AveragingLogger
    
    test_data_dir = './test_logs_append'
    os.environ['LOG_DIR'] = test_data_dir
    
    # 创建测试目录
    if not os.path.exists(test_data_dir):
        os.makedirs(test_data_dir)
    
    client_id = "0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO"
    client_secret = "ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860"
    
    try:
        print("创建AveragingLogger实例（追加模式）...")
        logger_instance = AveragingLogger(
            client_id,
            client_secret,
            interval_sec=2,  # 2秒计算一次平均值
            rolling_window_size=None  # 追加模式
        )
        
        # 设置3秒超时
        timeout_duration = 3
        stop_flag = threading.Event()
        
        def timeout_handler():
            time.sleep(timeout_duration)
            print(f"\n⏰ {timeout_duration}秒超时，关闭logger...")
            stop_flag.set()
            try:
                logger_instance.close()
            except:
                pass
        
        timeout_thread = threading.Thread(target=timeout_handler, daemon=True)
        timeout_thread.start()
        
        print(f"设置 {timeout_duration} 秒超时...")
        print("注意：由于没有真实BCI设备，连接会失败，这是正常现象")
        
        try:
            # 尝试启动（会因为没有设备而失败）
            streams = ['met', 'pow']
            logger_instance.start(streams)
        except Exception as e:
            print(f"预期的连接失败: {e}")
        
        # 等待超时
        stop_flag.wait(timeout_duration + 1)
        
        print("✓ AveragingLogger测试完成")
        
    except Exception as e:
        print(f"AveragingLogger测试失败: {e}")

def main():
    """主测试函数"""
    print("Mind Daemon BCI CSV存储功能测试")
    print(f"测试时间: {datetime.now()}")
    print("=" * 60)
    
    total_timeout = 20  # 总测试时间
    start_time = time.time()
    
    try:
        print(f"⏱️  设置总体超时时间: {total_timeout} 秒")
        print()
        
        # 测试1: 真实BCI设备连接测试
        has_real_bci = False
        if time.time() - start_time < total_timeout:
            print(f"[{int(time.time() - start_time)}s] 开始测试1: 真实BCI设备连接")
            has_real_bci = test_real_bci_connection()
        
        # 测试2: CSV存储功能（优先测试真实数据，然后模拟数据）
        if time.time() - start_time < total_timeout:
            print(f"\n[{int(time.time() - start_time)}s] 开始测试2: CSV存储功能")
            if has_real_bci:
                print("✅ 检测到真实BCI设备，将使用真实数据测试CSV存储")
                test_csv_storage_with_real_data()
            else:
                print("ℹ️  未检测到真实BCI设备，将使用模拟数据测试CSV存储")
                test_csv_storage_with_simplified_subscriber()
        
        # 测试3: AveragingLogger
        if time.time() - start_time < total_timeout:
            print(f"\n[{int(time.time() - start_time)}s] 开始测试3: AveragingLogger")
            test_averaging_logger_append_mode()
        
        elapsed_total = time.time() - start_time
        print("=" * 60)
        print(f"✓ 所有CSV存储测试完成 - 总耗时: {elapsed_total:.1f} 秒")
        print("=" * 60)
        
    except KeyboardInterrupt:
        elapsed = time.time() - start_time
        print(f"\n⚠️  测试被用户中断 (运行了 {elapsed:.1f} 秒)")
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"测试过程中发生错误 (运行了 {elapsed:.1f} 秒): {e}")
        import traceback
        traceback.print_exc()
    
    print("\n程序即将退出...")
    time.sleep(1)

if __name__ == "__main__":
    main()