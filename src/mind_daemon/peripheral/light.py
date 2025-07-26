#!/usr/bin/env python3
import socket
import json
import sys
import time
import os

from dotenv import load_dotenv
load_dotenv()

HOST = os.getenv('RDK_HOST')

class LEDClient:
    def __init__(self, host, port=8898):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
    
    def connect(self):
        """连接到远程LED服务器"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            self.connected = True
            print(f"✓ 已连接到LED服务器: {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            self.socket.close()
            self.connected = False
            print("已断开连接")
    
    def send_command(self, command):
        """发送命令到服务器"""
        if not self.connected:
            return {"status": "error", "message": "未连接到服务器"}
        
        try:
            # 发送JSON命令
            command_json = json.dumps(command)
            self.socket.send(command_json.encode('utf-8'))
            
            # 接收响应
            response = self.socket.recv(1024).decode('utf-8')
            return json.loads(response)
            
        except Exception as e:
            return {"status": "error", "message": f"通信错误: {str(e)}"}
    
    def set_color_hex(self, color):
        """设置十六进制颜色"""
        command = {
            "command": "set_color_hex",
            "color": color
        }
        return self.send_command(command)
    
    def set_color_name(self, color_name):
        """设置颜色名称"""
        command = {
            "command": "set_color_name",
            "color": color_name
        }
        return self.send_command(command)
    
    def change_light(self, r, g, b):
        """设置RGB值 (0-255)"""
        command = {
            "command": "change_light",
            "r": r,
            "g": g,
            "b": b
        }
        return self.send_command(command)
    
    def set_brightness(self, brightness):
        """设置亮度 (0-100)"""
        command = {
            "command": "set_brightness",
            "brightness": brightness
        }
        return self.send_command(command)
    
    def start_breathing(self):
        """开启呼吸灯"""
        command = {"command": "start_breathing"}
        return self.send_command(command)
    
    def stop_breathing(self):
        """关闭呼吸灯"""
        command = {"command": "stop_breathing"}
        return self.send_command(command)
    
    def get_status(self):
        """获取LED状态"""
        command = {"command": "get_status"}
        return self.send_command(command)
    
    def ping(self):
        """测试连接"""
        command = {"command": "ping"}
        return self.send_command(command)

    def print_response(self, response):
        """美化打印响应"""
        status = response.get('status', 'unknown')
        message = response.get('message', '')
        
        if status == 'success':
            print(f"✓ {message}")
        elif status == 'error':
            print(f"✗ {message}")
        elif status == 'info':
            print(f"ℹ {message}")
        
        # 如果有数据，也打印出来
        if 'data' in response:
            data = response['data']
            if isinstance(data, dict):
                print("状态信息:")
                for key, value in data.items():
                    print(f"  {key}: {value}")

    def rainbow_demo(self):
        """彩虹演示"""
        colors = [
            ('#FF0000', '红色'),
            ('#FF8000', '橙色'),
            ('#FFFF00', '黄色'),
            ('#00FF00', '绿色'),
            ('#00FFFF', '青色'),
            ('#0000FF', '蓝色'),
            ('#8000FF', '紫色')
        ]
        
        print("开始彩虹演示...")
        for color, name in colors:
            print(f"设置为{name}")
            response = self.set_color_hex(color)
            self.print_response(response)
            time.sleep(2)

    def brightness_demo(self):
        """亮度演示"""
        print("亮度演示...")
        
        # 设置基础颜色
        self.set_color_hex("#FFFFFF")
        
        # 渐变亮度
        for brightness in [10, 30, 50, 70, 100, 70, 50, 30, 10]:
            print(f"设置亮度: {brightness}%")
            response = self.set_brightness(brightness)
            self.print_response(response)
            time.sleep(1)

    def run_interactive_mode(self):
        """运行交互模式"""
        if not self.connected:
            if not self.connect():
                return False
        
        try:
            print("\n=== 远程LED控制客户端 ===")
            print("支持的命令:")
            print("1. hex #RRGGBB - 设置十六进制颜色")
            print("2. color 颜色名 - 设置颜色名称 (red/green/blue/white/yellow/cyan/magenta/orange/purple/pink/lime/off)")
            print("3. rgb R G B - 设置RGB值 (0-255)")
            print("4. bright 数值 - 设置亮度 (0-100)")
            print("5. breath - 开启呼吸灯")
            print("6. stop - 关闭呼吸灯")
            print("7. status - 获取状态")
            print("8. ping - 测试连接")
            print("9. demo rainbow - 彩虹演示")
            print("10. demo bright - 亮度演示")
            print("11. quit - 退出")
            print()
            
            while True:
                try:
                    user_input = input("LED> ").strip().split()
                    if not user_input:
                        continue
                    
                    command = user_input[0].lower()
                    
                    if command == 'quit':
                        break
                    
                    elif command == 'hex' and len(user_input) == 2:
                        response = self.set_color_hex(user_input[1])
                        self.print_response(response)
                    
                    elif command == 'color' and len(user_input) == 2:
                        response = self.set_color_name(user_input[1])
                        self.print_response(response)
                    
                    elif command == 'rgb' and len(user_input) == 4:
                        try:
                            r, g, b = map(int, user_input[1:4])
                            response = self.change_light(r, g, b)
                            self.print_response(response)
                        except ValueError:
                            print("✗ RGB值必须是0-255的整数")
                    
                    elif command == 'bright' and len(user_input) == 2:
                        try:
                            brightness = int(user_input[1])
                            response = self.set_brightness(brightness)
                            self.print_response(response)
                        except ValueError:
                            print("✗ 亮度值必须是0-100的整数")
                    
                    elif command == 'breath':
                        response = self.start_breathing()
                        self.print_response(response)
                    
                    elif command == 'stop':
                        response = self.stop_breathing()
                        self.print_response(response)
                    
                    elif command == 'status':
                        response = self.get_status()
                        self.print_response(response)
                    
                    elif command == 'ping':
                        response = self.ping()
                        self.print_response(response)
                    
                    elif command == 'demo' and len(user_input) == 2:
                        if user_input[1] == 'rainbow':
                            self.rainbow_demo()
                        elif user_input[1] == 'bright':
                            self.brightness_demo()
                        else:
                            print("✗ 支持的演示: rainbow, bright")
                    
                    else:
                        print("✗ 无效命令，请查看帮助")
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"✗ 错误: {e}")
        
        finally:
            self.disconnect()
        
        return True

def main():
    # if len(sys.argv) != 2:
    #     print("用法: python3 led_client.py <开发板IP地址>")
    #     print("例如: python3 led_client.py 192.168.1.100")
    #     sys.exit(1)
    
    # host = sys.argv[1]
    print(HOST)
    client = LEDClient(HOST)
    
    # 运行交互模式
    client.run_interactive_mode()

if __name__ == '__main__':
    main()