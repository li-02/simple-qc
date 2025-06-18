"""
数据插补模块
"""
import re
import pandas as pd
import numpy as np
from r_scripts import robjects, StrVector, FloatVector, IntVector, pandas2ri
from rpy2.robjects.conversion import localconverter


def gap_fill_par(file_name, longitude, latitude, timezone, data):
    """
    插补Par（光合有效辐射）
    
    Args:
        file_name: 文件名
        longitude: 经度
        latitude: 纬度
        timezone: 时区
        data: 数据DataFrame
        
    Returns:
        插补后的数据
    """
    # 将数据转化成R语言需要的格式
    data['record_time'] = pd.to_datetime(data['record_time'])
    data = data.rename(columns={"record_time": "DateTime"})
    
    # 准备R需要的变量
    data['rH'] = data['rh_threshold_limit'] if 'rh_threshold_limit' in data.columns else np.nan
    data['Rg'] = data['rg_1_1_2_threshold_limit'] if 'rg_1_1_2_threshold_limit' in data.columns else np.nan
    data['Tair'] = data['ta_1_2_1_threshold_limit'] if 'ta_1_2_1_threshold_limit' in data.columns else np.nan
    data['VPD'] = data['vpd_threshold_limit'] * 0.01 if 'vpd_threshold_limit' in data.columns else np.nan
    data['Par'] = data['ppfd_1_1_1_threshold_limit'] if 'ppfd_1_1_1_threshold_limit' in data.columns else np.nan
 
    # 转换为R对象
    r_filename = StrVector([file_name])
    r_longitude = FloatVector([longitude])
    r_latitude = FloatVector([latitude])
    r_timezone = IntVector([timezone])
    
    # 使用localconverter来转换DataFrame
    with localconverter(robjects.default_converter + pandas2ri.converter):
        data_r = robjects.conversion.py2rpy(data)
    
    # 调用R函数
    result_data = robjects.r['r_gap_fill_par'](r_filename, r_longitude, r_latitude, r_timezone, data_r)

    # 将R结果转回Python
    with localconverter(robjects.default_converter + pandas2ri.converter):
        result_data = robjects.conversion.rpy2py(result_data)
        
    # 处理结果数据
    result_data = result_data.rename(columns={"DateTime": "record_time"})
    result_data["record_time"] = result_data["record_time"].dt.tz_localize(None)
    result_data = result_data.set_index("record_time")
    
    # 删除不需要的列
    columns_to_drop = ["rH", "Rg", "Tair", "VPD", "Par"]
    result_data = result_data.drop([col for col in columns_to_drop if col in result_data.columns], axis=1)
    
    # 重置索引
    result_data = result_data.reset_index()
    
    return result_data


def gapfill(file_name,longitude,latitude,timezone,data,qc_indicators,data_type):
    data['record_time'] = pd.to_datetime(data['record_time'])
    data = data.rename(columns={'record_time': 'DateTime'})

    data['rH'] = data['rh_threshold_limit']
    data['Rg'] = data['rg_1_1_2_threshold_limit']
    data['Tair'] = data['ta_1_2_1_threshold_limit']
    # VPD pa to hpa
    data['VPD'] = data['vpd_threshold_limit'] * 0.01

    # 先把传入的参数给处理掉
    # print(longitude, latitude, timezone)
    r_filename = StrVector([file_name])
    r_longitude = FloatVector([longitude])
    r_latitude = FloatVector([latitude])
    r_timezone = IntVector([timezone])
    data_r = pandas2ri.py2rpy(data)

    # gapfilling indicators  这里是这个表里仅有的那几个指标而不是所有的指标都gapfilling 因为有的站没有一些指标
    gapfill_indicators = []
    for i in qc_indicators:
        if i['is_gapfill'] == 1:
            # aqi 有点特殊....
            if data_type == 'aqi':
                if i['belong_to'] == data_type and re.sub(
                    r"\W", "_", i["en_name"]).lower() in data.columns:
                    gapfill_indicators.append(
                        re.sub(r"\W", "_", i["en_name"]).lower() +
                        '_threshold_limit')
            else:
                if i['belong_to'] == data_type and i['code'] in data.columns:
                    gapfill_indicators.append(i['code'] + '_threshold_limit')
    result_data = robjects.r['r_gap_fill_all'](r_filename,
                                                           r_longitude,
                                                           r_latitude,
                                                           r_timezone, data_r,
                                                           gapfill_indicators)

    # 设置index
    # 这里ns 和ns Shanghai 不可直接合并，所以要转一下
    with localconverter(robjects.default_converter + pandas2ri.converter):
        result_data = robjects.conversion.rpy2py(result_data)

    result_data = result_data.rename(columns={'DateTime': 'record_time'})
    result_data['record_time'] = result_data['record_time'].dt.tz_localize(
        None)
    result_data.set_index('record_time')
    del_list = ['rH','Rg','Tair','VPD']
    for item in result_data.columns.tolist():
        if item in del_list:
            del result_data[item]
    return result_data