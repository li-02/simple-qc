"""
R脚本模块 - Windows兼容版本
"""
import os
import sys
import warnings

# 直接设置您的R路径
# R_HOME_PATH = r'C:\Program Files\R\R-4.4.2'

def setup_r_environment():
    """设置R环境变量"""
    if getattr(sys,'forzen',False):
        # 打包后的路径
        base_path=sys._MEIPASS
        R_HOME_PATH=os.path.join(base_path,'R')
    else:
        R_HOME_PATH = r'C:\Program Files\R\R-4.4.2' 


    # 设置R_HOME
    os.environ['R_HOME'] = R_HOME_PATH
    
    # 设置额外的环境变量来解决Windows兼容性问题
    os.environ['R_USER'] = os.path.expanduser('~')
    
    # 设置控制台编码以避免rpy2字符编码问题
    os.environ['R_ENCODING'] = 'UTF-8'
    os.environ['LC_ALL'] = 'C'
    
    # 设置PATH - 优先使用x64版本
    r_bin_x64 = os.path.join(R_HOME_PATH, 'bin', 'x64')
    r_bin = os.path.join(R_HOME_PATH, 'bin')
    
    current_path = os.environ.get('PATH', '')
    
    # 检查并添加合适的bin路径
    if os.path.exists(r_bin_x64):
        if r_bin_x64 not in current_path:
            os.environ['PATH'] = r_bin_x64 + os.pathsep + current_path
        print(f"R环境已设置: R_HOME={R_HOME_PATH}, BIN={r_bin_x64}")
    elif os.path.exists(r_bin):
        if r_bin not in current_path:
            os.environ['PATH'] = r_bin + os.pathsep + current_path
        print(f"R环境已设置: R_HOME={R_HOME_PATH}, BIN={r_bin}")
    else:
        print(f"警告: R bin目录不存在于 {R_HOME_PATH}")
        return False
    
    # 设置rpy2相关的环境变量
    os.environ['RPY2_CFFI_MODE'] = 'ABI'  # 使用ABI模式避免编译问题
    
    return True

def setup_rpy2_console_fix():
    """修复rpy2控制台输出问题"""
    try:
        # 导入rpy2的回调模块
        from rpy2.rinterface_lib import callbacks
        import rpy2.rinterface as rinterface
        
        # 创建一个安全的控制台写入函数
        def safe_console_write(s):
            """安全的控制台写入函数，避免编码错误"""
            try:
                if isinstance(s, bytes):
                    s = s.decode('utf-8', errors='ignore')
                elif s is None:
                    return
                
                # 简单地忽略控制台输出，避免编码问题
                pass
            except Exception:
                # 如果出现任何错误，就忽略
                pass
        
        # 替换默认的控制台写入函数（兼容不同版本的rpy2）
        try:
            callbacks.consolewrite_print = safe_console_write
            callbacks.consolewrite_warnerror = safe_console_write
        except AttributeError:
            pass
        
        # 尝试设置控制台回调（兼容性处理）
        try:
            if hasattr(rinterface, 'set_writeconsole_regular'):
                rinterface.set_writeconsole_regular(safe_console_write)
            if hasattr(rinterface, 'set_writeconsole_warnerror'):
                rinterface.set_writeconsole_warnerror(safe_console_write)
        except AttributeError:
            # 新版本的rpy2可能没有这些函数
            pass
        
        print("已设置rpy2控制台输出修复")
        return True
        
    except Exception as e:
        print(f"设置rpy2控制台修复时出错: {e}")
        return False

# 在导入rpy2之前设置R环境
print("正在配置R环境...")
setup_successful = setup_r_environment()

# 尝试导入rpy2
R_AVAILABLE = False
try:
    if setup_successful:
        print("正在导入rpy2...")
        
        # 禁用相关警告
        warnings.filterwarnings('ignore', category=UserWarning)
        warnings.filterwarnings('ignore', category=RuntimeWarning)
        warnings.filterwarnings('ignore', message='.*cffi callback.*')
        
        import rpy2.robjects as robjects
        from rpy2.robjects import vectors, pandas2ri
        
        # 设置控制台修复
        setup_rpy2_console_fix()
        
        # 激活pandas转换器
        pandas2ri.activate()
        
        # 创建便于使用的别名
        StrVector = vectors.StrVector
        FloatVector = vectors.FloatVector
        IntVector = vectors.IntVector
        
        print("正在加载R脚本...")
        # 导入R脚本，确保R函数被定义
        from . import r_gap_fill_par
        from . import r_co2_flux
        from . import r_gap_fill_all
        
        # 设置R选项来减少输出
        try:
            robjects.r('options(warn=-1)')  # 禁用R警告
            robjects.r('options(verbose=FALSE)')  # 禁用详细输出
        except:
            pass
        
        print("✓ rpy2导入成功，R环境配置完成")
        R_AVAILABLE = True
        
    else:
        raise ImportError("R环境设置失败")
        
except Exception as e:
    print(f"✗ rpy2导入失败: {e}")
    print("\n建议解决方案:")
    print("1. 降级rpy2版本: pip uninstall rpy2 && pip install rpy2==3.4.5")
    print("2. 或者尝试: pip uninstall rpy2 && pip install rpy2==3.3.6")
    print("3. 确保已安装REddyProc R包")
    print("4. 考虑使用conda安装: conda install -c conda-forge rpy2")
    
    R_AVAILABLE = False
    
    # 创建占位符以避免导入错误
    class DummyRobjects:
        r = lambda x: None
        
    class DummyVectors:
        pass
    
    robjects = DummyRobjects()
    vectors = DummyVectors()
    StrVector = lambda x: x
    FloatVector = lambda x: x
    IntVector = lambda x: x
    
    class DummyPandas2ri:
        @staticmethod
        def activate():
            pass
    
    pandas2ri = DummyPandas2ri()

# 导出供其他模块使用的符号
__all__ = [
    'robjects',
    'StrVector',
    'FloatVector', 
    'IntVector',
    'pandas2ri',
    'R_AVAILABLE'
]