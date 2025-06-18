"""
数据分区模块
"""
import pandas as pd
from r_scripts import robjects, StrVector, FloatVector, IntVector, pandas2ri
from rpy2.robjects.conversion import localconverter
from config.constants import DEL_LIST, NO_USE_LIST


def ustar_data(file_name, longitude, latitude, timezone, data, qc_indicators):
    """
    执行u*筛选、插补和分区
    
    Args:
        file_name: 文件名
        longitude: 经度
        latitude: 纬度
        timezone: 时区
        data: 数据DataFrame
        qc_indicators: 质量控制指标
        
    Returns:
        处理后的数据
    """
    # 格式化时间
    data['record_time'] = pd.to_datetime(data['record_time'])
    
    # 重命名列为R格式
    data = data.rename(columns={'record_time': 'DateTime'})
    
    # 准备R需要的列
    data['NEE'] = data['co2_despiking']
    data['rH'] = data['rh_threshold_limit']
    data['Rg'] = data['rg_1_1_2_threshold_limit']
    data['Tair'] = data['ta_1_2_1_threshold_limit']
    data['VPD'] = data['vpd_threshold_limit'] * 0.01  # Pa to hPa
    
    # 准备R函数参数
    pandas2ri.activate()
    r_filename = StrVector([file_name])
    r_longitude = FloatVector([longitude])
    r_latitude = FloatVector([latitude])
    r_timezone = IntVector([timezone])
    
    # 准备插补指标
    gapfill_indicators = []
    for indicator in qc_indicators:
        if indicator['is_gapfill'] == 1 and indicator['code'] not in NO_USE_LIST:
            if indicator['belong_to'] == 'flux' and indicator['code'] in data.columns:
                gapfill_indicators.append(indicator['code'] + '_threshold_limit')
    
    # 添加其他需要插补的指标
    gapfill_indicators += ['h2o_despiking', 'le_despiking', 'h_despiking']
    
    # 转换数据为R格式
    with localconverter(robjects.default_converter + pandas2ri.converter):
        data_r = robjects.conversion.py2rpy(data)
    r_gapfill_indicators = StrVector(gapfill_indicators)
    
    # 调用R函数
    result_data = robjects.r['r_co2_flux'](
        r_filename, r_longitude, r_latitude, r_timezone, data_r, r_gapfill_indicators
    )
    
    # 将R结果转回Python
    with localconverter(robjects.default_converter + pandas2ri.converter):
        result_data = robjects.conversion.rpy2py(result_data)
    
    # 处理结果数据
    result_data = result_data.rename(columns={'DateTime': 'record_time'})
    result_data['record_time'] = result_data['record_time'].dt.tz_localize(None)
    result_data = result_data.set_index('record_time')
    
    # 删除不需要的列
    for col in DEL_LIST:
        if col in result_data.columns:
            result_data = result_data.drop(col, axis=1)
    
    # 转换列名为小写
    result_data.columns = [col.lower() for col in result_data.columns]
    
    # 重置索引
    result_data = result_data.reset_index()
    
    return result_data