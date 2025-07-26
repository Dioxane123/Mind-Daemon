#!/usr/bin/env python3
"""
WebSocket监听工具 - Mind Daemon Dashboard数据流监控

功能：
- 连接到WebSocket服务器 (ws://localhost:8889)
- 实时显示接收到的数据
- 验证数据格式是否符合前端要求
- 统计连接状态和数据质量
- 彩色终端输出和数据格式化

使用方法：
    python websocket_monitor.py
    python websocket_monitor.py --host localhost --port 8889 --verbose

作者：Mind Daemon Project
"""

import asyncio
import websockets
import json
import argparse
import sys
import signal
from datetime import datetime
from typing import Dict, Any

# ANSI颜色代码
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m' 
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class WebSocketMonitor:
    """WebSocket数据流监控器"""
    
    def __init__(self, host: str = "localhost", port: int = 8889, verbose: bool = False, duration: int = None):
        self.host = host
        self.port = port
        self.verbose = verbose
        self.duration = duration  # 运行时长（秒）
        self.url = f"ws://{host}:{port}"
        
        # 统计数据
        self.stats = {
            'connected_at': None,
            'total_messages': 0,
            'valid_messages': 0,
            'invalid_messages': 0,
            'basic_data_count': 0,
            'advanced_data_count': 0,
            'algorithm_data_count': 0,
            'last_message_time': None,
            'connection_lost_count': 0
        }
        
        # 运行控制
        self.running = True
        
        print(f"{Colors.HEADER}🔍 Mind Daemon WebSocket Monitor{Colors.ENDC}")
        print(f"{Colors.OKCYAN}监听地址: {self.url}{Colors.ENDC}")
        print(f"{Colors.OKCYAN}详细模式: {'开启' if verbose else '关闭'}{Colors.ENDC}")
        if duration:
            print(f"{Colors.OKCYAN}运行时长: {duration} 秒{Colors.ENDC}")
        print("-" * 60)

    def validate_data_structure(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """验证数据结构是否符合前端要求"""
        validation_results = {
            'has_basic': False,
            'has_advanced': False,
            'basic_complete': False,
            'advanced_complete': False,
            'has_algorithm_analysis': False,
            'scores_valid': False
        }
        
        # 检查基础结构
        if 'basic' in data:
            validation_results['has_basic'] = True
            basic = data['basic']
            
            # 检查基础字段完整性
            required_basic = ['light', 'music', 'curtain', 'Scores']
            if all(field in basic for field in required_basic):
                validation_results['basic_complete'] = True
                self.stats['basic_data_count'] += 1
            
            # 检查Scores字段
            if 'Scores' in basic and isinstance(basic['Scores'], dict):
                scores = basic['Scores']
                required_scores = ['At', 'Ex', 'Re', 'St']
                if all(score in scores for score in required_scores):
                    validation_results['scores_valid'] = True
            
            # 检查算法分析
            if 'algorithm_analysis' in basic:
                validation_results['has_algorithm_analysis'] = True
                self.stats['algorithm_data_count'] += 1
        
        # 检查高级结构
        if 'advanced' in data:
            validation_results['has_advanced'] = True
            advanced = data['advanced']
            
            # 检查高级字段完整性
            required_advanced = ['State', 'Summary', 'Action']
            if all(field in advanced for field in required_advanced):
                validation_results['advanced_complete'] = True
                self.stats['advanced_data_count'] += 1
        
        return validation_results

    def format_data_display(self, data: Dict[str, Any], validation: Dict[str, bool]) -> str:
        """格式化数据显示"""
        output = []
        
        # 时间戳
        current_time = datetime.now().strftime("%H:%M:%S")
        output.append(f"{Colors.BOLD}[{current_time}] 数据包接收{Colors.ENDC}")
        
        # 验证状态
        status_color = Colors.OKGREEN if validation['basic_complete'] and validation['advanced_complete'] else Colors.WARNING
        status_text = "✅ 完整" if validation['basic_complete'] and validation['advanced_complete'] else "⚠️  不完整"
        output.append(f"状态: {status_color}{status_text}{Colors.ENDC}")
        
        # Basic数据
        if validation['has_basic']:
            output.append(f"\n{Colors.OKBLUE}📊 Basic Data:{Colors.ENDC}")
            basic = data['basic']
            
            # 灯光状态
            if 'light' in basic:
                light = basic['light']
                light_status = "🟢 ON" if light.get('is_on') else "🔴 OFF"
                color = light.get('color_hex', '#000000')
                brightness = light.get('lightness', 0)
                output.append(f"  💡 Light: {light_status} {color} ({brightness}%)")
            
            # 音乐状态
            if 'music' in basic:
                music = basic['music']
                music_status = "🎵 Playing" if music.get('is_playing') else "⏸️  Stopped"
                name = music.get('name', 'N/A')
                music_type = music.get('type', 'N/A')
                output.append(f"  🎼 Music: {music_status} - {name} [{music_type}]")
            
            # 窗帘状态
            if 'curtain' in basic:
                curtain = basic['curtain']
                curtain_status = "🪟 Open" if curtain.get('state') == 0 else "🚪 Closed"
                output.append(f"  🏠 Curtain: {curtain_status}")
            
            # 认知分数
            if validation['scores_valid']:
                scores = basic['Scores']
                score_color = Colors.OKGREEN if all(score >= 40 for score in scores.values()) else Colors.WARNING
                output.append(f"  📈 Scores: {score_color}At:{scores['At']} Ex:{scores['Ex']} Re:{scores['Re']} St:{scores['St']}{Colors.ENDC}")
            
            # 算法分析
            if validation['has_algorithm_analysis']:
                algo = basic['algorithm_analysis']
                output.append(f"  🧠 Algorithm Analysis: {Colors.OKCYAN}Available{Colors.ENDC}")
                
                if 'clinical_analysis' in algo:
                    clinical = algo['clinical_analysis']
                    clinical_state = clinical.get('state', 'Unknown')
                    faa_score = clinical.get('faa_z_score', 0)
                    output.append(f"    🏥 Clinical: {clinical_state} (FAA: {faa_score:.2f})")
                
                if 'cognitive_analysis' in algo:
                    cognitive = algo['cognitive_analysis']
                    cognitive_state = cognitive.get('state', 'Unknown')
                    engagement = cognitive.get('engagement_index', 0)
                    output.append(f"    🧮 Cognitive: {cognitive_state} (Engagement: {engagement:.2f})")
        
        # Advanced数据
        if validation['has_advanced']:
            output.append(f"\n{Colors.OKGREEN}🚀 Advanced Data:{Colors.ENDC}")
            advanced = data['advanced']
            
            state = advanced.get('State', 'Unknown')
            summary = advanced.get('Summary', '')[:80] + '...' if len(advanced.get('Summary', '')) > 80 else advanced.get('Summary', '')
            action = advanced.get('Action', 'None')
            
            # 状态图标映射
            state_icons = {
                'Relaxed': '😌',
                'Focused': '🎯', 
                'Stressed': '😰',
                'Excited': '⚡'
            }
            state_icon = state_icons.get(state, '❓')
            
            output.append(f"  {state_icon} State: {Colors.BOLD}{state}{Colors.ENDC}")
            output.append(f"  📝 Summary: {summary}")
            output.append(f"  🎯 Action: {action}")
        
        return '\n'.join(output)

    def print_statistics(self):
        """打印统计信息"""
        print(f"\n{Colors.HEADER}📈 连接统计{Colors.ENDC}")
        print("-" * 40)
        
        # 连接时间
        if self.stats['connected_at']:
            duration = datetime.now() - self.stats['connected_at']
            print(f"连接时长: {Colors.OKGREEN}{duration}{Colors.ENDC}")
        
        # 消息统计
        print(f"总消息数: {Colors.OKCYAN}{self.stats['total_messages']}{Colors.ENDC}")
        print(f"有效消息: {Colors.OKGREEN}{self.stats['valid_messages']}{Colors.ENDC}")
        print(f"无效消息: {Colors.FAIL}{self.stats['invalid_messages']}{Colors.ENDC}")
        
        # 数据类型统计
        print(f"Basic数据: {Colors.OKBLUE}{self.stats['basic_data_count']}{Colors.ENDC}")
        print(f"Advanced数据: {Colors.OKGREEN}{self.stats['advanced_data_count']}{Colors.ENDC}")
        print(f"算法分析: {Colors.OKCYAN}{self.stats['algorithm_data_count']}{Colors.ENDC}")
        
        # 连接质量
        if self.stats['connection_lost_count'] > 0:
            print(f"连接中断: {Colors.WARNING}{self.stats['connection_lost_count']}次{Colors.ENDC}")
        else:
            print(f"连接质量: {Colors.OKGREEN}稳定{Colors.ENDC}")
        
        # 消息频率
        if self.stats['total_messages'] > 0 and self.stats['connected_at']:
            duration = (datetime.now() - self.stats['connected_at']).total_seconds()
            if duration > 0:
                frequency = self.stats['total_messages'] / duration
                print(f"数据频率: {Colors.OKCYAN}{frequency:.2f} msg/s{Colors.ENDC}")

    async def monitor_websocket(self):
        """监控WebSocket连接"""
        while self.running:
            try:
                print(f"{Colors.OKCYAN}🔄 正在连接到 {self.url}...{Colors.ENDC}")
                
                async with websockets.connect(
                    self.url,
                    ping_interval=20,
                    ping_timeout=10,
                    close_timeout=10
                ) as websocket:
                    
                    print(f"{Colors.OKGREEN}✅ WebSocket连接成功！{Colors.ENDC}")
                    self.stats['connected_at'] = datetime.now()
                    
                    async for message in websocket:
                        if not self.running:
                            break
                        
                        # 检查是否超过设定的运行时长
                        if self.duration and self.stats['connected_at']:
                            elapsed = (datetime.now() - self.stats['connected_at']).total_seconds()
                            if elapsed >= self.duration:
                                print(f"{Colors.WARNING}⏰ 已达到设定运行时长 {self.duration} 秒，停止监控{Colors.ENDC}")
                                self.running = False
                                break
                            
                        self.stats['total_messages'] += 1
                        self.stats['last_message_time'] = datetime.now()
                        
                        try:
                            # 解析JSON数据
                            data = json.loads(message)
                            
                            # 验证数据结构
                            validation = self.validate_data_structure(data)
                            
                            # 判断消息有效性
                            is_valid = validation['has_basic'] or validation['has_advanced']
                            
                            if is_valid:
                                self.stats['valid_messages'] += 1
                                
                                # 显示数据
                                if self.verbose:
                                    # 详细模式：显示格式化数据
                                    formatted_data = self.format_data_display(data, validation)
                                    print(formatted_data)
                                    print("-" * 60)
                                else:
                                    # 简洁模式：只显示关键信息
                                    timestamp = datetime.now().strftime("%H:%M:%S")
                                    basic_status = "✅" if validation['basic_complete'] else "❌"
                                    advanced_status = "✅" if validation['advanced_complete'] else "❌"
                                    algo_status = "🧠" if validation['has_algorithm_analysis'] else "⭕"
                                    
                                    scores_info = ""
                                    if validation['scores_valid']:
                                        scores = data['basic']['Scores']
                                        scores_info = f"At:{scores['At']} Ex:{scores['Ex']} Re:{scores['Re']} St:{scores['St']}"
                                    
                                    print(f"[{timestamp}] Basic:{basic_status} Advanced:{advanced_status} Algo:{algo_status} | {scores_info}")
                            else:
                                self.stats['invalid_messages'] += 1
                                print(f"{Colors.WARNING}⚠️  收到无效数据包{Colors.ENDC}")
                                if self.verbose:
                                    print(f"原始数据: {message[:200]}...")
                        
                        except json.JSONDecodeError as e:
                            self.stats['invalid_messages'] += 1
                            print(f"{Colors.FAIL}❌ JSON解析失败: {e}{Colors.ENDC}")
                            if self.verbose:
                                print(f"原始消息: {message[:100]}...")
                        
                        except Exception as e:
                            self.stats['invalid_messages'] += 1
                            print(f"{Colors.FAIL}❌ 处理消息时出错: {e}{Colors.ENDC}")
            
            except websockets.exceptions.ConnectionClosed:
                self.stats['connection_lost_count'] += 1
                print(f"{Colors.WARNING}⚠️  WebSocket连接已关闭{Colors.ENDC}")
                if self.running:
                    print(f"{Colors.OKCYAN}🔄 3秒后尝试重新连接...{Colors.ENDC}")
                    await asyncio.sleep(3)
            
            except websockets.exceptions.InvalidURI:
                print(f"{Colors.FAIL}❌ 无效的WebSocket URI: {self.url}{Colors.ENDC}")
                break
            
            except ConnectionRefusedError:
                print(f"{Colors.FAIL}❌ 无法连接到 {self.url} - 连接被拒绝{Colors.ENDC}")
                print(f"{Colors.WARNING}提示: 请确保Mind Daemon WebSocket服务器正在运行{Colors.ENDC}")
                print(f"{Colors.OKCYAN}🔄 5秒后尝试重新连接...{Colors.ENDC}")
                await asyncio.sleep(5)
            
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}⚠️  用户中断，正在停止监控...{Colors.ENDC}")
                self.running = False
                break
            
            except Exception as e:
                self.stats['connection_lost_count'] += 1
                print(f"{Colors.FAIL}❌ 连接错误: {e}{Colors.ENDC}")
                if self.running:
                    print(f"{Colors.OKCYAN}🔄 5秒后尝试重新连接...{Colors.ENDC}")
                    await asyncio.sleep(5)

    def signal_handler(self, signum, _frame):
        """处理信号中断"""
        print(f"\n{Colors.WARNING}⚠️  收到停止信号 ({signum})，正在停止监控...{Colors.ENDC}")
        self.running = False

    async def start_monitoring(self):
        """开始监控"""
        # 设置信号处理
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            await self.monitor_websocket()
        finally:
            self.print_statistics()
            print(f"\n{Colors.HEADER}🛑 WebSocket监控已停止{Colors.ENDC}")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="Mind Daemon WebSocket监听工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python websocket_monitor.py                          # 默认连接localhost:8889
  python websocket_monitor.py --host 192.168.1.100    # 连接远程主机
  python websocket_monitor.py --port 8890              # 自定义端口
  python websocket_monitor.py --verbose                # 详细输出模式
  python websocket_monitor.py --duration 30            # 运行30秒后自动停止
  python websocket_monitor.py -v -d 60 --host localhost # 组合参数

输出说明:
  ✅ - 数据完整    ❌ - 数据缺失    🧠 - 包含算法分析
  ⭕ - 无算法分析  ⚠️ - 警告       🔄 - 重新连接
        """
    )
    
    parser.add_argument(
        '--host', 
        default='localhost',
        help='WebSocket服务器主机地址 (默认: localhost)'
    )
    
    parser.add_argument(
        '--port', 
        type=int, 
        default=8889,
        help='WebSocket服务器端口 (默认: 8889)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出模式，显示完整数据内容'
    )
    
    parser.add_argument(
        '--duration', '-d',
        type=int,
        help='设置监控运行时长（秒），不设置则持续运行'
    )
    
    args = parser.parse_args()
    
    # 创建监控器
    monitor = WebSocketMonitor(
        host=args.host,
        port=args.port,
        verbose=args.verbose,
        duration=args.duration
    )
    
    # 启动监控
    try:
        asyncio.run(monitor.start_monitoring())
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}程序被用户中断{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}程序运行出错: {e}{Colors.ENDC}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())