#!/usr/bin/env python3
"""
RDK X5 SSH连接测试工具

测试SSH连接并提供交互式密码输入选项
"""

import os
import paramiko
import getpass
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class Config:
    def __init__(self):
        self.host = os.getenv('RDK_HOST', '172.20.10.2')
        self.port = int(os.getenv('RDK_PORT', '22'))
        self.username = os.getenv('RDK_USER', 'root')
        self.password = os.getenv('RDK_PASSWORD', 'root')
        self.script_path = os.getenv('RDK_SCRIPT_PATH', '/root/service_manager.sh')
        self.timeout = int(os.getenv('RDK_TIMEOUT', '30'))

remote_config = Config()

def test_ssh_with_config():
    """使用配置文件中的密码测试SSH连接"""
    print("🔐 使用配置文件密码测试SSH连接...")
    print(f"主机: {remote_config.host}")
    print(f"用户: {remote_config.username}")
    print(f"密码: {'*' * len(remote_config.password) if remote_config.password else '未设置'}")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=remote_config.host,
            port=remote_config.port,
            username=remote_config.username,
            password=remote_config.password,
            timeout=10
        )
        
        print("✅ SSH连接成功（使用配置文件密码）")
        
        # 测试执行命令
        stdin, stdout, stderr = ssh.exec_command('whoami')
        output = stdout.read().decode().strip()
        print(f"当前用户: {output}")
        
        # 检查服务脚本
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {remote_config.script_path}')
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            print(f"⚠️  服务脚本检查: {error}")
        else:
            print(f"✅ 服务脚本存在: {output}")
        
        ssh.close()
        return True
        
    except paramiko.AuthenticationException:
        print("❌ SSH认证失败 - 密码可能不正确")
        return False
    except paramiko.SSHException as e:
        print(f"❌ SSH连接错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False

def test_ssh_interactive():
    """交互式SSH连接测试"""
    print("\n🔐 交互式SSH连接测试...")
    
    host = input(f"主机地址 [{remote_config.host}]: ").strip() or remote_config.host
    username = input(f"用户名 [{remote_config.username}]: ").strip() or remote_config.username
    password = getpass.getpass("密码: ")
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            hostname=host,
            port=22,
            username=username,
            password=password,
            timeout=10
        )
        
        print("✅ SSH连接成功（交互式输入）")
        
        # 测试执行命令
        stdin, stdout, stderr = ssh.exec_command('whoami')
        output = stdout.read().decode().strip()
        print(f"当前用户: {output}")
        
        # 检查系统信息
        stdin, stdout, stderr = ssh.exec_command('uname -a')
        output = stdout.read().decode().strip()
        print(f"系统信息: {output}")
        
        # 检查服务脚本
        script_path = input(f"服务脚本路径 [{remote_config.script_path}]: ").strip() or remote_config.script_path
        stdin, stdout, stderr = ssh.exec_command(f'ls -la {script_path}')
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if error:
            print(f"⚠️  服务脚本: {error}")
            
            # 尝试查找可能的脚本位置
            print("🔍 搜索服务脚本...")
            stdin, stdout, stderr = ssh.exec_command('find /root -name "*service*" -type f 2>/dev/null | head -10')
            output = stdout.read().decode().strip()
            if output:
                print("找到的相关文件:")
                for line in output.split('\n'):
                    print(f"  {line}")
        else:
            print(f"✅ 服务脚本存在: {output}")
        
        ssh.close()
        return True, host, username, password
        
    except paramiko.AuthenticationException:
        print("❌ SSH认证失败")
        return False, None, None, None
    except Exception as e:
        print(f"❌ 连接错误: {e}")
        return False, None, None, None

def update_env_file(host, username, password):
    """更新.env文件中的连接信息"""
    choice = input("\n💾 是否更新.env文件中的连接信息? (y/n): ").strip().lower()
    if choice != 'y':
        return
    
    try:
        with open('/Users/m3airmima0000/new_dir/Mind-Daemon/.env', 'r') as f:
            lines = f.readlines()
        
        # 更新配置
        new_lines = []
        for line in lines:
            if line.startswith('RDK_HOST='):
                new_lines.append(f'RDK_HOST={host}\n')
            elif line.startswith('RDK_USER='):
                new_lines.append(f'RDK_USER={username}\n')
            elif line.startswith('RDK_PASSWORD='):
                new_lines.append(f'RDK_PASSWORD={password}\n')
            else:
                new_lines.append(line)
        
        with open('/Users/m3airmima0000/new_dir/Mind-Daemon/.env', 'w') as f:
            f.writelines(new_lines)
        
        print("✅ .env文件已更新")
        
    except Exception as e:
        print(f"❌ 更新.env文件失败: {e}")

def main():
    """主函数"""
    print("🔐 RDK X5 SSH连接测试工具")
    print("=" * 50)
    
    # 首先尝试配置文件中的密码
    if remote_config.password:
        config_success = test_ssh_with_config()
        if config_success:
            print("\n✅ 配置文件中的连接信息正确，可以继续使用手势检测功能")
            return
    else:
        print("⚠️  配置文件中未设置密码")
    
    # 如果配置文件连接失败，尝试交互式输入
    print("\n" + "=" * 50)
    success, host, username, password = test_ssh_interactive()
    
    if success:
        print("\n✅ 交互式SSH连接成功")
        update_env_file(host, username, password)
        print("\n💡 现在可以运行手势检测程序:")
        print("   uv run python test_gesture_detection.py")
    else:
        print("\n❌ SSH连接失败")
        print("💡 请检查:")
        print("   1. 开发板是否开机并连接到网络")
        print("   2. IP地址是否正确")
        print("   3. SSH服务是否启动")
        print("   4. 用户名和密码是否正确")
        print("   5. 防火墙是否阻止SSH连接")

if __name__ == "__main__":
    main()