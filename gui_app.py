#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据质量控制GUI应用
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import os
import datetime
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import io
from contextlib import redirect_stdout, redirect_stderr

# pandas兼容性补丁 - 修复iteritems问题
def _fix_pandas_compatibility():
    """修复pandas版本兼容性问题"""
    import pandas as pd
    if not hasattr(pd.DataFrame, 'iteritems'):
        pd.DataFrame.iteritems = pd.DataFrame.items
    if not hasattr(pd.Series, 'iteritems'):
        pd.Series.iteritems = pd.Series.items

_fix_pandas_compatibility()

# 抑制rpy2相关的警告和错误输出
import warnings
import sys
warnings.filterwarnings('ignore')

# 重定向stderr以抑制cffi错误消息
class SuppressStderr:
    def __enter__(self):
        self.old_stderr = sys.stderr
        sys.stderr = open(os.devnull, 'w')
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stderr.close()
        sys.stderr = self.old_stderr

# 检查R语言依赖
R_AVAILABLE = False
R_ERROR_MSG = ""

try:
    # 首先尝试设置R环境
    import os
    import sys
    
    # 可能的R安装路径
    possible_r_paths = [
        r'C:\Program Files\R\R-4.4.2',
        r'C:\Program Files\R\R-4.3.3',
        r'C:\Program Files\R\R-4.3.2',
        r'C:\Program Files (x86)\R\R-4.4.2',
        r'C:\Program Files (x86)\R\R-4.3.3',
    ]
    
    # 查找并设置R_HOME
    for r_path in possible_r_paths:
        if os.path.exists(r_path):
            os.environ['R_HOME'] = r_path
            r_bin = os.path.join(r_path, 'bin', 'x64')
            if os.path.exists(r_bin):
                os.environ['PATH'] = r_bin + os.pathsep + os.environ.get('PATH', '')
            break
    
    # 抑制rpy2导入时的错误输出
    with SuppressStderr():
        # 导入您的数据处理模块
        from core.data_qc import DataQc
        from utils.fill_time import fill_time
        from utils.validators import validate_args
    R_AVAILABLE = True
    
except ImportError as e:
    R_ERROR_MSG = f"R语言相关模块导入失败: {str(e)}"
    print(f"警告: {R_ERROR_MSG}")
    
    # 创建模拟的类和函数以避免导入错误
    class DataQc:
        def __init__(self, **kwargs):
            pass
        def data_qc(self):
            raise Exception("R语言环境未正确配置")
    
    def fill_time(data, time_freq="30min"):
        return data
    
    def validate_args(args):
        return True, []


class DataQCGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("数据质量控制工具")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # 设置窗口图标（可选）
        # self.root.iconbitmap("icon.ico")
        
        # 变量
        self.file_path = tk.StringVar()
        self.data_type = tk.StringVar(value="flux")
        self.ftp_name = tk.StringVar(value="shisanling")
        self.longitude = tk.DoubleVar(value=116.28824)
        self.latitude = tk.DoubleVar(value=40.265635)
        self.is_strg = tk.IntVar(value=0)
        self.despiking_z = tk.DoubleVar(value=4.0)
        self.is_processing = False
        
        # GUI日志处理器
        self.gui_logger = GUILogHandler(self)
        
        # 加载QC指标
        self.qc_indicators = self.load_qc_indicators()
        
        # 先创建界面组件
        self.create_widgets()
        
        # 然后检查R语言环境（这时log_text已经创建）
        self.check_r_environment()
        
    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="数据质量控制工具", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # 文件选择区域
        file_frame = ttk.LabelFrame(main_frame, text="文件选择", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)
        
        ttk.Label(file_frame, text="数据文件:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=50)
        file_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        ttk.Button(file_frame, text="浏览", command=self.browse_file).grid(row=0, column=2)
        
        # 参数配置区域
        config_frame = ttk.LabelFrame(main_frame, text="参数配置", padding="10")
        config_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        config_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(3, weight=1)
        
        # 数据类型
        ttk.Label(config_frame, text="数据类型:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        data_type_frame = ttk.Frame(config_frame)
        data_type_frame.grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        
        data_types = [("flux", "flux"), ("aqi", "aqi"), ("nai", "nai"), ("sapflow", "sapflow")]
        for i, (text, value) in enumerate(data_types):
            ttk.Radiobutton(data_type_frame, text=text, variable=self.data_type, 
                           value=value).grid(row=0, column=i, padx=(0, 10))
        
        # 站点名称
        ttk.Label(config_frame, text="站点名称:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        ttk.Entry(config_frame, textvariable=self.ftp_name, width=15).grid(row=0, column=3, sticky=tk.W)
        
        # 经度
        ttk.Label(config_frame, text="经度:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Entry(config_frame, textvariable=self.longitude, width=15).grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        
        # 纬度
        ttk.Label(config_frame, text="纬度:").grid(row=1, column=2, sticky=tk.W, padx=(0, 10), pady=(10, 0))
        ttk.Entry(config_frame, textvariable=self.latitude, width=15).grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        
        # 高级选项
        # advanced_frame = ttk.LabelFrame(main_frame, text="高级选项", padding="10")
        # advanced_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        # advanced_frame.columnconfigure(1, weight=1)
        # advanced_frame.columnconfigure(3, weight=1)
        
        # # 存储项校正
        # ttk.Checkbutton(advanced_frame, text="进行存储项校正", 
        #                variable=self.is_strg).grid(row=0, column=0, sticky=tk.W, padx=(0, 20))
        
        # # 去噪声Z值
        # ttk.Label(advanced_frame, text="去噪声Z值:").grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        # ttk.Entry(advanced_frame, textvariable=self.despiking_z, width=10).grid(row=0, column=2, sticky=tk.W)
        
        # 控制按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        self.start_button = ttk.Button(button_frame, text="开始处理", 
                                      command=self.start_processing, 
                                      style="Accent.TButton")
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="停止处理", 
                                     command=self.stop_processing, 
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="清空日志", 
                  command=self.clear_log).pack(side=tk.LEFT)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 状态标签
        self.status_label = ttk.Label(main_frame, text="就绪", foreground="green")
        self.status_label.grid(row=5, column=0, columnspan=3, pady=(0, 10))
        
        # 输出日志区域
        log_frame = ttk.LabelFrame(main_frame, text="运行日志", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80, 
                                                 wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 结果区域
        result_frame = ttk.LabelFrame(main_frame, text="处理结果", padding="10")
        result_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        result_frame.columnconfigure(1, weight=1)
        
        self.result_label = ttk.Label(result_frame, text="等待处理...")
        self.result_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        self.save_button = ttk.Button(result_frame, text="保存结果", 
                                     command=self.save_result, state=tk.DISABLED)
        self.save_button.grid(row=0, column=1, sticky=tk.E)
        
        # 存储结果数据
        self.result_data = None
        
    def load_qc_indicators(self):
        """加载QC指标"""
        try:
            qc_indicators = pd.read_csv("qc_indicators.csv")
            return qc_indicators.to_dict("records")
        except Exception as e:
            # 在界面创建之前，使用print而不是log_message
            print(f"警告: 无法加载QC指标文件: {str(e)}")
            return []
    
    def check_r_environment(self):
        """检查R语言环境"""
        if not R_AVAILABLE:
            self.log_message(f"警告: {R_ERROR_MSG}")
            self.log_message("请检查以下项目:")
            self.log_message("1. 确保已安装R语言 (https://www.r-project.org/)")
            self.log_message("2. 确保已安装rpy2: pip install rpy2")
            self.log_message("3. 确保已安装REddyProc R包: install.packages('REddyProc')")
            self.log_message("4. 检查R_HOME环境变量是否正确设置")
        else:
            self.log_message("R语言环境检查通过")
        
    def browse_file(self):
        """浏览文件"""
        file_path = filedialog.askopenfilename(
            title="选择数据文件",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx;*.xls"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.file_path.set(file_path)
            self.log_message(f"已选择文件: {file_path}")
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete(1.0, tk.END)
    
    def validate_inputs(self):
        """验证输入参数"""
        if not R_AVAILABLE:
            messagebox.showerror("错误", f"R语言环境未正确配置:\n{R_ERROR_MSG}\n\n请先安装和配置R语言环境")
            return False
            
        if not self.file_path.get():
            messagebox.showerror("错误", "请选择数据文件")
            return False
            
        if not os.path.exists(self.file_path.get()):
            messagebox.showerror("错误", "文件不存在")
            return False
            
        if not self.ftp_name.get().strip():
            messagebox.showerror("错误", "请输入站点名称")
            return False
            
        if not (-180 <= self.longitude.get() <= 180):
            messagebox.showerror("错误", "经度必须在-180到180之间")
            return False
            
        if not (-90 <= self.latitude.get() <= 90):
            messagebox.showerror("错误", "纬度必须在-90到90之间")
            return False
            
        return True
    
    def start_processing(self):
        """开始处理"""
        if not self.validate_inputs():
            return
            
        self.is_processing = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.save_button.config(state=tk.DISABLED)
        self.progress.start()
        self.status_label.config(text="正在处理...", foreground="orange")
        
        # 清空之前的结果
        self.result_data = None
        self.result_label.config(text="处理中...")
        
        self.log_message("开始数据质量控制处理")
        self.log_message(f"文件: {self.file_path.get()}")
        self.log_message(f"数据类型: {self.data_type.get()}")
        self.log_message(f"站点: {self.ftp_name.get()}")
        self.log_message(f"坐标: ({self.longitude.get()}, {self.latitude.get()})")
        
        # 在后台线程中运行处理
        processing_thread = threading.Thread(target=self.run_data_qc)
        processing_thread.daemon = True
        processing_thread.start()
    
    def stop_processing(self):
        """停止处理"""
        self.is_processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.status_label.config(text="已停止", foreground="red")
        self.log_message("用户停止了处理")
    
    def run_data_qc(self):
        """运行数据质量控制（在后台线程中）"""
        try:
            try:
                # 在新线程中重新激活pandas转换器
                from rpy2.robjects import pandas2ri
                from rpy2.robjects.conversion import localconverter
                pandas2ri.activate()
                self.log_message("已在新线程中重新激活pandas转换器")
            except Exception as e:
                self.log_message(f"重新激活pandas转换器失败: {str(e)}")
                
            # 创建参数对象
            class Args:
                def __init__(self, file_path, data_type, ftp, longitude, latitude, is_strg, despiking_z):
                    self.file_path = file_path
                    self.data_type = data_type
                    self.ftp = ftp
                    self.longitude = longitude
                    self.latitude = latitude
                    self.is_strg = str(is_strg)
                    self.despiking_z = despiking_z
            
            args = Args(
                self.file_path.get(),
                self.data_type.get(),
                self.ftp_name.get(),
                self.longitude.get(),
                self.latitude.get(),
                self.is_strg.get(),
                self.despiking_z.get()
            )
            
            # 验证参数
            self.log_message("正在验证输入参数...")
            from utils.validators import validate_args
            valid, error_msgs = validate_args(args)
            if not valid:
                error_message = "\n".join(error_msgs)
                self.root.after(0, lambda: self.processing_failed(error_message))
                return
                
            if not self.is_processing:
                return
            
            # 创建任务ID
            task_id = args.ftp + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            self.log_message(f"创建任务ID: {task_id}")
            
            # 读取数据
            self.log_message("正在读取数据文件...")
            try:
                data = pd.read_csv(args.file_path)
                self.log_message(f"数据行数: {len(data)}")
                if 'record_time' in data.columns:
                    self.log_message(f"数据时间范围：{data['record_time'].min()} 至 {data['record_time'].max()}")
            except Exception as e:
                self.root.after(0, lambda: self.processing_failed(f"读取数据文件失败: {str(e)}"))
                return
                
            if not self.is_processing:
                return
            
            # 确保数据文件时间间隔为半小时
            self.log_message("正在处理时间序列...")
            data = fill_time(data, time_freq="auto")
            
            if not self.is_processing:
                return
            
            # 检查QC指标
            if not self.qc_indicators:
                self.root.after(0, lambda: self.processing_failed("无法加载QC指标文件"))
                return
            
            # 创建数据质量控制对象
            self.log_message(f"开始执行{args.data_type}类型数据的质量控制...")
            dc = DataQc(
                task_id=task_id,
                data=data,
                data_type=args.data_type,
                ftp=args.ftp,
                qc_indicators=self.qc_indicators,
                qc_flag_list=["0", "1", "2"],
                is_strg=args.is_strg,
                despiking_z=args.despiking_z,
                longitude=args.longitude,
                latitude=args.latitude,
                timezone=8,
                filename=args.file_path,
                logger=self.gui_logger,
            )
            
            if not self.is_processing:
                return
            
            # 执行质量控制
            self.log_message("正在执行数据质量控制...")
            processed_data = dc.data_qc()
            
            if not self.is_processing:
                return
            
            # 保存结果数据
            self.result_data = processed_data
            
            # 生成输出文件名
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            self.output_filename = f"{args.ftp}_{args.data_type}_{timestamp}.csv"
            
            # 在主线程中完成处理
            self.root.after(0, self.processing_completed)
            
        except Exception as e:
            error_message = f"处理过程中发生错误: {str(e)}"
            self.root.after(0, lambda: self.processing_failed(error_message))
    
    def processing_completed(self):
        """处理完成"""
        self.is_processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()
        self.status_label.config(text="处理完成", foreground="green")
        
        self.log_message("数据质量控制处理完成!")
        self.log_message(f"处理后数据行数: {len(self.result_data) if self.result_data is not None else 0}")
        
        # 在主线程中弹出保存对话框
        self.root.after(100, self.auto_save_result)  # 延迟100ms确保界面更新完成

    def auto_save_result(self):
        """处理完成后自动弹出保存对话框"""
        if self.result_data is None:
            self.log_message("错误: 没有可保存的结果数据")
            return
        
        # 使用建议的文件名作为默认名
        default_name = getattr(self, 'output_filename', 'processed_data.csv')
        
        self.log_message("请选择保存位置...")
        
        try:
            file_path = filedialog.asksaveasfilename(
                parent=self.root,  # 明确指定父窗口
                title="选择保存位置 - 数据处理结果",
                initialfile=default_name,  # 改为 initialfile
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                try:
                    # 保存文件
                    if file_path.endswith('.xlsx'):
                        self.result_data.to_excel(file_path, index=False)
                    else:
                        self.result_data.to_csv(file_path, index=False)
                    
                    # 获取完整的绝对路径
                    absolute_path = os.path.abspath(file_path)
                    
                    self.log_message(f"结果已保存到: {absolute_path}")
                    self.result_label.config(text=f"已保存: {os.path.basename(absolute_path)}")
                    
                    # 显示保存成功信息
                    message = f"数据处理结果已成功保存!\n\n保存位置:\n{absolute_path}"
                    messagebox.showinfo("保存成功", message)
                    
                    # 将路径复制到剪贴板方便用户使用
                    try:
                        self.root.clipboard_clear()
                        self.root.clipboard_append(absolute_path)
                        self.log_message("文件路径已复制到剪贴板")
                    except:
                        pass
                    
                    # 保存成功后启用手动保存按钮（以防用户想要保存到其他位置）
                    self.save_button.config(state=tk.NORMAL)
                        
                except Exception as e:
                    self.log_message(f"保存失败: {str(e)}")
                    messagebox.showerror("保存失败", f"无法保存文件:\n{str(e)}")
                    # 保存失败也要启用保存按钮，让用户重试
                    self.save_button.config(state=tk.NORMAL)
            else:
                # 用户取消了保存，启用保存按钮让用户稍后可以手动保存
                self.log_message("用户取消了保存，可稍后手动保存")
                self.result_label.config(text="处理完成，等待保存...")
                self.save_button.config(state=tk.NORMAL)
                
        except Exception as e:
            self.log_message(f"打开保存对话框失败: {str(e)}")
            # 如果对话框无法打开，也要启用保存按钮
            self.save_button.config(state=tk.NORMAL)

    def processing_failed(self, error_message):
        """处理失败"""
        self.is_processing = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress.stop()    
        self.status_label.config(text="处理失败", foreground="red")
            
        self.log_message(f"错误: {error_message}")
        self.result_label.config(text="处理失败")
            
        messagebox.showerror("错误", error_message)
        
    def save_result(self):
        """保存结果"""
        if self.result_data is None:
            messagebox.showwarning("警告", "没有可保存的结果数据")
            return
                
        # 使用建议的文件名作为默认名
        default_name = getattr(self, 'output_filename', 'processed_data.csv')
            
        file_path = filedialog.asksaveasfilename(
                title="保存结果文件",
                initialfile=default_name,
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx"),
                    ("All files", "*.*")
                ]
            )
            
        if file_path:
            try:
                # 保存实际的结果数据
                if file_path.endswith('.xlsx'):
                    self.result_data.to_excel(file_path, index=False)
                else:
                    self.result_data.to_csv(file_path, index=False)
                        
                self.log_message(f"结果已保存到: {file_path}")
                messagebox.showinfo("成功", f"结果已保存到:\n{file_path}")
            except Exception as e:
                self.log_message(f"保存失败: {str(e)}")
                messagebox.showerror("错误", f"保存失败: {str(e)}")


class GUILogHandler:
    """GUI日志处理器，用于将日志输出到GUI界面"""
    def __init__(self, gui):
        self.gui = gui
        
    def info(self, message):
        """信息日志"""
        self.gui.root.after(0, lambda: self.gui.log_message(f"INFO: {message}"))
        
    def warning(self, message):
        """警告日志"""
        self.gui.root.after(0, lambda: self.gui.log_message(f"WARNING: {message}"))
        
    def error(self, message):
        """错误日志"""
        self.gui.root.after(0, lambda: self.gui.log_message(f"ERROR: {message}"))
        
    def debug(self, message):
        """调试日志"""
        self.gui.root.after(0, lambda: self.gui.log_message(f"DEBUG: {message}"))


def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')  # 使用现代主题
    
    app = DataQCGUI(root)
    
    # 设置窗口关闭事件
    def on_closing():
        if app.is_processing:
            if messagebox.askokcancel("退出", "正在处理数据，确定要退出吗？"):
                app.stop_processing()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()