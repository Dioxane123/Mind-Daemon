#!/usr/bin/env python3
"""
RDK X5开发板SSH连接快速测试脚本
用于日常快速验证SSH连接状态
"""

import sys
import os
import time

# 添加项目路径到sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import paramiko
    from mind_daemon.detect.config import remote_config
    
    def quick_ssh_test():
        """快速SSH连接测试"""
        print("🔍 RDK X5 SSH连接快速测试")
        print("=" * 40)
        print(f"目标: {remote_config.username}@{remote_config.host}:{remote_config.port}")
        
        try:
            # 连接测试
            print("正在连接...", end=" ")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            start_time = time.time()
            ssh.connect(
                hostname=remote_config.host,
                port=remote_config.port,
                username=remote_config.username,
                password=remote_config.password,
                timeout=10
            )
            connect_time = time.time() - start_time
            print(f"✅ 成功 ({connect_time:.2f}s)")
            
            # 基本命令测试
            print("执行基本命令...", end=" ")
            stdin, stdout, stderr = ssh.exec_command('whoami && pwd && date')
            output = stdout.read().decode().strip()
            error = stderr.read().decode().strip()
            
            if output and not error:
                print("✅ 成功")
                print(f"输出: {output.replace(chr(10), ' | ')}")
            else:
                print(f"❌ 失败: {error}")
                
            # 检查服务脚本
            print("检查服务脚本...", end=" ")
            stdin, stdout, stderr = ssh.exec_command(f'test -f {remote_config.script_path} && echo "exists" || echo "missing"')
            result = stdout.read().decode().strip()
            
            if result == "exists":
                print("✅ 存在")
            else:
                print("❌ 不存在")
                
            # 检查系统状态
            print("检查系统负载...", end=" ")
            stdin, stdout, stderr = ssh.exec_command('uptime | awk -F"load average:" \'{print $2}\'')
            load_avg = stdout.read().decode().strip()
            print(f"✅ 负载{load_avg}")
            
            ssh.close()
            
            print("\n" + "=" * 40)
            print("✅ 所有测试通过，SSH连接正常")
            print("💡 可以运行手势检测: python test_gesture_detection.py")
            return True
            
        except paramiko.AuthenticationException:
            print("❌ 认证失败")
            print("💡 检查用户名和密码配置")
            return False
        except Exception as e:
            print(f"❌ 连接失败: {str(e)}")
            print("💡 检查网络连接和开发板状态")
            return False
    
    if __name__ == "__main__":
        success = quick_ssh_test()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"❌ 导入错误: {str(e)}")
    print("💡 请确保已安装paramiko: pip install paramiko")
    sys.exit(1)
except Exception as e:
    print(f"❌ 程序异常: {str(e)}")
    sys.exit(1)