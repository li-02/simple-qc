"""
数据处理辅助函数
"""
import numpy as np
import pandas as pd


def set_data_nan(data, condition, column_name):
    """
    根据条件将数据设置为NaN
    
    Args:
        data: 数据DataFrame
        condition: 布尔条件
        column_name: 要设置为NaN的列名
        
    Returns:
        处理后的DataFrame
    """
    data.loc[condition, column_name] = np.nan
    return data


def calculate_diff(data, value):
    """
    计算时间序列的二阶差分
    
    Args:
        data: 包含需要进行差分的数据的DataFrame
        value: 需要进行差分的列名
        
    Returns:
        计算后的二阶差分序列
    """
    a = data[value]
    b = a.shift(1)
    c = a.shift(-1)
    temp_value = (a-c)-(b-a)
    return temp_value


def add_window_tag(data, day_size=13):
    """
    添加一列window标签序号，如果最后一个的个数不够window_size，则算前一个window
    
    Args:
        data: 所有数据DataFrame
        day_size: 设定的天数，默认为13
        
    Returns:
        data: 增加了windowID的数据
        window_size: 一个window大小
        window_nums: windows的个数
    """
    window_size = day_size * 48
    window_nums = data.shape[0] // window_size
    data['windowID'] = data.index // window_size
    if data.shape[0] % window_size != 0:
        data.loc[data['windowID'] == window_nums, 'windowID'] = window_nums - 1
    return data, window_size, window_nums


def judge_day_night(data, ppfd_column='Par_f', ppfd_threshold=5):
    """
    添加白天/黑夜标记列
    
    Args:
        data: 数据DataFrame
        ppfd_column: 光合有效辐射列名，默认为'Par_f'
        ppfd_threshold: 判断白天/黑夜的阈值，默认为5
        
    Returns:
        带有is_day_night列的DataFrame，1表示白天，0表示夜晚
    """
    data['is_day_night'] = np.nan
    if ppfd_column not in data.columns:
        print(f'数据表缺失 {ppfd_column}，无法判断白天黑夜')
    else:
        data[ppfd_column] = data[ppfd_column].astype('float')
        day_condition = (data[ppfd_column] > ppfd_threshold) & (pd.isna(data['is_day_night']))
        night_condition = (data[ppfd_column] <= ppfd_threshold) & (pd.isna(data['is_day_night']))
        data.loc[day_condition, 'is_day_night'] = 1
        data.loc[night_condition, 'is_day_night'] = 0
    return data