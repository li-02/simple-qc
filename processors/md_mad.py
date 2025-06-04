"""
中位数Md和绝对中位差MAD计算模块
"""
import numpy as np
import pandas as pd


def calculate_md(data, value):
    """
    计算Md值
    
    Args:
        data: 包含数据的DataFrame
        value: 需要计算的指标名称
        
    Returns:
        包含Md值的DataFrame
    """
    Md_data = data.groupby(by=['windowID', 'is_day_night'], as_index=False).median()
    result_data = {
        'windowID': Md_data['windowID'],
        'is_day_night': Md_data['is_day_night'],
        f'{value}_Md': Md_data[f'{value}_diff']
    }
    return pd.DataFrame(result_data)


def calculate_mad(data, value):
    """
    计算MAD值
    
    Args:
        data: 包含数据的DataFrame
        value: 需要计算的指标名称
        
    Returns:
        MAD值
    """
    MAD = (data[f'{value}_diff'] - data[f'{value}_Md']).abs().median()
    return MAD


def md_method(data_D, data_N, data, value):
    """
    计算MD
    
    Args:
        data_D: 白天数据DataFrame
        data_N: 夜晚数据DataFrame
        data: 完整数据DataFrame
        value: 需要计算md的指标名称
        
    Returns:
        增加了{value}_Md列的DataFrame
    """
    # 白天数据的MD
    day_md = calculate_md(data_D, value)
    try:
        day_md_value = day_md[f'{value}_Md'].values[0]
    except:
        day_md_value = np.nan
    data.loc[data_D.index.tolist(), f'{value}_Md'] = day_md_value

    # 夜晚数据的MD
    night_md = calculate_md(data_N, value)
    try:
        night_md_value = night_md[f'{value}_Md'].values[0]
    except:
        night_md_value = np.nan
    data.loc[data_N.index.tolist(), f'{value}_Md'] = night_md_value

    return data


def mad_method(data_D, data_N, data, value):
    """
    计算MAD
    
    Args:
        data_D: 白天数据DataFrame
        data_N: 夜晚数据DataFrame
        data: 完整数据DataFrame
        value: 需要计算mad的指标名称
        
    Returns:
        增加了{value}_MAD列的DataFrame
    """
    try:
        day_mad = calculate_mad(data_D, value)
    except:
        day_mad = np.nan
    data.loc[data_D.index.tolist(), f'{value}_MAD'] = day_mad
    
    try:
        night_mad = calculate_mad(data_N, value)
    except:
        night_mad = np.nan
    data.loc[data_N.index.tolist(), f'{value}_MAD'] = night_mad

    return data