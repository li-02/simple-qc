#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动打包脚本
用于将GUI应用打包为可执行文件
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_dependencies():
    """检查打包所需依赖"""
    print("检查打包依赖...")
    
    # 检查PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller版本: {PyInstaller.__version__}")
    except ImportError:
        print("✗ PyInstaller未安装, 请运行: pip install pyinstaller")
        return False
    
    # 检查statsmodels (ARIMA依赖)
    try:
        import statsmodels
        print(f"✓ statsmodels版本: {statsmodels.__version__}")
    except ImportError:
        print("✗ statsmodels未安装, 请运行: pip install statsmodels")
        return False
    
    # 检查必要文件
    required_files = [
        'gui_app.py',
        'qc_indicators.csv',
        'R-4.4.2',
        'core',
        'utils',
        'processors', 
        'r_scripts',
        'ARIMA',  # 新增检查
    ]
    
    for file in required_files:
        if not os.path.exists(file):
            print(f"✗ 缺少必要文件/目录: {file}")
            return False
        else:
            print(f"✓ 找到: {file}")
    
    return True

def clean_build():
    """清理之前的构建文件"""
    print("\n清理构建文件...")
    
    directories_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in directories_to_clean:
        if os.path.exists(dir_name):
            print(f"删除: {dir_name}")
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def build_app(spec_file='gui_app.spec'):
    """执行打包"""
    print(f"\n开始使用 {spec_file} 打包...")
    
    try:
        # 运行PyInstaller
        cmd = [sys.executable, '-m', 'PyInstaller', '--clean', spec_file]
        print(f"执行命令: {' '.join(cmd)}")
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ 打包成功!")
            
            # 检查输出文件
            if os.path.exists('dist'):
                print("\n生成的文件:")
                for item in os.listdir('dist'):
                    item_path = os.path.join('dist', item)
                    if os.path.isfile(item_path):
                        size = os.path.getsize(item_path) / (1024*1024)  # MB
                        print(f"  {item} ({size:.1f} MB)")
                    else:
                        print(f"  {item}/ (目录)")
            
            return True
        else:
            print("✗ 打包失败!")
            print("错误信息:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"✗ 打包过程出错: {str(e)}")
        return False

def main():
    """主函数"""
    print("=== SimpleQC 自动打包工具 ===")
    print(f"工作目录: {os.getcwd()}")
    
    # 检查依赖
    if not check_dependencies():
        print("\n依赖检查失败，请先安装所需依赖")
        return
    
    # 询问用户选择spec文件
    print("\n选择打包配置:")
    print("1. gui_app.spec (推荐, 简化版)")
    print("2. build.spec (完整版)")
    
    while True:
        choice = input("请选择 (1/2): ").strip()
        if choice == '1':
            spec_file = 'gui_app.spec'
            break
        elif choice == '2':
            spec_file = 'build.spec'
            break
        else:
            print("无效选择，请输入 1 或 2")
    
    # 询问是否清理
    clean = input("\n是否清理之前的构建文件? (y/N): ").strip().lower()
    if clean in ['y', 'yes']:
        clean_build()
    
    # 执行打包
    success = build_app(spec_file)
    
    if success:
        print("\n=== 打包完成 ===")
        print("可执行文件位于 dist/ 目录中")
        print("可以将整个 dist/ 目录复制到目标机器运行")
    else:
        print("\n=== 打包失败 ===")
        print("请检查错误信息并修复问题后重试")

if __name__ == "__main__":
    main() 