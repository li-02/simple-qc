#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
R环境诊断脚本
用于检查R语言和rpy2的配置状态
"""
import os
import sys
import subprocess
import platform

def check_r_installation():
    """检查R是否已安装"""
    print("=" * 50)
    print("检查R语言安装状态")
    print("=" * 50)
    
    try:
        # 尝试运行R --version命令
        result = subprocess.run(['R', '--version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ R语言已安装")
            print(f"版本信息: {result.stdout.split()[2]}")
            return True
        else:
            print("✗ R语言未正确安装或未加入PATH")
            return False
    except FileNotFoundError:
        print("✗ R语言未安装或未加入PATH")
        return False
    except subprocess.TimeoutExpired:
        print("✗ R命令执行超时")
        return False

def check_r_home():
    """检查R_HOME环境变量"""
    print("\n" + "=" * 50)
    print("检查R_HOME环境变量")
    print("=" * 50)
    
    r_home = os.environ.get('R_HOME')
    if r_home:
        print(f"✓ R_HOME已设置: {r_home}")
        if os.path.exists(r_home):
            print("✓ R_HOME路径存在")
            return True
        else:
            print("✗ R_HOME路径不存在")
            return False
    else:
        print("✗ R_HOME未设置")
        return False

def find_r_installations():
    """查找R安装路径"""
    print("\n" + "=" * 50)
    print("搜索R安装路径")
    print("=" * 50)
    
    possible_paths = [
        r'C:\Program Files\R',
        r'C:\Program Files (x86)\R',
        r'D:\Program Files\R',
        r'D:\R',
    ]
    
    found_installations = []
    
    for base_path in possible_paths:
        if os.path.exists(base_path):
            for item in os.listdir(base_path):
                full_path = os.path.join(base_path, item)
                if os.path.isdir(full_path) and item.startswith('R-'):
                    found_installations.append(full_path)
                    print(f"找到R安装: {full_path}")
    
    if not found_installations:
        print("未找到R安装")
    
    return found_installations

def check_r_packages():
    """检查R包安装状态"""
    print("\n" + "=" * 50)
    print("检查R包安装状态")
    print("=" * 50)
    
    required_packages = ['REddyProc', 'dplyr']
    
    for package in required_packages:
        try:
            cmd = ['R', '--slave', '-e', f'packageVersion("{package}")']
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0 and 'Error' not in result.stderr:
                print(f"✓ {package} 已安装")
            else:
                print(f"✗ {package} 未安装")
                print(f"  安装命令: install.packages('{package}')")
        except:
            print(f"✗ 无法检查 {package} 安装状态")

def check_rpy2():
    """检查rpy2安装状态"""
    print("\n" + "=" * 50)
    print("检查rpy2安装状态")
    print("=" * 50)
    
    try:
        import rpy2
        print(f"✓ rpy2已安装，版本: {rpy2.__version__}")
        
        try:
            import rpy2.robjects as robjects
            print("✓ rpy2.robjects导入成功")
            
            # 尝试简单的R命令
            result = robjects.r('R.version.string')
            print(f"✓ R连接成功: {str(result[0])}")
            return True
            
        except Exception as e:
            print(f"✗ rpy2.robjects导入失败: {e}")
            return False
            
    except ImportError:
        print("✗ rpy2未安装")
        print("  安装命令: pip install rpy2")
        return False

def provide_solutions():
    """提供解决方案"""
    print("\n" + "=" * 50)
    print("解决方案建议")
    print("=" * 50)
    
    installations = find_r_installations()
    
    if installations:
        latest_r = max(installations)  # 假设按字母顺序排序，最后一个是最新的
        print(f"\n建议设置环境变量:")
        print(f"R_HOME={latest_r}")
        print(f"PATH=%PATH%;{latest_r}\\bin\\x64")
        
        print(f"\n或者在Python代码中设置:")
        print(f"import os")
        print(f"os.environ['R_HOME'] = r'{latest_r}'")
        
    else:
        print("\n1. 安装R语言:")
        print("   - 访问 https://cran.r-project.org/bin/windows/base/")
        print("   - 下载并安装最新版本的R")
        
    print("\n2. 安装R包 (在R控制台中运行):")
    print("   install.packages('REddyProc')")
    print("   install.packages('dplyr')")
    
    print("\n3. 安装rpy2:")
    print("   pip install rpy2")

def main():
    """主函数"""
    print("R环境诊断工具")
    print(f"Python版本: {sys.version}")
    print(f"操作系统: {platform.system()} {platform.release()}")
    
    r_installed = check_r_installation()
    r_home_ok = check_r_home()
    
    if not r_home_ok:
        find_r_installations()
    
    if r_installed:
        check_r_packages()
    
    rpy2_ok = check_rpy2()
    
    if not (r_installed and rpy2_ok):
        provide_solutions()
    else:
        print("\n" + "=" * 50)
        print("✓ R环境配置完成！可以正常使用。")
        print("=" * 50)

if __name__ == "__main__":
    main()