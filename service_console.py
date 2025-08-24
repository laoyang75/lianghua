"""
量化回测系统 - 命令行服务控制台
简单的命令行界面，用于服务管理和API测试
"""

import requests
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


class ServiceConsole:
    def __init__(self):
        self.service_port = 5318
        self.base_url = f"http://localhost:{self.service_port}"
        
    def print_banner(self):
        """打印横幅"""
        print("=" * 60)
        print("           量化回测系统 - 服务控制台")
        print("=" * 60)
        print()
        
    def print_menu(self):
        """打印主菜单"""
        print("\n" + "=" * 40)
        print("主菜单:")
        print("1. 服务管理")
        print("2. API测试")
        print("3. 查看服务状态")
        print("4. 查看服务日志")
        print("0. 退出")
        print("=" * 40)
        
    def service_management_menu(self):
        """服务管理菜单"""
        while True:
            print("\n" + "-" * 30)
            print("服务管理:")
            print("1. 启动服务")
            print("2. 停止服务") 
            print("3. 重启服务")
            print("4. 查看状态")
            print("0. 返回主菜单")
            print("-" * 30)
            
            choice = input("请选择操作 (0-4): ").strip()
            
            if choice == "1":
                self.start_service()
            elif choice == "2":
                self.stop_service()
            elif choice == "3":
                self.restart_service()
            elif choice == "4":
                self.check_service_status()
            elif choice == "0":
                break
            else:
                print("无效选择，请重试")
                
    def api_testing_menu(self):
        """API测试菜单"""
        while True:
            print("\n" + "-" * 30)
            print("API测试:")
            print("1. 健康检查")
            print("2. 数据状态")
            print("3. 标签列表")
            print("4. 策略列表")
            print("5. 自定义API调用")
            print("0. 返回主菜单")
            print("-" * 30)
            
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == "1":
                self.test_health()
            elif choice == "2":
                self.test_data_status()
            elif choice == "3":
                self.test_labels()
            elif choice == "4":
                self.test_strategies()
            elif choice == "5":
                self.custom_api_call()
            elif choice == "0":
                break
            else:
                print("无效选择，请重试")
                
    def start_service(self):
        """启动服务"""
        print("\n正在启动服务...")
        try:
            result = subprocess.run(
                [sys.executable, "service_manager.py", "start"],
                capture_output=True, text=True, cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                print("✅ 服务启动成功")
                print(result.stdout)
            else:
                print("❌ 服务启动失败")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ 启动服务时出错: {e}")
            
    def stop_service(self):
        """停止服务"""
        print("\n正在停止服务...")
        try:
            result = subprocess.run(
                [sys.executable, "service_manager.py", "stop"],
                capture_output=True, text=True, cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                print("✅ 服务停止成功")
                print(result.stdout)
            else:
                print("❌ 服务停止失败")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ 停止服务时出错: {e}")
            
    def restart_service(self):
        """重启服务"""
        print("\n正在重启服务...")
        try:
            result = subprocess.run(
                [sys.executable, "service_manager.py", "restart"],
                capture_output=True, text=True, cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                print("✅ 服务重启成功")
                print(result.stdout)
            else:
                print("❌ 服务重启失败")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ 重启服务时出错: {e}")
            
    def check_service_status(self):
        """检查服务状态"""
        print("\n正在检查服务状态...")
        try:
            result = subprocess.run(
                [sys.executable, "service_manager.py", "status"],
                capture_output=True, text=True, cwd=Path.cwd()
            )
            
            print(result.stdout)
            
        except Exception as e:
            print(f"❌ 检查状态时出错: {e}")
            
    def view_service_logs(self):
        """查看服务日志"""
        print("\n正在获取服务日志...")
        try:
            result = subprocess.run(
                [sys.executable, "service_manager.py", "logs", "--lines", "30"],
                capture_output=True, text=True, cwd=Path.cwd()
            )
            
            if result.returncode == 0:
                print("最近30行日志:")
                print("-" * 60)
                print(result.stdout)
                print("-" * 60)
            else:
                print("❌ 获取日志失败")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ 获取日志时出错: {e}")
            
    def test_api(self, endpoint, description):
        """通用API测试方法"""
        print(f"\n正在测试 {description}...")
        try:
            response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    formatted = json.dumps(data, indent=2, ensure_ascii=False)
                    print("响应数据:")
                    print("-" * 40)
                    print(formatted)
                    print("-" * 40)
                except json.JSONDecodeError:
                    print("响应内容 (非JSON):")
                    print(response.text[:500])
            else:
                print(f"❌ 请求失败: {response.text}")
                
        except requests.ConnectionError:
            print("❌ 连接失败 - 服务可能未启动")
        except requests.Timeout:
            print("❌ 请求超时")
        except Exception as e:
            print(f"❌ 请求出错: {e}")
            
    def test_health(self):
        """测试健康检查"""
        self.test_api("/healthz", "健康检查")
        
    def test_data_status(self):
        """测试数据状态"""
        self.test_api("/data/status", "数据状态")
        
    def test_labels(self):
        """测试标签列表"""
        self.test_api("/labels/list", "标签列表")
        
    def test_strategies(self):
        """测试策略列表"""
        self.test_api("/backtest/strategies", "策略列表")
        
    def custom_api_call(self):
        """自定义API调用"""
        print("\n自定义API调用:")
        endpoint = input("请输入API端点 (如: /healthz): ").strip()
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        method = input("请求方法 (GET/POST) [默认GET]: ").strip().upper()
        if not method:
            method = "GET"
            
        if method == "GET":
            self.test_api(endpoint, f"自定义API {endpoint}")
        elif method == "POST":
            print("POST请求暂不支持，请使用GUI工具进行复杂测试")
        else:
            print("暂不支持该HTTP方法")
            
    def run(self):
        """运行控制台"""
        self.print_banner()
        
        while True:
            self.print_menu()
            choice = input("请选择操作 (0-4): ").strip()
            
            if choice == "1":
                self.service_management_menu()
            elif choice == "2":
                self.api_testing_menu()
            elif choice == "3":
                self.check_service_status()
            elif choice == "4":
                self.view_service_logs()
            elif choice == "0":
                print("\n感谢使用量化回测系统服务控制台!")
                break
            else:
                print("无效选择，请重试")
                
            input("\n按 Enter 继续...")


if __name__ == "__main__":
    import os
    
    # 检查是否在正确的目录
    if not os.path.exists("service_manager.py"):
        print("❌ 未找到 service_manager.py，请在项目根目录运行此程序")
        sys.exit(1)
        
    console = ServiceConsole()
    try:
        console.run()
    except KeyboardInterrupt:
        print("\n\n程序被用户中断")
    except Exception as e:
        print(f"\n❌ 程序运行出错: {e}")
        input("按 Enter 退出...")