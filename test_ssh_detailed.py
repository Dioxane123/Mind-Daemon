#!/usr/bin/env python3
"""
RDK X5开发板SSH连接详细测试脚本
提供全面的连接诊断和故障排除信息
"""

import sys
import os
import socket
import subprocess
import time
import json
from typing import Dict, Any, Optional

# 添加项目路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import paramiko
    PARAMIKO_AVAILABLE = True
except ImportError:
    PARAMIKO_AVAILABLE = False

from mind_daemon.detect.config import remote_config


class SSHDetailedTester:
    """SSH详细测试类"""
    
    def __init__(self, config):
        self.config = config
        self.test_results = {}
        self.start_time = time.time()
        
    def print_header(self, title: str):
        """打印测试标题"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")
        
    def print_test_result(self, test_name: str, success: bool, message: str = "", details: str = ""):
        """打印测试结果"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if message:
            print(f"   Message: {message}")
        if details:
            print(f"   Details: {details}")
        self.test_results[test_name] = {
            "success": success, 
            "message": message, 
            "details": details,
            "timestamp": time.time() - self.start_time
        }
        
    def test_environment_check(self) -> bool:
        """检查测试环境"""
        self.print_header("测试环境检查")
        
        # 检查Python版本
        python_version = sys.version
        print(f"Python版本: {python_version}")
        
        # 检查必要的模块
        modules = {
            "paramiko": PARAMIKO_AVAILABLE,
            "socket": True,
            "subprocess": True
        }
        
        for module, available in modules.items():
            self.print_test_result(f"{module}模块", available, 
                                 "可用" if available else "不可用")
        
        # 检查配置文件
        config_valid = all([
            self.config.host,
            self.config.username, 
            self.config.password
        ])
        
        self.print_test_result("配置文件", config_valid,
                             "配置完整" if config_valid else "配置不完整")
        
        return config_valid and PARAMIKO_AVAILABLE
        
    def test_network_connectivity(self) -> bool:
        """测试网络连通性"""
        self.print_header("网络连通性测试")
        
        # 1. Ping测试
        try:
            print(f"正在ping {self.config.host}...")
            result = subprocess.run(
                ['ping', '-c', '3', '-W', '3000', self.config.host],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode == 0:
                # 解析ping结果
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'packet loss' in line:
                        print(f"   {line.strip()}")
                    elif 'min/avg/max' in line:
                        print(f"   {line.strip()}")
                        
                self.print_test_result("Ping测试", True, f"主机 {self.config.host} 可达")
            else:
                self.print_test_result("Ping测试", False, 
                                     f"主机 {self.config.host} 不可达",
                                     result.stderr.strip() if result.stderr else "网络不通")
                return False
                
        except subprocess.TimeoutExpired:
            self.print_test_result("Ping测试", False, "Ping超时 (15秒)")
            return False
        except FileNotFoundError:
            self.print_test_result("Ping测试", False, "ping命令不可用")
            # 继续其他测试
        except Exception as e:
            self.print_test_result("Ping测试", False, f"Ping异常: {str(e)}")
            
        # 2. 端口连通性测试
        try:
            print(f"正在测试端口 {self.config.host}:{self.config.port}...")
            start_time = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.config.host, self.config.port))
            connect_time = time.time() - start_time
            sock.close()
            
            if result == 0:
                self.print_test_result("端口连通性", True, 
                                     f"端口 {self.config.port} 开放 (连接时间: {connect_time:.2f}s)")
                return True
            else:
                self.print_test_result("端口连通性", False,
                                     f"端口 {self.config.port} 不可达 (错误码: {result})",
                                     "SSH服务可能未启动或端口被阻塞")
                return False
                
        except Exception as e:
            self.print_test_result("端口连通性", False, f"端口测试异常: {str(e)}")
            return False
            
    def test_ssh_authentication(self) -> bool:
        """测试SSH认证"""
        self.print_header("SSH认证测试")
        
        if not PARAMIKO_AVAILABLE:
            self.print_test_result("SSH认证", False, "paramiko库不可用")
            return False
            
        try:
            print(f"正在连接 {self.config.username}@{self.config.host}:{self.config.port}...")
            
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            start_time = time.time()
            ssh_client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout,
                banner_timeout=30
            )
            connect_time = time.time() - start_time
            
            self.print_test_result("SSH认证", True, 
                                 f"认证成功 (连接时间: {connect_time:.2f}s)")
            
            # 获取服务器信息
            transport = ssh_client.get_transport()
            server_version = transport.remote_version if transport else "未知"
            print(f"   服务器版本: {server_version}")
            
            ssh_client.close()
            return True
            
        except paramiko.AuthenticationException:
            self.print_test_result("SSH认证", False, "认证失败",
                                 "用户名或密码错误")
            return False
        except paramiko.SSHException as e:
            self.print_test_result("SSH认证", False, f"SSH协议错误: {str(e)}")
            return False
        except socket.timeout:
            self.print_test_result("SSH认证", False, "连接超时")
            return False
        except Exception as e:
            self.print_test_result("SSH认证", False, f"连接异常: {str(e)}")
            return False
            
    def test_command_execution(self) -> bool:
        """测试命令执行"""
        self.print_header("命令执行测试")
        
        if not PARAMIKO_AVAILABLE:
            self.print_test_result("命令执行", False, "paramiko库不可用")
            return False
            
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout
            )
            
            # 测试基本命令
            commands = [
                ("whoami", "获取当前用户"),
                ("pwd", "获取当前目录"),
                ("date", "获取系统时间"),
                ("uptime", "获取系统运行时间"),
                ("free -h", "获取内存使用情况"),
                ("df -h /", "获取磁盘使用情况")
            ]
            
            all_success = True
            for cmd, desc in commands:
                print(f"正在执行: {cmd} ({desc})")
                stdin, stdout, stderr = ssh_client.exec_command(cmd)
                output = stdout.read().decode().strip()
                error = stderr.read().decode().strip()
                
                if output and not error:
                    self.print_test_result(f"命令: {cmd}", True, output[:100])
                    if len(output) > 100:
                        print(f"   完整输出: {output}")
                else:
                    self.print_test_result(f"命令: {cmd}", False, 
                                         error if error else "无输出")
                    all_success = False
                    
            ssh_client.close()
            return all_success
            
        except Exception as e:
            self.print_test_result("命令执行", False, f"执行异常: {str(e)}")
            return False
            
    def test_service_status(self) -> bool:
        """测试服务状态"""
        self.print_header("服务状态检查")
        
        if not PARAMIKO_AVAILABLE:
            self.print_test_result("服务状态", False, "paramiko库不可用")
            return False
            
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout
            )
            
            # 检查服务脚本
            print(f"检查服务脚本: {self.config.script_path}")
            stdin, stdout, stderr = ssh_client.exec_command(f'ls -la {self.config.script_path}')
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if output and not error:
                self.print_test_result("服务脚本", True, f"脚本存在: {output}")
                
                # 检查脚本内容摘要
                stdin, stdout, stderr = ssh_client.exec_command(f'head -20 {self.config.script_path}')
                script_content = stdout.read().decode().strip()
                if script_content:
                    print(f"   脚本内容预览:\n{script_content}")
                    
            else:
                self.print_test_result("服务脚本", False, 
                                     f"脚本不存在: {self.config.script_path}",
                                     error)
                
                # 搜索可能的脚本位置
                print("搜索可能的服务脚本...")
                search_commands = [
                    'find /root -name "*service*" -type f 2>/dev/null',
                    'find /root -name "*.sh" -type f 2>/dev/null | head -10',
                    'ls -la /root/'
                ]
                
                for search_cmd in search_commands:
                    stdin, stdout, stderr = ssh_client.exec_command(search_cmd)
                    search_output = stdout.read().decode().strip()
                    if search_output:
                        print(f"   搜索结果 ({search_cmd}):")
                        for line in search_output.split('\n')[:10]:
                            print(f"     {line}")
                        break
                        
            # 检查系统服务状态
            print("检查相关系统服务...")
            services = ['ssh', 'sshd', 'network']
            for service in services:
                stdin, stdout, stderr = ssh_client.exec_command(f'systemctl is-active {service} 2>/dev/null || echo "unknown"')
                status = stdout.read().decode().strip()
                active = status == 'active'
                self.print_test_result(f"服务: {service}", active, 
                                     f"状态: {status}")
                                     
            # 检查网络接口
            print("检查网络接口...")
            stdin, stdout, stderr = ssh_client.exec_command('ip addr show | grep inet')
            network_output = stdout.read().decode().strip()
            if network_output:
                self.print_test_result("网络接口", True, "网络接口正常")
                print("   网络信息:")
                for line in network_output.split('\n'):
                    if 'inet ' in line:
                        print(f"     {line.strip()}")
            
            ssh_client.close()
            return True
            
        except Exception as e:
            self.print_test_result("服务状态", False, f"检查异常: {str(e)}")
            return False
            
    def test_performance_metrics(self) -> bool:
        """测试性能指标"""
        self.print_header("性能指标测试")
        
        if not PARAMIKO_AVAILABLE:
            self.print_test_result("性能指标", False, "paramiko库不可用")
            return False
            
        try:
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh_client.connect(
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username,
                password=self.config.password,
                timeout=self.config.timeout
            )
            
            # 测试连接延迟
            latencies = []
            for i in range(5):
                start_time = time.time()
                stdin, stdout, stderr = ssh_client.exec_command('echo "ping"')
                stdout.read()
                latency = (time.time() - start_time) * 1000
                latencies.append(latency)
                
            avg_latency = sum(latencies) / len(latencies)
            min_latency = min(latencies)
            max_latency = max(latencies)
            
            self.print_test_result("连接延迟", True, 
                                 f"平均: {avg_latency:.2f}ms, 最小: {min_latency:.2f}ms, 最大: {max_latency:.2f}ms")
            
            # 测试数据传输
            test_data = "a" * 1000  # 1KB数据
            start_time = time.time()
            stdin, stdout, stderr = ssh_client.exec_command(f'echo "{test_data}" | wc -c')
            result = stdout.read().decode().strip()
            transfer_time = time.time() - start_time
            
            if result.strip() == '1001':  # 1000字符 + 1个换行符
                throughput = 1000 / transfer_time if transfer_time > 0 else 0
                self.print_test_result("数据传输", True,
                                     f"1KB传输时间: {transfer_time:.3f}s, 吞吐量: {throughput:.2f} bytes/s")
            else:
                self.print_test_result("数据传输", False, "数据传输测试失败")
                
            ssh_client.close()
            return True
            
        except Exception as e:
            self.print_test_result("性能指标", False, f"测试异常: {str(e)}")
            return False
            
    def generate_report(self):
        """生成测试报告"""
        self.print_header("测试报告")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results.values() if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"测试统计:")
        print(f"  总测试数: {total_tests}")
        print(f"  通过: {passed_tests} ✅")
        print(f"  失败: {failed_tests} ❌")
        print(f"  成功率: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "0%")
        print(f"  总耗时: {time.time() - self.start_time:.2f}秒")
        
        # 详细结果
        print(f"\n详细结果:")
        for test_name, result in self.test_results.items():
            status = "✅" if result["success"] else "❌"
            timestamp = f"{result['timestamp']:.2f}s"
            print(f"  {status} {test_name} ({timestamp})")
            if result["message"]:
                print(f"      {result['message']}")
                
        # 失败测试的建议
        if failed_tests > 0:
            self.print_troubleshooting_guide()
            
        # 保存报告到文件
        self.save_report_to_file()
        
    def save_report_to_file(self):
        """保存报告到文件"""
        try:
            report_data = {
                "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
                "config": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "username": self.config.username,
                    "script_path": self.config.script_path
                },
                "results": self.test_results,
                "summary": {
                    "total_tests": len(self.test_results),
                    "passed": sum(1 for r in self.test_results.values() if r["success"]),
                    "failed": sum(1 for r in self.test_results.values() if not r["success"]),
                    "duration": time.time() - self.start_time
                }
            }
            
            report_file = f"ssh_test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
                
            print(f"\n📊 测试报告已保存至: {report_file}")
            
        except Exception as e:
            print(f"⚠️  保存报告失败: {str(e)}")
            
    def print_troubleshooting_guide(self):
        """打印故障排除指南"""
        self.print_header("故障排除指南")
        
        failed_tests = [name for name, result in self.test_results.items() if not result["success"]]
        
        solutions = {
            "环境检查": [
                "安装必要依赖: pip install paramiko",
                "检查Python版本是否支持",
                "验证配置文件完整性"
            ],
            "Ping测试": [
                "检查网络连接状态",
                "确认IP地址正确",
                "检查路由配置",
                "测试其他网络服务"
            ],
            "端口连通性": [
                "确认SSH服务已启动: systemctl status ssh",
                "检查防火墙设置: iptables -L",
                "验证SSH端口配置: grep Port /etc/ssh/sshd_config",
                "重启SSH服务: systemctl restart ssh"
            ],
            "SSH认证": [
                "验证用户名密码正确性",
                "检查SSH配置允许密码认证",
                "查看SSH日志: journalctl -u ssh",
                "尝试手动SSH连接调试"
            ],
            "命令执行": [
                "检查用户权限",
                "验证shell环境",
                "检查系统资源使用情况",
                "测试简单命令执行"
            ],
            "服务状态": [
                "确认服务脚本路径正确",
                "检查脚本权限: chmod +x script",
                "验证脚本依赖",
                "手动执行脚本测试"
            ],
            "性能指标": [
                "检查网络质量",
                "优化SSH配置参数",
                "监控系统资源使用",
                "考虑网络优化"
            ]
        }
        
        print("根据失败的测试，建议按以下步骤排查：\n")
        
        for test_name in failed_tests:
            # 匹配测试名称到解决方案
            matched_solutions = []
            for solution_key, solution_list in solutions.items():
                if any(keyword in test_name.lower() for keyword in solution_key.lower().split()):
                    matched_solutions.extend(solution_list)
                    
            if matched_solutions:
                print(f"🔧 {test_name}:")
                for i, solution in enumerate(matched_solutions, 1):
                    print(f"   {i}. {solution}")
                print()
                
        print("通用排查步骤:")
        print("1. 确保开发板电源正常，系统已完全启动")
        print("2. 检查网络连接，确保主机和开发板在同一网段")
        print("3. 验证SSH服务配置和状态")
        print("4. 检查防火墙和安全组设置")
        print("5. 查看系统日志获取详细错误信息")
        print("6. 考虑使用SSH密钥认证替代密码认证")
        
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("🔍 RDK X5开发板SSH连接全面诊断测试")
        print(f"测试开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"目标主机: {self.config.host}:{self.config.port}")
        print(f"用户: {self.config.username}")
        
        # 测试序列
        test_sequence = [
            ("环境检查", self.test_environment_check),
            ("网络连通性", self.test_network_connectivity),
            ("SSH认证", self.test_ssh_authentication),
            ("命令执行", self.test_command_execution),
            ("服务状态", self.test_service_status),
            ("性能指标", self.test_performance_metrics)
        ]
        
        for test_name, test_func in test_sequence:
            try:
                print(f"\n⏳ 正在执行: {test_name}")
                test_func()
            except KeyboardInterrupt:
                print(f"\n⚠️  测试被用户中断")
                break
            except Exception as e:
                self.print_test_result(test_name, False, f"测试异常: {str(e)}")
                print(f"❌ {test_name} 执行异常: {str(e)}")
                
        # 生成最终报告
        self.generate_report()


def main():
    """主函数"""
    try:
        tester = SSHDetailedTester(remote_config)
        tester.run_comprehensive_test()
    except KeyboardInterrupt:
        print("\n⚠️  测试被用户中断")
    except Exception as e:
        print(f"❌ 程序异常: {str(e)}")
        

if __name__ == "__main__":
    main()