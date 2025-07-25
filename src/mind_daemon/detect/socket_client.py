"""Socket communication with main system - placeholder."""

from config import remote_config

import socket
import json
import time
try:
    from loguru import logger
    islogger = True
except:
    islogger = False

class SocketClient:
    """Handles socket communication between detection module and main system."""
    
    def __init__(self, host: str = remote_config.host, port: int = 8888):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
            
    def connect(self):
        """Connect to main system via socket."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            if islogger:
                logger.info("成功连接到RDK开发板")
            return True
        except Exception as e:
            self.connected = False
            if islogger:
                logger.error(f"连接客户端发生错误：{e}")
            else:
                print(f"连接客户端发生错误:{e}")
            return False
        

    def wait_gesture(self):
        """Receive gesture message by socket. Disconnects after receiving one message."""
        if not self.is_connected():
            if islogger:
                logger.warning("未连接到服务器，无法接收手势数据。")
            else:
                print("未连接到服务器，无法接收手势数据")
            return None
            
        try:
            # 接收消息长度（4字节大端序）
            length_data = self._recv_exactly(4)
            if not length_data:
                return None
                
            message_length = int.from_bytes(length_data, byteorder='big')
            
            # 接收完整消息
            message_data = self._recv_exactly(message_length)
            if not message_data:
                return None
                
            # 解析JSON消息
            message_str = message_data.decode('utf-8')
            message = json.loads(message_str)
            
            if islogger:
                logger.info(f"接收到手势数据: {message}")
            
            # 收到消息后立即断开连接
            self.disconnect()
            
            return message
            
        except json.JSONDecodeError as e:
            if islogger:
                logger.error(f"JSON解析错误: {e}")
            else:
                print(f"JSON解析错误: {e}")
            # 出错时也断开连接
            self.disconnect()
            return None
        except Exception as e:
            self.connected = False
            if islogger:
                logger.error(f"接收手势数据失败: {e}")
            else:
                print(f"接收手势数据失败: {e}")
            # 出错时也断开连接
            self.disconnect()
            return None
    
    def _recv_exactly(self, size):
        """Helper method to receive exactly 'size' bytes."""
        data = b''
        while len(data) < size:
            try:
                chunk = self.socket.recv(size - len(data))
                if not chunk:
                    # 连接已关闭
                    self.connected = False
                    return None
                data += chunk
            except socket.timeout:
                if islogger:
                    logger.warning("接收数据超时")
                return None
            except Exception as e:
                self.connected = False
                if islogger:
                    logger.error(f"接收数据时发生错误: {e}")
                else:
                    print(f"接收数据时发生错误: {e}")
                return None
        return data
    
    def disconnect(self):
        """Disconnect from main system."""
        try:
            if self.socket:
                self.socket.close()
                self.socket = None
            self.connected = False
            if islogger:
                logger.info("已断开与服务器的连接")
        except Exception as e:
            if islogger:
                logger.error(f"断开连接时发生错误: {e}")
            else:
                print(f"断开连接时发生错误: {e}")
    
    def is_connected(self):
        """Check if socket is connected."""
        return self.connected and self.socket is not None
    
    def reconnect(self, max_retries: int = 3):
        """Attempt to reconnect to the server."""
        for attempt in range(max_retries):
            if islogger:
                logger.info(f"尝试重连 ({attempt + 1}/{max_retries})")
            else:
                print(f"尝试重连 ({attempt + 1}/{max_retries})")
                
            if self.connect():
                return True
            time.sleep(1)
        
        if islogger:
            logger.error("重连失败，已达到最大重试次数")
        else:
            print("重连失败，已达到最大重试次数")
        return False

if __name__ == "__main__":
    socket_client = SocketClient()
    try:
        socket_client.connect()
    except:
        socket_client.reconnect()
    
    for _ in range(5):
        if socket_client.is_connected():
            message = socket_client.wait_gesture()
            socket_client.connect()
