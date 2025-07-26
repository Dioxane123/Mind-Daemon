#!/usr/bin/env python3
"""
简单SSH连接测试

使用现有的config.py配置测试SSH连接
"""

from src.mind_daemon.detect.config import remote_config
from src.mind_daemon.detect import GestureDetector

def main():
    print("🔐 RDK X5 SSH连接测试")
    print("=" * 40)
    print(f"主机: {remote_config.host}")
    print(f"端口: {remote_config.port}")
    print(f"用户: {remote_config.username}")
    print(f"密码: {'*' * len(remote_config.password) if remote_config.password else '未设置'}")
    print(f"脚本: {remote_config.script_path}")
    print("=" * 40)
    
    # 创建手势检测器并测试连接
    detector = GestureDetector(remote_config)
    
    print("🔌 尝试SSH连接...")
    if detector.connect():
        print("✅ SSH连接成功！")
        
        # 检查服务状态
        print("📊 检查服务状态...")
        status = detector.get_status()
        print(f"连接状态: {'✅' if status.get('connected') else '❌'}")
        print(f"服务运行: {'✅' if status.get('services_running') else '❌'}")
        
        if status.get('output'):
            print(f"输出: {status['output'].strip()}")
        
        # 尝试启动服务
        if not status.get('services_running'):
            print("🚀 尝试启动服务...")
            if detector.start_services():
                print("✅ 服务启动成功")
            else:
                print("❌ 服务启动失败")
        
        detector.disconnect()
        print("✅ 连接测试完成")
        
    else:
        print("❌ SSH连接失败")
        print("💡 可能的原因：")
        print("   1. 网络连接问题")
        print("   2. 用户名或密码错误")
        print("   3. SSH服务未启动")

if __name__ == "__main__":
    main()