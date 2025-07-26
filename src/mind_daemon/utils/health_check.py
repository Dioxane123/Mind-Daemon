"""
Mind Daemon 系统健康检查模块 - 启动前验证所有关键组件

功能：
- 测试LLM API连接（MiniMax, OpenAI等）
- 验证BCI设备连接
- 检查配置文件完整性
- 验证数据存储路径
- 测试外设控制功能

作者：Mind Daemon Project
"""

import os
import sys
import time
import json
import asyncio
import requests
import subprocess
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from .config import config
logger = logging.getLogger(__name__)

try:
    from ..analyzers.llm_analyzer import LLMAnalyzer
    HAS_LLM_ANALYZER = True
except ImportError:
    HAS_LLM_ANALYZER = False
    logger.warning("LLMAnalyzer not available for health check")

@dataclass
class HealthCheckResult:
    """健康检查结果"""
    component: str
    status: str  # "pass", "fail", "warning"
    message: str
    details: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

@dataclass
class SystemHealthReport:
    """系统健康报告"""
    timestamp: str
    overall_status: str  # "healthy", "degraded", "critical"
    total_checks: int
    passed_checks: int
    failed_checks: int
    warning_checks: int
    results: List[HealthCheckResult]
    recommendations: List[str]

class HealthChecker:
    """系统健康检查器"""
    
    def __init__(self):
        self.results: List[HealthCheckResult] = []
        self.config = config
        
    def run_all_checks(self) -> SystemHealthReport:
        """运行所有健康检查"""
        logger.info("🔍 开始系统健康检查...")
        
        self.results = []
        
        # 基础配置检查
        self._check_configuration()
        
        # 数据存储检查
        self._check_data_directories()
        
        # LLM API检查
        self._check_llm_apis()
        
        # BCI连接检查
        self._check_bci_connection()
        
        # 外设检查
        self._check_peripherals()
        
        # 网络连接检查
        self._check_network_connectivity()
        
        # 生成报告
        return self._generate_report()
    
    def _check_configuration(self):
        """检查配置文件完整性"""
        start_time = time.time()
        
        try:
            # 检查必需的配置项
            required_configs = [
                'MUSIC_DIR',
                'DATA_DIR', 
                'WINDOW_PY_PATH',
                'WEBSOCKET_HOST',
                'WEBSOCKET_PORT'
            ]
            
            missing_configs = []
            for key in required_configs:
                value = self.config.get(key)
                if not value:
                    missing_configs.append(key)
            
            duration = (time.time() - start_time) * 1000
            
            if missing_configs:
                self.results.append(HealthCheckResult(
                    component="Configuration",
                    status="warning",
                    message=f"缺少配置项: {', '.join(missing_configs)}",
                    details={"missing_configs": missing_configs},
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Configuration",
                    status="pass",
                    message="所有必需配置项已正确设置",
                    duration_ms=duration
                ))
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="Configuration",
                status="fail",
                message=f"配置检查失败: {str(e)}",
                duration_ms=duration
            ))
    
    def _check_data_directories(self):
        """检查数据存储目录"""
        start_time = time.time()
        
        try:
            directories_to_check = [
                ('DATA_DIR', '数据存储目录'),
                ('MUSIC_DIR', '音乐文件目录')
            ]
            
            issues = []
            for config_key, desc in directories_to_check:
                path = self.config.get(config_key)
                if path:
                    if not os.path.exists(path):
                        try:
                            os.makedirs(path, exist_ok=True)
                            logger.info(f"创建目录: {path}")
                        except Exception as e:
                            issues.append(f"{desc}创建失败: {str(e)}")
                    elif not os.access(path, os.W_OK):
                        issues.append(f"{desc}无写入权限: {path}")
                else:
                    issues.append(f"{desc}未配置")
            
            duration = (time.time() - start_time) * 1000
            
            if issues:
                self.results.append(HealthCheckResult(
                    component="Data Directories",
                    status="fail",
                    message=f"目录检查失败: {'; '.join(issues)}",
                    details={"issues": issues},
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Data Directories",
                    status="pass",
                    message="所有数据目录检查通过",
                    duration_ms=duration
                ))
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="Data Directories",
                status="fail",
                message=f"目录检查异常: {str(e)}",
                duration_ms=duration
            ))
    
    def _check_llm_apis(self):
        """检查LLM API连接"""
        
        # 检查MiniMax API
        self._check_minimax_api()
        
        # 检查OpenAI API (如果配置了)
        self._check_openai_api()
    
    def _check_minimax_api(self):
        """检查MiniMax API连接"""
        start_time = time.time()
        
        try:
            api_key = self.config.get('MINIMAX_API_KEY')
            base_url = self.config.get('MINIMAX_BASE_URL')
            
            if not api_key:
                duration = (time.time() - start_time) * 1000
                self.results.append(HealthCheckResult(
                    component="MiniMax API",
                    status="warning",
                    message="MiniMax API Key未配置",
                    details={"reason": "API密钥缺失"},
                    duration_ms=duration
                ))
                return
            
            # 测试API连接（发送简单请求）
            test_prompt = "请回复'连接测试成功'"
            
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            # MiniMax API测试请求
            data = {
                'model': self.config.get('MINIMAX_MODEL', 'MiniMax-Text-01'),
                'messages': [
                    {
                        'role': 'user',
                        'content': test_prompt
                    }
                ],
                'max_tokens': 50,
                'temperature': 0.1
            }
            
            response = requests.post(
                base_url,
                headers=headers,
                json=data,
                timeout=10
            )
            
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.results.append(HealthCheckResult(
                    component="MiniMax API",
                    status="pass",
                    message="MiniMax API连接成功",
                    details={
                        "status_code": response.status_code,
                        "response_time_ms": duration
                    },
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="MiniMax API",
                    status="fail",
                    message=f"MiniMax API连接失败: HTTP {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "response": response.text[:200]
                    },
                    duration_ms=duration
                ))
                
        except requests.exceptions.Timeout:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="MiniMax API",
                status="fail",
                message="MiniMax API请求超时",
                details={"reason": "timeout"},
                duration_ms=duration
            ))
        except requests.exceptions.RequestException as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="MiniMax API",
                status="fail",
                message=f"MiniMax API请求异常: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="MiniMax API",
                status="fail",
                message=f"MiniMax API检查失败: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
    
    def _check_openai_api(self):
        """检查OpenAI API连接"""
        start_time = time.time()
        
        try:
            api_key = self.config.get('OPENAI_API_KEY')
            
            if not api_key:
                duration = (time.time() - start_time) * 1000
                self.results.append(HealthCheckResult(
                    component="OpenAI API",
                    status="warning",
                    message="OpenAI API Key未配置（可选）",
                    details={"reason": "API密钥缺失"},
                    duration_ms=duration
                ))
                return
                
            # 测试OpenAI API连接
            headers = {
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.config.get('OPENAI_MODEL', 'gpt-3.5-turbo'),
                'messages': [
                    {
                        'role': 'user',
                        'content': '请回复"连接测试成功"'
                    }
                ],
                'max_tokens': 50,
                'temperature': 0.1
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=10
            )
            
            duration = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                self.results.append(HealthCheckResult(
                    component="OpenAI API",
                    status="pass",
                    message="OpenAI API连接成功",
                    details={
                        "status_code": response.status_code,
                        "response_time_ms": duration
                    },
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="OpenAI API",
                    status="fail",
                    message=f"OpenAI API连接失败: HTTP {response.status_code}",
                    details={
                        "status_code": response.status_code,
                        "response": response.text[:200]
                    },
                    duration_ms=duration
                ))
                
        except requests.exceptions.Timeout:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="OpenAI API",
                status="fail",
                message="OpenAI API请求超时",
                details={"reason": "timeout"},
                duration_ms=duration
            ))
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="OpenAI API",
                status="fail",
                message=f"OpenAI API检查失败: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
    
    def _check_bci_connection(self):
        """检查BCI设备连接"""
        start_time = time.time()
        
        try:
            client_id = self.config.get('EMOTIV_CLIENT_ID')
            client_secret = self.config.get('EMOTIV_CLIENT_SECRET')
            
            if not client_id or not client_secret:
                duration = (time.time() - start_time) * 1000
                self.results.append(HealthCheckResult(
                    component="BCI Connection",
                    status="warning",
                    message="Emotiv BCI凭证未配置，将使用开发模式",
                    details={
                        "has_client_id": bool(client_id),
                        "has_client_secret": bool(client_secret),
                        "dev_mode": self.config.get('DEV_MODE', False)
                    },
                    duration_ms=duration
                ))
                return
            
            # 这里可以添加实际的BCI连接测试
            # 由于BCI连接比较复杂，现在只检查凭证是否存在
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="BCI Connection",
                status="pass",
                message="BCI凭证已配置，连接测试需要实际设备",
                details={
                    "credentials_configured": True,
                    "note": "需要实际BCI设备进行完整测试"
                },
                duration_ms=duration
            ))
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="BCI Connection",
                status="fail",
                message=f"BCI连接检查失败: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
    
    def _check_peripherals(self):
        """检查外设控制功能"""
        start_time = time.time()
        
        try:
            # 检查光晕控制器
            window_py_path = self.config.get('WINDOW_PY_PATH')
            
            issues = []
            
            if not window_py_path:
                issues.append("光晕控制器路径未配置")
            elif not os.path.exists(window_py_path):
                issues.append(f"光晕控制器文件不存在: {window_py_path}")
            elif not os.access(window_py_path, os.R_OK):
                issues.append(f"光晕控制器文件无读取权限: {window_py_path}")
            
            # 检查音乐目录
            music_dir = self.config.get('MUSIC_DIR')
            if music_dir and os.path.exists(music_dir):
                focus_dir = os.path.join(music_dir, 'focus')
                relax_dir = os.path.join(music_dir, 'relax')
                
                if not os.path.exists(focus_dir):
                    issues.append("专注音乐目录不存在")
                elif not os.listdir(focus_dir):
                    issues.append("专注音乐目录为空")
                
                if not os.path.exists(relax_dir):
                    issues.append("放松音乐目录不存在")
                elif not os.listdir(relax_dir):
                    issues.append("放松音乐目录为空")
            
            duration = (time.time() - start_time) * 1000
            
            if issues:
                self.results.append(HealthCheckResult(
                    component="Peripherals",
                    status="warning",
                    message=f"外设检查发现问题: {'; '.join(issues)}",
                    details={"issues": issues},
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Peripherals",
                    status="pass",
                    message="外设控制功能检查通过",
                    duration_ms=duration
                ))
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="Peripherals",
                status="fail",
                message=f"外设检查失败: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
    
    def _check_network_connectivity(self):
        """检查网络连接"""
        start_time = time.time()
        
        try:
            # 测试基本网络连接
            test_urls = [
                'https://www.google.com',
                'https://api.openai.com',
                'https://api.minimax.chat'
            ]
            
            connectivity_results = {}
            for url in test_urls:
                try:
                    response = requests.get(url, timeout=5)
                    connectivity_results[url] = {
                        "status": "success",
                        "status_code": response.status_code
                    }
                except Exception as e:
                    connectivity_results[url] = {
                        "status": "failed",
                        "error": str(e)
                    }
            
            duration = (time.time() - start_time) * 1000
            
            # 检查是否有成功的连接
            successful_connections = sum(1 for result in connectivity_results.values() 
                                       if result["status"] == "success")
            
            if successful_connections > 0:
                self.results.append(HealthCheckResult(
                    component="Network Connectivity",
                    status="pass",
                    message=f"网络连接正常 ({successful_connections}/{len(test_urls)}个测试通过)",
                    details=connectivity_results,
                    duration_ms=duration
                ))
            else:
                self.results.append(HealthCheckResult(
                    component="Network Connectivity",
                    status="fail",
                    message="网络连接失败，所有测试URL均无法访问",
                    details=connectivity_results,
                    duration_ms=duration
                ))
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.results.append(HealthCheckResult(
                component="Network Connectivity",
                status="fail",
                message=f"网络连接检查异常: {str(e)}",
                details={"error": str(e)},
                duration_ms=duration
            ))
    
    def _generate_report(self) -> SystemHealthReport:
        """生成健康检查报告"""
        
        passed = sum(1 for result in self.results if result.status == "pass")
        failed = sum(1 for result in self.results if result.status == "fail")
        warnings = sum(1 for result in self.results if result.status == "warning")
        
        # 确定整体状态
        overall_status = "healthy"
        if failed > 0:
            overall_status = "critical"
        elif warnings > 0:
            overall_status = "degraded"
        
        # 生成建议
        recommendations = []
        
        for result in self.results:
            if result.status == "fail":
                if "API" in result.component:
                    recommendations.append(f"检查{result.component}配置和网络连接")
                elif "BCI" in result.component:
                    recommendations.append("确保BCI设备已连接并配置正确的凭证")
                elif "Configuration" in result.component:
                    recommendations.append("完善系统配置文件")
                elif "Data Directories" in result.component:
                    recommendations.append("检查数据目录权限和存储空间")
                elif "Peripherals" in result.component:
                    recommendations.append("检查外设文件和音乐资源")
                elif "Network" in result.component:
                    recommendations.append("检查网络连接和防火墙设置")
            elif result.status == "warning":
                if "API" in result.component:
                    recommendations.append(f"考虑配置{result.component}以获得完整功能")
        
        if not recommendations:
            recommendations.append("系统状态良好，建议定期进行健康检查")
        
        return SystemHealthReport(
            timestamp=datetime.now().isoformat(),
            overall_status=overall_status,
            total_checks=len(self.results),
            passed_checks=passed,
            failed_checks=failed,
            warning_checks=warnings,
            results=self.results,
            recommendations=list(set(recommendations))  # 去重
        )

def run_health_check() -> SystemHealthReport:
    """运行系统健康检查并返回报告"""
    checker = HealthChecker()
    return checker.run_all_checks()

def print_health_report(report: SystemHealthReport, verbose: bool = False):
    """打印健康检查报告"""
    
    # 状态图标
    status_icons = {
        "healthy": "✅",
        "degraded": "⚠️", 
        "critical": "❌"
    }
    
    # 组件状态图标
    component_icons = {
        "pass": "✅",
        "fail": "❌",
        "warning": "⚠️"
    }
    
    print(f"\n🏥 Mind Daemon 系统健康检查报告")
    print(f"{'='*50}")
    print(f"检查时间: {report.timestamp}")
    print(f"整体状态: {status_icons.get(report.overall_status, '❓')} {report.overall_status.upper()}")
    print(f"总检查项: {report.total_checks}")
    print(f"通过: {report.passed_checks} | 警告: {report.warning_checks} | 失败: {report.failed_checks}")
    
    print(f"\n📋 检查结果:")
    for result in report.results:
        icon = component_icons.get(result.status, "❓")
        duration_info = f" ({result.duration_ms:.0f}ms)" if result.duration_ms else ""
        print(f"  {icon} {result.component}: {result.message}{duration_info}")
        
        if verbose and result.details:
            print(f"      详情: {json.dumps(result.details, ensure_ascii=False, indent=6)}")
    
    if report.recommendations:
        print(f"\n💡 建议:")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")
    
    print(f"\n{'='*50}")

def main():
    """主函数 - 命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Mind Daemon 系统健康检查')
    parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    parser.add_argument('--json', action='store_true', help='输出JSON格式')
    parser.add_argument('--save', type=str, help='保存报告到文件')
    
    args = parser.parse_args()
    
    # 运行健康检查
    report = run_health_check()
    
    if args.json:
        # JSON输出
        json_report = asdict(report)
        print(json.dumps(json_report, ensure_ascii=False, indent=2))
    else:
        # 标准输出
        print_health_report(report, verbose=args.verbose)
    
    # 保存报告
    if args.save:
        try:
            with open(args.save, 'w', encoding='utf-8') as f:
                json.dump(asdict(report), f, ensure_ascii=False, indent=2)
            print(f"\n报告已保存到: {args.save}")
        except Exception as e:
            print(f"\n保存报告失败: {e}")
    
    # 根据整体状态设置退出码
    if report.overall_status == "critical":
        sys.exit(1)
    elif report.overall_status == "degraded":
        sys.exit(2)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()