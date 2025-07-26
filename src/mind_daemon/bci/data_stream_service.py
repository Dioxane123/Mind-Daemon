"""
BCI数据流服务 - 集成追加模式和滚动模式的数据订阅

功能：
- 同时运行追加模式（数据存储）和滚动模式（实时分析）
- 从BCI数据流计算认知分数
- 为WebSocket接口提供实时数据
- 与环境控制系统集成

作者：Mind Daemon Project
"""

import threading
import time
import json
import logging
import csv
from typing import Dict, Any, Optional, Callable, List
from collections import deque
from datetime import datetime
import os
import numpy as np

from .cortex import Cortex
from .sub_data import Subcribe
from .data_store import AveragingLogger
from ..utils.config import config
from ..analyzers.realtime_algorithms import get_algorithm_analyzer

logger = logging.getLogger(__name__)

class SimplifiedBCISubscriber(Subcribe):
    """
    简化的BCI数据订阅器
    
    基于参考实现，直接处理数据存储和回调
    """
    
    def __init__(self, app_client_id: str, app_client_secret: str, data_stream_service=None, **kwargs):
        super().__init__(app_client_id, app_client_secret, **kwargs)
        self.data_stream_service = data_stream_service
        
        # CSV存储
        self.csv_files = {}
        self.csv_writers = {}
        self.data_count = 0
        
        # 算法分析器
        self.algorithm_analyzer = get_algorithm_analyzer()
        self.pow_labels = []  # 存储pow数据标签
        
        # pow数据5秒平均值存储
        self.pow_buffer = deque(maxlen=25)  # 5秒的数据缓冲区(假设5Hz采样率)
        self.pow_5s_averages = []  # 存储5秒平均值
        self.pow_avg_csv_file = None
        self.pow_avg_csv_writer = None
    
    def on_new_data_labels(self, *args, **kwargs):
        """处理数据标签并初始化CSV存储"""
        data = kwargs.get('data')
        stream_name = data['streamName']
        stream_labels = data['labels']
        logger.info(f'{stream_name} labels: {stream_labels}')
        
        # 保存pow标签用于算法分析
        if stream_name == 'pow':
            self.pow_labels = stream_labels
            logger.info(f"保存pow标签用于算法分析: {len(stream_labels)}个频段")
            
            # 为pow数据5秒平均值创建单独的CSV文件
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                pow_avg_filename = os.path.join(data_dir, f"pow_5s_avg_{timestamp}.csv")
                
                self.pow_avg_csv_file = open(pow_avg_filename, 'w', newline='')
                self.pow_avg_csv_writer = csv.writer(self.pow_avg_csv_file)
                avg_headers = ['time', 'timestamp'] + [f'{label}_avg' for label in stream_labels]
                self.pow_avg_csv_writer.writerow(avg_headers)
                logger.info(f"创建pow 5秒平均值CSV文件: {pow_avg_filename}")
            except Exception as e:
                logger.error(f"创建pow平均值CSV文件失败: {e}")
        
        # 创建CSV文件用于数据存储
        try:
            # 创建数据目录
            data_dir = config.get('DATA_DIR', 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(data_dir, f"{stream_name}_{timestamp}.csv")
            
            f = open(filename, 'w', newline='')
            writer = csv.writer(f)
            headers = ['time', 'timestamp'] + stream_labels
            writer.writerow(headers)
            self.csv_files[stream_name] = f
            self.csv_writers[stream_name] = writer
            logger.info(f"创建CSV文件: {filename}")
        except Exception as e:
            logger.error(f"创建CSV文件失败: {e}")
        
    def on_new_met_data(self, *args, **kwargs):
        """处理性能指标数据"""
        data = kwargs.get('data')
        if data and self.data_stream_service:
            met_values = data.get('met', [])
            timestamp = data.get('time', 0)
            
            if met_values:
                # 更新数据流服务的数据
                with self.data_stream_service.data_lock:
                    self.data_stream_service.latest_met_data = met_values
                    self.data_stream_service._calculate_scores_from_met(met_values)
                
                # 创建数据包并通知WebSocket回调
                data_package = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'production_mode',
                    'stream_name': 'met',
                    'met_data': met_values,
                    'scores': self.data_stream_service.latest_scores.copy()
                }
                
                self.data_stream_service._notify_callbacks(data_package)
                
                # 直接写入CSV文件
                if 'met' in self.csv_writers:
                    try:
                        row = [datetime.now().isoformat(), timestamp] + met_values
                        self.csv_writers['met'].writerow(row)
                        self.csv_files['met'].flush()  # 确保数据立即写入磁盘
                        self.data_count += 1
                        if self.data_count % 10 == 0:  # 每10条记录日志一次
                            logger.info(f"已存储met数据 #{self.data_count}条 - 压力值: {met_values[6] if len(met_values) > 6 else 'N/A'}")
                    except Exception as e:
                        logger.error(f"写入met数据失败: {e}")
    
    def on_new_pow_data(self, *args, **kwargs):
        """处理频段功率数据"""
        data = kwargs.get('data')
        if data and self.data_stream_service:
            pow_values = data.get('pow', [])
            timestamp = data.get('time', 0)
            
            if pow_values:
                # 执行算法分析（如果有pow标签）
                algorithm_analysis = {}
                if self.pow_labels and len(pow_values) == len(self.pow_labels):
                    try:
                        algorithm_analysis = self.algorithm_analyzer.get_algorithm_analysis(pow_values, self.pow_labels)
                        logger.debug(f"算法分析完成: Clinical={algorithm_analysis.get('clinical_analysis', {}).get('state')}, "
                                   f"Cognitive={algorithm_analysis.get('cognitive_analysis', {}).get('state')}")
                    except Exception as e:
                        logger.error(f"算法分析失败: {e}")
                        algorithm_analysis = {'error': str(e)}
                
                # 更新数据流服务的数据
                with self.data_stream_service.data_lock:
                    self.data_stream_service.latest_pow_data = pow_values
                
                # 创建数据包并通知WebSocket回调
                data_package = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'production_mode',
                    'stream_name': 'pow',
                    'pow_data': pow_values,
                    'scores': self.data_stream_service.latest_scores.copy(),
                    'algorithm_analysis': algorithm_analysis  # 添加算法分析结果
                }
                
                self.data_stream_service._notify_callbacks(data_package)
                
                # 添加pow数据到缓冲区用于5秒平均值计算
                self.pow_buffer.append({
                    'timestamp': timestamp,
                    'datetime': datetime.now(),
                    'values': pow_values.copy()
                })
                
                # 每5秒计算一次平均值并存储
                if len(self.pow_buffer) >= 25:  # 假设5Hz采样率，5秒=25个样本
                    self._calculate_and_store_pow_average()
                
                # 直接写入CSV文件
                if 'pow' in self.csv_writers:
                    try:
                        row = [datetime.now().isoformat(), timestamp] + pow_values
                        self.csv_writers['pow'].writerow(row)
                        self.csv_files['pow'].flush()  # 确保数据立即写入磁盘
                        if self.data_count % 10 == 0:  # 每10条记录日志一次
                            logger.info(f"已存储pow数据 #{self.data_count}条")
                    except Exception as e:
                        logger.error(f"写入pow数据失败: {e}")
    
    def _calculate_and_store_pow_average(self):
        """计算并存储pow数据的5秒平均值"""
        try:
            if len(self.pow_buffer) < 5:  # 至少需要5个样本
                return
                
            # 获取最近5秒的数据
            current_time = datetime.now()
            recent_data = []
            
            for entry in reversed(self.pow_buffer):
                time_diff = (current_time - entry['datetime']).total_seconds()
                if time_diff <= 5.0:  # 5秒内的数据
                    recent_data.append(entry['values'])
                else:
                    break
            
            if len(recent_data) < 2:
                return
            
            # 计算平均值
            avg_values = np.mean(recent_data, axis=0).tolist()
            
            # 存储到CSV文件
            if self.pow_avg_csv_writer:
                try:
                    avg_row = [current_time.isoformat(), current_time.timestamp()] + avg_values
                    self.pow_avg_csv_writer.writerow(avg_row)
                    self.pow_avg_csv_file.flush()
                    logger.info(f"已存储pow 5秒平均值数据，样本数: {len(recent_data)}")
                except Exception as e:
                    logger.error(f"写入pow平均值数据失败: {e}")
                    
        except Exception as e:
            logger.error(f"计算pow平均值失败: {e}")
    
    def close(self):
        """关闭CSV文件"""
        logger.info("关闭BCI数据存储文件...")
        for stream_name, f in self.csv_files.items():
            if not f.closed:
                f.close()
                logger.info(f"已关闭{stream_name} CSV文件")
        
        # 关闭pow平均值CSV文件
        if self.pow_avg_csv_file and not self.pow_avg_csv_file.closed:
            self.pow_avg_csv_file.close()
            logger.info("已关闭pow 5秒平均值CSV文件")

class BCIDataStreamService:
    """
    BCI数据流服务
    
    管理BCI数据的订阅、存储和实时分析
    """
    
    def __init__(self, client_id: str = None, client_secret: str = None):
        """
        初始化BCI数据流服务
        
        Args:
            client_id: Emotiv客户端ID
            client_secret: Emotiv客户端密钥
        """
        # 配置
        self.client_id = client_id or config.get('EMOTIV_CLIENT_ID')
        self.client_secret = client_secret or config.get('EMOTIV_CLIENT_SECRET')
        self.dev_mode = config.get('DEV_MODE')
        
        # BCI数据订阅器
        self.bci_subscriber: Optional[SimplifiedBCISubscriber] = None  # 简化的BCI数据订阅器
        
        # 实时数据缓存
        self.latest_scores = {"At": 50, "Ex": 50, "Re": 50, "St": 50}
        self.latest_met_data = None
        self.latest_pow_data = None
        self.data_lock = threading.Lock()
        
        # 服务状态
        self.is_running = False
        self.service_thread: Optional[threading.Thread] = None
        
        # 数据回调
        self.data_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        logger.info(f"BCI数据流服务初始化完成 - Dev模式: {self.dev_mode}")
    
    def add_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """添加数据更新回调"""
        self.data_callbacks.append(callback)
    
    def remove_data_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """移除数据更新回调"""
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
    
    def _notify_callbacks(self, data: Dict[str, Any]):
        """通知所有回调函数"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error(f"数据回调通知失败: {e}")
    
    def start_service(self):
        """启动BCI数据流服务"""
        if self.is_running:
            logger.warning("BCI数据流服务已在运行")
            return
        
        if self.dev_mode:
            logger.info("开发模式：使用模拟BCI数据流")
            self._start_dev_mode()
        else:
            logger.info("生产模式：启动Emotiv BCI数据订阅")
            self._start_production_mode()
        
        self.is_running = True
        logger.info("BCI数据流服务已启动")
    
    def stop_service(self):
        """停止BCI数据流服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 停止BCI数据订阅器
        if self.bci_subscriber:
            try:
                # 关闭CSV文件
                self.bci_subscriber.close()
                # 关闭Cortex连接
                if hasattr(self.bci_subscriber, 'c') and self.bci_subscriber.c:
                    self.bci_subscriber.c.close()
                logger.info("BCI数据订阅器已停止")
            except Exception as e:
                logger.error(f"停止BCI数据订阅器失败: {e}")
        
        # 等待服务线程结束
        if self.service_thread and self.service_thread.is_alive():
            self.service_thread.join(timeout=3)
        
        logger.info("BCI数据流服务已停止")
    
    def _start_dev_mode(self):
        """启动开发模式（模拟数据）"""
        try:
            # 创建数据目录
            data_dir = config.get('DATA_DIR', 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            logger.info("开发模式：数据存储功能已禁用")
            logger.info("要测试BCI数据存储，请使用生产模式或运行test_bci_simple.py")
            
            logger.info("创建开发模式数据生成线程...")
            self.service_thread = threading.Thread(target=self._dev_mode_loop, daemon=True)
            self.service_thread.start()
            logger.info(f"开发模式线程已启动，线程活跃: {self.service_thread.is_alive()}")
            
        except Exception as e:
            logger.error(f"启动开发模式失败: {e}")
            raise
    
    def _start_production_mode(self):
        """启动生产模式（真实BCI数据）"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Emotiv API凭证未配置，无法启动生产模式")
        
        try:
            # 创建数据目录
            data_dir = config.get('DATA_DIR', 'data')
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            
            # 创建简化的BCI订阅器（集成数据存储和WebSocket回调）
            logger.info("创建简化BCI数据订阅器...")
            self.bci_subscriber = SimplifiedBCISubscriber(
                self.client_id,
                self.client_secret,
                data_stream_service=self
            )
            
            # 启动BCI数据订阅和存储
            logger.info("启动BCI数据订阅...")
            streams = ['met', 'pow']  # 订阅性能指标和频段功率数据
            self.bci_subscriber.start(streams)
            
            logger.info("BCI数据订阅和存储系统已启动")
            
            logger.info("所有BCI数据流已启动")
            
        except Exception as e:
            logger.error(f"启动生产模式失败: {e}")
            # 回退到开发模式
            logger.info("回退到开发模式")
            self._start_dev_mode()
    
    def _dev_mode_loop(self):
        """开发模式数据生成循环"""
        try:
            import random
            logger.info("开发模式数据生成循环已启动")
            logger.info(f"线程进入循环，self.is_running = {self.is_running}")
            
            loop_count = 0
            while self.is_running:
                loop_count += 1
                logger.info(f"开发模式循环 #{loop_count} 开始")
                
                # 生成模拟的met数据（performance metrics）
                logger.info("生成模拟met数据...")
                simulated_met_data = [
                    1,  # eng.isActive
                    random.uniform(0.3, 0.8),  # eng (engagement/attention)
                    1,  # exc.isActive
                    random.uniform(0.2, 0.7),  # exc (excitement)
                    random.uniform(0.0, 1.0),  # lex
                    1,  # str.isActive
                    random.uniform(0.1, 0.6),  # str (stress)
                    1,  # rel.isActive
                    random.uniform(0.4, 0.9),  # rel (relaxation)
                    1,  # int.isActive
                    random.uniform(0.3, 0.8),  # int (interest)
                    1,  # foc.isActive
                    random.uniform(0.4, 0.8),  # foc (focus)
                ]
                logger.info("met数据生成完成")
                
                # 生成模拟的pow数据（power bands）
                logger.info("生成模拟pow数据...")
                simulated_pow_data = [random.uniform(0.1, 2.0) for _ in range(20)]
                logger.info("pow数据生成完成")
                
                # 更新最新数据
                logger.info("更新最新数据...")
                with self.data_lock:
                    self.latest_met_data = simulated_met_data
                    self.latest_pow_data = simulated_pow_data
                    self._calculate_scores_from_met(simulated_met_data)
                logger.info("数据更新完成")
                
                # 创建数据包并通知回调
                logger.info("创建数据包...")
                data_package = {
                    'timestamp': datetime.now().isoformat(),
                    'source': 'dev_mode',
                    'met_data': simulated_met_data,
                    'pow_data': simulated_pow_data,
                    'scores': self.latest_scores.copy()
                }
                logger.info("数据包创建完成")
                
                # 通知所有回调函数
                if self.data_callbacks:
                    logger.info(f"通知 {len(self.data_callbacks)} 个回调函数 - 分数: At={self.latest_scores['At']} Ex={self.latest_scores['Ex']}")
                    self._notify_callbacks(data_package)
                else:
                    logger.info("没有注册的数据回调函数")
                
                # 开发模式不进行数据存储，仅用于WebSocket数据流测试
                
                logger.info(f"开发模式循环 #{loop_count} 完成，进入休眠...")
                # 模拟数据更新频率
                time.sleep(1)  # 1Hz更新
                logger.info(f"开发模式循环 #{loop_count} 休眠结束")
        
        except Exception as e:
            logger.error(f"开发模式数据生成循环严重错误: {e}")
            import traceback
            traceback.print_exc()
        
        logger.info("开发模式数据生成循环已结束")
    
    
    def _on_realtime_data_update(self, stream_name: str, data: List[float]):
        """实时数据更新回调（从滚动模式记录器）"""
        try:
            with self.data_lock:
                if stream_name == 'met':
                    self.latest_met_data = data
                    self._calculate_scores_from_met(data)
                elif stream_name == 'pow':
                    self.latest_pow_data = data
            
            # 创建数据包并通知回调
            data_package = {
                'timestamp': datetime.now().isoformat(),
                'source': 'production_mode',
                'stream_name': stream_name,
                'data': data,
                'scores': self.latest_scores.copy()
            }
            
            self._notify_callbacks(data_package)
            
        except Exception as e:
            logger.error(f"实时数据更新处理失败: {e}")
    
    def _calculate_scores_from_met(self, met_data: List[float]):
        """从met数据计算认知分数"""
        try:
            if len(met_data) >= 15:  # 确保有足够的数据
                # 根据met数据结构提取performance metrics并转换为0-100分数
                # met结构: time,timestamp,attention.isActive,attention,eng.isActive,eng,exc.isActive,exc,lex,str.isActive,str,rel.isActive,rel,int.isActive,int
                attention = met_data[3] * 100    # attention - 专注度  
                engagement = met_data[5] * 100   # eng - 参与度
                excitement = met_data[7] * 100   # exc - 兴奋度
                stress = met_data[10] * 100      # str - 压力值
                relaxation = met_data[12] * 100  # rel - 放松度
                
                # 更新分数（限制在0-100范围内）
                self.latest_scores = {
                    "At": max(0, min(100, int(attention))),       # Attention (使用attention字段)
                    "Ex": max(0, min(100, int(excitement))),      # Excitement  
                    "Re": max(0, min(100, int(relaxation))),      # Relaxation
                    "St": max(0, min(100, int(stress)))           # Stress
                }
                
                logger.debug(f"计算的认知分数: At={int(attention)}, Ex={int(excitement)}, Re={int(relaxation)}, St={int(stress)}")
                
        except (IndexError, TypeError, ValueError) as e:
            logger.warning(f"计算认知分数失败: {e}, met_data长度: {len(met_data) if met_data else 0}")
    
    def get_current_scores(self) -> Dict[str, int]:
        """获取当前认知分数"""
        with self.data_lock:
            return self.latest_scores.copy()
    
    def get_current_data(self) -> Dict[str, Any]:
        """获取当前所有数据"""
        with self.data_lock:
            return {
                'timestamp': datetime.now().isoformat(),
                'scores': self.latest_scores.copy(),
                'met_data': self.latest_met_data,
                'pow_data': self.latest_pow_data,
                'is_running': self.is_running,
                'dev_mode': self.dev_mode
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            'is_running': self.is_running,
            'dev_mode': self.dev_mode,
            'has_credentials': bool(self.client_id and self.client_secret),
            'bci_subscriber_active': self.bci_subscriber is not None,
            'callbacks_count': len(self.data_callbacks),
            'data_files_open': len(self.bci_subscriber.csv_files) if self.bci_subscriber else 0
        }

# 全局数据流服务实例
_data_stream_service: Optional[BCIDataStreamService] = None

def get_data_stream_service() -> BCIDataStreamService:
    """获取全局数据流服务实例"""
    global _data_stream_service
    if _data_stream_service is None:
        _data_stream_service = BCIDataStreamService()
    return _data_stream_service

if __name__ == "__main__":
    # 测试数据流服务
    service = BCIDataStreamService()
    
    def data_callback(data):
        scores = data.get('scores', {})
        print(f"收到数据: At={scores.get('At', 0)} Ex={scores.get('Ex', 0)} Re={scores.get('Re', 0)} St={scores.get('St', 0)}")
    
    service.add_data_callback(data_callback)
    
    try:
        service.start_service()
        print("数据流服务已启动，按Ctrl+C停止...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("正在停止服务...")
    finally:
        service.stop_service()