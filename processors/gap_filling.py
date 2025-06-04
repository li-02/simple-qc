"""
数据插补模块
"""
import re
import pandas as pd
import numpy as np
from r_scripts import robjects, StrVector, FloatVector, IntVector, pandas2ri
from rpy2.robjects.conversion import localconverter


def safe_datetime_conversion(datetime_series):
    """
    安全的datetime转换函数，处理时区问题
    
    Args:
        datetime_series: 需要转换的datetime序列
        
    Returns:
        转换后的datetime序列（无时区信息）
    """
    try:
        # 如果已经是datetime类型，直接处理时区
        if pd.api.types.is_datetime64_any_dtype(datetime_series):
            print("数据已经是datetime类型，处理时区信息...")
            # 检查是否有时区信息
            if hasattr(datetime_series.dtype, 'tz') and datetime_series.dtype.tz is not None:
                print("移除现有时区信息...")
                return datetime_series.dt.tz_localize(None)
            else:
                print("无时区信息，直接返回...")
                return datetime_series
        else:
            # 如果不是datetime类型，进行转换
            print("转换为datetime类型...")
            return pd.to_datetime(datetime_series, errors='coerce')
    except Exception as e:
        print(f"时间转换出错: {e}")
        # 如果转换失败，尝试其他方法
        try:
            # 先转换为字符串，再转换为datetime
            str_series = datetime_series.astype(str)
            return pd.to_datetime(str_series, errors='coerce')
        except:
            print("所有转换方法都失败，返回原始数据")
            return datetime_series


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
    try:
        # 完全重新初始化rpy2转换环境
        import rpy2.robjects as robjects
        from rpy2.robjects import pandas2ri
        from rpy2.robjects.conversion import localconverter
        
        # 强制重新激活
        pandas2ri.deactivate()  # 先停用
        pandas2ri.activate()    # 再激活    
        
        # 检查时间数据
        print("\n=== 开始处理时间数据 ===")
        print("原始时间数据类型:", data['record_time'].dtype)
        print("时间数据样本:", data['record_time'].head())
        
        # 转换时间格式
        data['record_time'] = pd.to_datetime(data['record_time'], errors='coerce')
        print("转换后时间数据类型:", data['record_time'].dtype)
        
        # 检查无效时间
        invalid_dates = data['record_time'].isna().sum()
        print(f"无效时间数量: {invalid_dates}")
        
        # 检查时区状态
        print("\n=== 检查时区状态 ===")
        tz_info = data['record_time'].dt.tz
        print(f"当前时区信息: {tz_info}")
        
        # 如果有时区信息，先移除
        if tz_info is not None:
            print("移除时区信息...")
            data['record_time'] = data['record_time'].dt.tz_localize(None)
            print("移除时区后数据类型:", data['record_time'].dtype)
        
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
        print("\n=== 转换数据为R对象 ===")
        r_filename = StrVector([file_name])
        r_longitude = FloatVector([longitude])
        r_latitude = FloatVector([latitude])
        r_timezone = IntVector([timezone])
        
        # 使用localconverter来转换DataFrame
        print("转换DataFrame为R对象...")
        with localconverter(robjects.default_converter + pandas2ri.converter):
            data_r = robjects.conversion.py2rpy(data)
            print("转换完成，R对象类型:", type(data_r))
        
        # 调用R函数
        print("\n=== 调用R函数 ===")
        print("正在调用r_gap_fill_par函数...")
        result_data = robjects.r['r_gap_fill_par'](r_filename, r_longitude, r_latitude, r_timezone, data_r)
        
        if result_data is None:
            raise ValueError("R函数r_gap_fill_par返回None，插补失败")
            
        print("R函数返回结果类型:", type(result_data))
        
        # 将R结果转回Python
        print("\n=== 转换R结果回Python ===")
        with localconverter(robjects.default_converter + pandas2ri.converter):
            try:
                result_data = robjects.conversion.rpy2py(result_data)
                print("转换完成，Python对象类型:", type(result_data))
                print("结果数据列名:", result_data.columns.tolist())
                
                # 安全地处理时间数据
                if 'DateTime' in result_data.columns:
                    print("\n=== 处理时间数据 ===")
                    print("原始DateTime类型:", result_data['DateTime'].dtype)
                    print("DateTime样本:", result_data['DateTime'].head())
                    
                    # 使用安全的时间转换函数
                    result_data['DateTime'] = safe_datetime_conversion(result_data['DateTime'])
                    print("处理后DateTime类型:", result_data['DateTime'].dtype)
                    
                    # 重命名列
                    result_data = result_data.rename(columns={"DateTime": "record_time"})
                    
                    # 设置索引
                    result_data = result_data.set_index("record_time")
                    print("结果数据形状:", result_data.shape)
                else:
                    print("警告: 结果数据中缺少DateTime列")
                    raise KeyError("结果数据中缺少DateTime列")
            except Exception as e:
                print(f"转换R结果失败: {str(e)}")
                raise
        
        # 删除不需要的列
        columns_to_drop = ["rH", "Rg", "Tair", "VPD", "Par"]
        result_data = result_data.drop([col for col in columns_to_drop if col in result_data.columns], axis=1)
        
        # 重置索引
        result_data = result_data.reset_index()
        
        return result_data
        
    except Exception as e:
        import traceback
        print("\n=== 错误信息 ===")
        print(f"错误类型: {type(e)}")
        print(f"错误信息: {str(e)}")
        print("详细错误信息:")
        traceback.print_exc()
        raise


def gapfill(file_name,longitude,latitude,timezone,data,qc_indicators,data_type):
    """
    AQI等数据类型的插补函数
    """
    # 在函数开始时重新激活rpy2转换器（多线程环境需要）
    try:
        from rpy2.robjects import pandas2ri
        pandas2ri.deactivate()  # 先停用
        pandas2ri.activate()    # 再激活
        print("已在gapfill函数中重新激活rpy2转换器")
    except Exception as e:
        print(f"激活rpy2转换器失败: {str(e)}")
    
    data['record_time'] = pd.to_datetime(data['record_time'])
    data = data.rename(columns={'record_time': 'DateTime'})

    data['rH'] = data['rh_threshold_limit']
    data['Rg'] = data['rg_1_1_2_threshold_limit'] 
    data['Tair'] = data['ta_1_2_1_threshold_limit']
    # VPD pa to hpa
    data['VPD'] = data['vpd_threshold_limit'] * 0.01

    # 先把传入的参数给处理掉
    r_filename = StrVector([file_name])
    r_longitude = FloatVector([longitude])
    r_latitude = FloatVector([latitude])
    r_timezone = IntVector([timezone])
    
    # 重新激活pandas转换器并转换数据
    try:
        with localconverter(robjects.default_converter + pandas2ri.converter):
            data_r = robjects.conversion.py2rpy(data)
    except:
        # 如果转换失败，尝试直接使用pandas2ri
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
    
    print(f"AQI插补指标: {gapfill_indicators}")
    
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