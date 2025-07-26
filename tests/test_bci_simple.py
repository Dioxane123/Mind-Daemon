#!/usr/bin/env python3
"""
简化的BCI数据订阅测试
基于cortex-example参考实现
"""

import sys
import os
sys.path.append('src')

from src.mind_daemon.bci.cortex import Cortex
import csv
from datetime import datetime
import threading

class SimpleBCITest():
    def __init__(self, app_client_id, app_client_secret):
        print("SimpleBCITest __init__")
        self.c = Cortex(app_client_id, app_client_secret, debug_mode=True)
        self.c.bind(create_session_done=self.on_create_session_done)
        self.c.bind(new_data_labels=self.on_new_data_labels)
        self.c.bind(new_met_data=self.on_new_met_data)
        self.c.bind(new_pow_data=self.on_new_pow_data)
        self.c.bind(inform_error=self.on_inform_error)
        
        # CSV写入器
        self.csv_files = {}
        self.csv_writers = {}
        self.data_count = 0

    def start(self, streams, headset_id=''):
        self.streams = streams
        if headset_id != '':
            self.c.set_wanted_headset(headset_id)
        self.c.open()

    def sub(self, streams):
        self.c.sub_request(streams)

    def on_new_data_labels(self, *args, **kwargs):
        data = kwargs.get('data')
        stream_name = data['streamName']
        stream_labels = data['labels']
        print(f'{stream_name} labels are: {stream_labels}')
        
        # 创建CSV文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_{stream_name}_{timestamp}.csv"
        
        try:
            f = open(filename, 'w', newline='')
            writer = csv.writer(f)
            headers = ['time', 'timestamp'] + stream_labels
            writer.writerow(headers)
            self.csv_files[stream_name] = f
            self.csv_writers[stream_name] = writer
            print(f"创建CSV文件: {filename}")
        except Exception as e:
            print(f"创建CSV文件失败: {e}")

    def on_new_met_data(self, *args, **kwargs):
        data = kwargs.get('data')
        met_data = data['met']
        timestamp = data.get('time', 0)
        
        print(f'met data: {met_data}')
        
        # 写入CSV
        if 'met' in self.csv_writers:
            try:
                row = [datetime.now().isoformat(), timestamp] + met_data
                self.csv_writers['met'].writerow(row)
                self.csv_files['met'].flush()
                self.data_count += 1
                print(f"已写入met数据 #{self.data_count}")
            except Exception as e:
                print(f"写入met数据失败: {e}")

    def on_new_pow_data(self, *args, **kwargs):
        data = kwargs.get('data')
        pow_data = data['pow']
        timestamp = data.get('time', 0)
        
        print(f'pow data: {pow_data[:5]}... (长度: {len(pow_data)})')
        
        # 写入CSV
        if 'pow' in self.csv_writers:
            try:
                row = [datetime.now().isoformat(), timestamp] + pow_data
                self.csv_writers['pow'].writerow(row)
                self.csv_files['pow'].flush()
                print(f"已写入pow数据 #{self.data_count}")
            except Exception as e:
                print(f"写入pow数据失败: {e}")

    def on_create_session_done(self, *args, **kwargs):
        print('on_create_session_done - 开始订阅数据流')
        self.sub(self.streams)

    def on_inform_error(self, *args, **kwargs):
        error_data = kwargs.get('error_data')
        print(f"BCI错误: {error_data}")

    def close(self):
        print("关闭CSV文件...")
        for f in self.csv_files.values():
            if not f.closed:
                f.close()

def main():
    # 使用您的API凭证
    your_app_client_id = '0IWf9W3w12bZjkLPooA9nu8XXw6VxLNfwyg1AuZO'
    your_app_client_secret = 'ikjGYf5uGJmso4qhh5jsWt9VOsh1wQzehICQ3pAevtgCca36s67gp2Pkd5SqF00tn5mtAMAaMo5dAJSQMwp9Z1BKcZkoJ4P2ljnX9SwgpPZp3Da3z9MwegUTK60j1860'
    
    test = SimpleBCITest(your_app_client_id, your_app_client_secret)
    
    streams = ['met', 'pow']
    print(f"启动BCI测试，订阅数据流: {streams}")
    test.start(streams)
    
    try:
        print("BCI测试运行中，让它运行30秒...")
        print("按Ctrl+C停止")
        import time
        time.sleep(30)
    except KeyboardInterrupt:
        print("接收到停止信号")
    finally:
        test.close()
        print("BCI测试结束")

if __name__ == '__main__':
    main()