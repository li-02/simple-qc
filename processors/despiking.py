"""
去尖峰处理模块
"""
import numpy as np
import pandas as pd
from utils.data_helpers import judge_day_night, add_window_tag, calculate_diff, set_data_nan
from processors.md_mad import md_method, mad_method


def despiking_data(data, despiking_z=4):
    """
    对数据进行去尖峰处理
    
    Args:
        data: 插补后的par数据
        despiking_z: z系数，默认为4
        
    Returns:
        去峰值后的数据
    """
    # 1. 创建despiking列
    data['co2_despiking'] = data['co2_flux_threshold_limit']
    data['h2o_despiking'] = data['h2o_flux_threshold_limit']
    data['le_despiking'] = data['le_threshold_limit']
    data['h_despiking'] = data['h_threshold_limit']

    # 2. 判断白天黑夜
    data = judge_day_night(data)

    # 3. 对每个变量处理
    variables = ['co2', 'h2o', 'le', 'h']
    for var in variables:
        var_column = f'{var}_despiking'
        # 筛选非空数据
        window_data = data[data[var_column].notnull()].reset_index(drop=True)
        
        # 添加窗口标签
        window_data, _, window_nums = add_window_tag(window_data)
        
        # 处理每个窗口
        data = process_variable_despiking(data, window_data, var, window_nums, despiking_z)
    
    return data


def process_variable_despiking(data, window_data, var_name, window_nums, despiking_z):
    """
    对指定变量进行去尖峰处理
    
    Args:
        data: 主数据集
        window_data: 按窗口划分的数据
        var_name: 变量名称（如'co2', 'h2o'等）
        window_nums: 窗口数量
        despiking_z: 去尖峰的z系数
        
    Returns:
        处理后的主数据集
    """
    diff_col = f"{var_name}_diff"
    md_col = f"{var_name}_Md"
    mad_col = f"{var_name}_MAD"
    despiking_col = f"{var_name}_despiking"
    
    # 预先创建diff列，避免重复创建
    if diff_col not in window_data.columns:
        window_data[diff_col] = np.nan
    
    for i in range(window_nums):
        # 基于窗口ID和白天/黑夜标志筛选数据
        window_condition = window_data['windowID'] == i
        day_condition = window_condition & (window_data['is_day_night'] == 1)
        night_condition = window_condition & (window_data['is_day_night'] == 0)
        
        # 获取白天和夜晚数据
        window_data_D = window_data[day_condition]
        window_data_N = window_data[night_condition]
        
        # 计算差分
        if not window_data_D.empty:
            temp_diff = calculate_diff(window_data_D, despiking_col)
            window_data.loc[temp_diff.index, diff_col] = temp_diff
        
        if not window_data_N.empty:
            temp_diff = calculate_diff(window_data_N, despiking_col)
            window_data.loc[temp_diff.index, diff_col] = temp_diff
        
        # 更新数据
        window_data_D = window_data[day_condition]
        window_data_N = window_data[night_condition]
        
        # 计算MD和MAD
        window_data = md_method(window_data_D, window_data_N, window_data, var_name)
        
        window_data_D = window_data[day_condition]
        window_data_N = window_data[night_condition]
        window_data = mad_method(window_data_D, window_data_N, window_data, var_name)
        
        # 计算并标记峰值
        di_low_range = window_data[md_col] - (despiking_z * window_data[mad_col]) / 0.6745
        di_high_range = window_data[md_col] + (despiking_z * window_data[mad_col]) / 0.6745
        
        # 检测条件
        condition = (window_data[diff_col] < di_low_range) | (window_data[diff_col] > di_high_range)
        condition = condition & window_condition
        
        if condition.any():
            spike_times = window_data.loc[condition, 'record_time'].tolist()
            data_condition = data['record_time'].isin(spike_times)
            data = set_data_nan(data, data_condition, despiking_col)
    
    return data