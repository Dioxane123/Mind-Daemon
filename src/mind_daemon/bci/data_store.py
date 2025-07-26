from .cortex import Cortex
from .sub_data import Subcribe

import time
import csv
import os
from datetime import datetime
import threading
import numpy as np
from collections import deque  # 导入 deque
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class AveragingLogger(Subcribe):
    """
    一个灵活的记录器，支持两种模式：
    1. 追加模式 (默认): 将所有平均数据追加到CSV文件。
    2. 滚动模式: 只在CSV文件中保留最近N条数据。
    """
    def __init__(self, app_client_id, app_client_secret, interval_sec=5, rolling_window_size=None, **kwargs):
        super().__init__(app_client_id, app_client_secret, **kwargs)

        self.interval = interval_sec
        self.buffer_lock = threading.Lock()
        self.data_buffers = {}
        
        # --- 新增: 模式选择参数 ---
        self.rolling_window_size = rolling_window_size
        
        # --- 初始化两种模式所需的所有数据结构 ---
        # 滚动模式所需
        self.rolling_data_windows = {}
        self.csv_filepaths = {}
        self.csv_headers = {}
        # 追加模式所需
        self.csv_files = {}
        self.csv_writers = {}
        
        # 从环境变量获取日志目录配置
        base_log_dir = os.getenv('LOG_DIR', './logs')
        if not os.path.isabs(base_log_dir):
            base_log_dir = os.path.abspath(base_log_dir)
        
        # 根据模式选择不同的日志目录
        log_dir_name = f'rolling_logs_last_{self.rolling_window_size}' if self.rolling_window_size else 'append_logs'
        log_dir = os.path.join(base_log_dir, log_dir_name)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.log_dir = log_dir

        # 线程相关的初始化保持不变
        self.stop_event = threading.Event()
        self.ticker_thread = threading.Thread(target=self._ticker_loop)
        self.ticker_thread.daemon = True
        self.ticker_thread.start()

    def on_new_data_labels(self, *args, **kwargs):
        """
        根据所选模式，初始化数据结构和CSV文件。
        """
        data = kwargs.get('data')
        stream_name = data['streamName']
        labels = data['labels']
        
        with self.buffer_lock:
            self.data_buffers[stream_name] = []
        
        headers = ['time', 'sample_count'] + labels
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = f"{self.log_dir}/{stream_name}_{timestamp}.csv"

        # --- MODIFICATION: 根据模式选择初始化路径 ---
        if self.rolling_window_size is not None:
            # --- 滚动模式初始化 ---
            print(f"Initializing ROLLING mode for '{stream_name}' (last {self.rolling_window_size} entries)")
            self.rolling_data_windows[stream_name] = deque(maxlen=self.rolling_window_size)
            self.csv_filepaths[stream_name] = filepath
            self.csv_headers[stream_name] = headers
            try:
                with open(filepath, 'w', newline='') as f:
                    csv.writer(f).writerow(headers)
            except IOError as e:
                print(f"Error creating initial CSV for rolling mode: {e}")
        else:
            # --- 追加模式初始化 ---
            print(f"Initializing APPEND mode for '{stream_name}'")
            try:
                # 使用 'a' 模式追加，并永久持有文件句柄
                f = open(filepath, 'a', newline='')
                writer = csv.writer(f)
                # 仅当文件为空时写入表头
                if f.tell() == 0:
                    writer.writerow(headers)
                self.csv_files[stream_name] = f
                self.csv_writers[stream_name] = writer
            except IOError as e:
                print(f"Error creating CSV for append mode: {e}")

    def process_and_write_averages(self):
        """
        计算平均值，并根据所选模式写入数据。
        """
        with self.buffer_lock:
            for stream_name, buffer in self.data_buffers.items():
                if not buffer:
                    continue
                
                # 计算平均值的逻辑是共用的
                avg_values = np.array(buffer).mean(axis=0)
                new_row = [datetime.now().isoformat(), len(buffer)] + avg_values.tolist()
                
                # --- MODIFICATION: 根据模式选择写入路径 ---
                if self.rolling_window_size is not None:
                    # --- 滚动模式写入逻辑 ---
                    if stream_name in self.rolling_data_windows:
                        self.rolling_data_windows[stream_name].append(new_row)
                else:
                    # --- 追加模式写入逻辑 ---
                    if stream_name in self.csv_writers:
                        try:
                            self.csv_writers[stream_name].writerow(new_row)
                            self.csv_files[stream_name].flush() # 确保写入磁盘
                        except IOError as e:
                            print(f"Error during append write: {e}")
                
                buffer.clear()

        # 对于滚动模式，需要在锁之外重写文件
        if self.rolling_window_size is not None:
            for stream_name in self.rolling_data_windows:
                self._rewrite_csv(stream_name)

    def _rewrite_csv(self, stream_name):
        """辅助方法，仅用于滚动模式。"""
        filepath = self.csv_filepaths.get(stream_name)
        headers = self.csv_headers.get(stream_name)
        rolling_window = self.rolling_data_windows.get(stream_name)
        if not all([filepath, headers, rolling_window is not None]):
            return
        try:
            with open(filepath, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                writer.writerows(list(rolling_window))
        except IOError as e:
            print(f"Error rewriting CSV file {filepath}: {e}")

    def close(self):
        """
        根据所选模式，优雅地关闭记录器。
        """
        print("Closing logger...")
        self.stop_event.set()
        self.ticker_thread.join(timeout=2)
        print("Processing any remaining data and performing final write...")
        self.process_and_write_averages()

        # --- MODIFICATION: 只有在追加模式下才需要关闭文件 ---
        if self.rolling_window_size is None:
            print("Closing open file handles for append mode...")
            for f in self.csv_files.values():
                if not f.closed:
                    f.close()
        
        print("Logger closed.")

    # 其他辅助方法保持不变
    def _add_to_buffer(self, stream_name, data_points):
        with self.buffer_lock:
            if stream_name in self.data_buffers:
                self.data_buffers[stream_name].append(data_points)
    def _ticker_loop(self):
        while not self.stop_event.is_set():
            self.stop_event.wait(self.interval)
            if not self.stop_event.is_set():
                self.process_and_write_averages()
    def on_new_pow_data(self, *args, **kwargs):
        self._add_to_buffer('pow', kwargs.get('data')['pow'])
    def on_new_met_data(self, *args, **kwargs):
        self._add_to_buffer('met', kwargs.get('data')['met'])

def main_append_mode():
    your_app_client_id = '0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO'
    your_app_client_secret = 'ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860'
    logger = AveragingLogger(your_app_client_id, your_app_client_secret,
                             interval_sec=5, 
                             rolling_window_size=None)  # 设置为 None 以使用追加模式
    logger.start(['pow', 'met'])
    

def main_rolling_mode():
    your_app_client_id = '0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO'
    your_app_client_secret = 'ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860'
    
    
    # 设置 rolling_window_size=3 来激活滚动模式
    logger = AveragingLogger(your_app_client_id, your_app_client_secret, 
                             interval_sec=1, 
                             rolling_window_size=3)
    
    streams = ['pow', 'met']
    logger.start(streams)
    
if __name__ == "__main__":
    # main_append_mode()  # 如果需要使用追加模式，请取消注释
    # main_rolling_mode()  # 使用滚动模式
    main_append_mode()  # 使用追加模式
    # 注意：如果同时运行两个模式，可能会导致资源竞争问题，请确保在实际使用中只运行一个模式。