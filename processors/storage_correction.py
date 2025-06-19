"""
存储项校正模块
"""
import numpy as np
import pandas as pd
from config.constants import CAMPBELL_SITES


def do_add_strg(data):
    """
    对数据进行存储项校正
    
    Args:
        data: 数据DataFrame
        
    Returns:
        校正后的数据
    """
    # 定义需要处理的变量列表
    variables = [
        ('co2_flux', 'co2_flux_filter_label', 'co2_flux_strg', 'co2_flux_add_strg'),
        ('h2o_flux', 'h2o_flux_filter_label', 'h2o_flux_strg', 'h2o_flux_add_strg'),
        ('le', 'le_filter_label', 'le_strg', 'le_add_strg'),
        ('h', 'h_filter_label', 'h_strg', 'h_add_strg')
    ]

    for _, filter_col, strg_col, result_col in variables:
        if filter_col in data.columns:
            data[filter_col] = data[filter_col].astype('float')
            if strg_col in data.columns:
                data[strg_col] = data[strg_col].astype('float')
                data[result_col] = data[filter_col] + data[strg_col]

    return data


def not_add_strg(data):
    """
    不进行存储项校正，直接复制数据
    
    Args:
        data: 数据DataFrame
        
    Returns:
        处理后的数据
    """
    # 定义需要处理的变量列表
    variables = [
        ('co2_flux_filter_label', 'co2_flux_add_strg'),
        ('h2o_flux_filter_label', 'h2o_flux_add_strg'),
        ('le_filter_label', 'le_add_strg'),
        ('h_filter_label', 'h_add_strg')
    ]

    for filter_col, result_col in variables:
        if filter_col in data.columns:
            data[filter_col] = data[filter_col].astype('float')
            data[result_col] = data[filter_col]

    return data


def copy_flux_columns_without_qc_filter(data):
    """
    直接复制通量列而不进行QC标记过滤
    
    Args:
        data: 数据DataFrame
        
    Returns:
        处理后的数据
    """
    # 复制通量列
    data['co2_flux_filter_label'] = data['co2_flux']
    data['h2o_flux_filter_label'] = data['h2o_flux']
    data['le_filter_label'] = data['le']
    data['h_filter_label'] = data['h']
    
    return data


def handle_campbell_special_case(data):
    """
    处理Campbell站点特殊情况
    
    Args:
        data: 数据DataFrame
        
    Returns:
        处理后的数据
    """
    data['co2_flux_filter_label'] = data['co2_flux']

    # 八达岭、奥森没有h2o_flux，需要计算
    # 计算h2o_flux
    data['h2o_flux'] = (data['le'].astype(float)) / 2450 / 18 * 1000
    data['h2o_flux_filter_label'] = data['h2o_flux']

    data['le_filter_label'] = data['le']
    data['h_filter_label'] = data['h']

    return data


def filter_flux_by_qc_flags(data, excluded_qc_flags):
    """
    复制通量数据（已移除QC标记过滤功能）
    
    Args:
        data: 数据DataFrame
        excluded_qc_flags: 要排除的QC标记列表（已废弃，保留参数兼容性）
        
    Returns:
        处理后的数据
    """
    # 复制通量列
    data['co2_flux_filter_label'] = data['co2_flux']
    data['h2o_flux_filter_label'] = data['h2o_flux']
    data['le_filter_label'] = data['le']
    data['h_filter_label'] = data['h']
    
    return data