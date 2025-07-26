#!/usr/bin/env python3
"""
RDK X5连接诊断工具

此工具帮助诊断与RDK X5开发板的连接问题
"""

import subprocess
import socket
import time
from src.mind_daemon.detect.config import remote_config
from src.mind_daemon.detect import GestureDetector

def ping_test(host: str) -> bool:
    """测试网络连通性"""
    print(f"🏓 Ping测试 {host}...")
    try:
        result = subprocess.run(['ping', '-c', '3', host], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ Ping成功 - 网络连通")
            return True
        else:
            print("❌ Ping失败 - 网络不通")
            print(f"错误: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("❌ Ping超时")
        return False
    except Exception as e:
        print(f"❌ Ping测试错误: {e}")
        return False

def test_ssh_connection() -> bool:
    """测试SSH连接"""
    print(f"🔐 测试SSH连接 {remote_config.host}:{remote_config.port}...")
    detector = GestureDetector(remote_config)
    
    if detector.connect():
        print("✅ SSH连接成功")
        detector.disconnect()
        return True
    else:
        print("❌ SSH连接失败")
        return False

def test_socket_port(host: str, port: int, timeout: int = 5) -> bool:
    """测试Socket端口连通性"""
    print(f"🔌 测试Socket端口 {host}:{port}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        
        if result == 0:
            print(f"✅ 端口 {port} 开放")
            return True
        else:
            print(f"❌ 端口 {port} 关闭或不可达")
            return False
    except Exception as e:
        print(f"❌ 端口测试错误: {e}")
        return False

def test_service_script() -> bool:
    """测试远程服务脚本"""
    print(f"🧪 测试服务脚本 {remote_config.script_path}...")
    detector = GestureDetector(remote_config)
    
    if not detector.connect():
        print("❌ 无法连接SSH，跳过脚本测试")
        return False
    
    # 检查脚本是否存在
    exit_code, output, error = detector.controller.execute_command(f"ls -la {remote_config.script_path}")
    if exit_code != 0:
        print(f"❌ 服务脚本不存在: {remote_config.script_path}")
        print(f"错误: {error}")
        detector.disconnect()
        return False
    
    print("✅ 服务脚本存在")
    print(f"脚本信息: {output.strip()}")
    
    # 测试脚本状态命令
    print("🔍 检查服务状态...")
    status = detector.get_status()
    print(f"状态信息: {status}")
    
    detector.disconnect()
    return True

def main():
    """主诊断流程"""
    print("🩺 RDK X5连接诊断工具")
    print("=" * 50)
    print(f"目标主机: {remote_config.host}")
    print(f"SSH端口: {remote_config.port}")
    print(f"Socket端口: 8888")
    print(f"用户名: {remote_config.username}")
    print("=" * 50)
    
    # 1. 网络连通性测试
    if not ping_test(remote_config.host):
        print("\n❌ 网络连通性测试失败")
        print("💡 请检查:")
        print("   - 开发板是否开机")
        print("   - 网络连接是否正常")
        print("   - IP地址是否正确")
        return
    
    # 2. SSH连接测试
    if not test_ssh_connection():
        print("\n❌ SSH连接测试失败")
        print("💡 请检查:")
        print("   - SSH服务是否启动")
        print("   - 用户名密码是否正确")
        print("   - SSH端口是否正确")
        return
    
    # 3. 服务脚本测试
    if not test_service_script():
        print("\n❌ 服务脚本测试失败")
        return
    
    # 4. Socket端口测试
    socket_available = test_socket_port(remote_config.host, 8888)
    
    print("\n" + "=" * 50)
    print("📊 诊断结果汇总:")
    print("✅ 网络连通性: 正常")
    print("✅ SSH连接: 正常")
    print("✅ 服务脚本: 正常")
    print(f"{'✅' if socket_available else '❌'} Socket端口: {'开放' if socket_available else '关闭'}")
    
    if not socket_available:
        print("\n🔧 Socket端口未开放的可能原因:")
        print("   1. 远程服务未启动")
        print("   2. 服务启动失败")
        print("   3. 防火墙阻止连接")
        print("   4. 服务绑定到其他端口")
        
        print("\n💡 建议操作:")
        print("   1. 手动启动远程服务")
        print("   2. 检查服务日志")
        print("   3. 确认端口配置")
        
        # 尝试启动服务
        choice = input("\n是否尝试启动远程服务? (y/n): ").strip().lower()
        if choice == 'y':
            print("🚀 启动远程服务...")
            detector = GestureDetector(remote_config)
            if detector.connect():
                if detector.start_services():
                    print("✅ 服务启动成功")
                    time.sleep(3)
                    if test_socket_port(remote_config.host, 8888):
                        print("✅ Socket端口现在可用")
                    else:
                        print("❌ Socket端口仍不可用")
                else:
                    print("❌ 服务启动失败")
                detector.disconnect()
    else:
        print("\n🎉 所有连接测试通过！可以正常使用手势检测功能。")

if __name__ == "__main__":
    main()