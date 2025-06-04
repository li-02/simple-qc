"""
阈值处理模块
"""
import re
import numpy as np
import pandas as pd


def threshold_limit(data, qc_indicators, data_type):
    """
    基于阈值对数据进行筛选
    
    Args:
        data: 数据DataFrame
        qc_indicators: 所有质量控制指标
        data_type: 数据类型
        
    Returns:
        阈值处理后的数据
    """
    if data_type == 'flux':
        return threshold_limit_flux(data, qc_indicators)
    elif data_type == 'sapflow':
        return threshold_limit_sapflow(data, qc_indicators)
    elif data_type == 'aqi':
        return threshold_limit_aqi(data, qc_indicators)
    else:
        return threshold_limit_general(data, qc_indicators, data_type)


def threshold_limit_flux(data, qc_indicators):
    """
    对flux类型数据进行阈值处理
    
    Args:
        data: 数据DataFrame
        qc_indicators: 所有质量控制指标
        
    Returns:
        阈值处理后的数据
    """
    try:
        # 特殊变量与其对应的 add_strg 和 threshold_limit 列名的映射
        special_vars = {
            'co2_flux': {'add_strg': 'co2_flux_add_strg', 'threshold': 'co2_flux_threshold_limit'},
            'h2o_flux': {'add_strg': 'h2o_flux_add_strg', 'threshold': 'h2o_flux_threshold_limit'},
            'le': {'add_strg': 'le_add_strg', 'threshold': 'le_threshold_limit'},
            'h': {'add_strg': 'h_add_strg', 'threshold': 'h_threshold_limit'},
        }
        
        # 创建一个字典来快速查找 qc_indicators 中的值
        qc_dict = {
            item['code']: {
                'lower': float(item['qc_lower_limit']), 
                'upper': float(item['qc_upper_limit'])
            } 
            for item in qc_indicators
        }
        
        for col in data.columns:
            if col in qc_dict:
                limits = qc_dict[col]
                if col in special_vars:
                    # 对特殊变量处理
                    add_strg_col = special_vars[col]['add_strg']
                    threshold_col = special_vars[col]['threshold']
                    if add_strg_col in data.columns:
                        condition = (data[add_strg_col] < limits['lower']) | (data[add_strg_col] > limits['upper'])
                        data[threshold_col] = data[add_strg_col]
                        data.loc[condition, threshold_col] = np.nan
                else:
                    # 对其他变量处理
                    threshold_col = col + "_threshold_limit"
                    condition = (data[col] < limits['lower']) | (data[col] > limits['upper'])
                    data[threshold_col] = data[col]
                    data.loc[condition, threshold_col] = np.nan
        return data
    except Exception as e:
        print(f"阈值处理出错: {e}")
        return data


def threshold_limit_general(data, qc_indicators, data_type):
    """
    对一般类型数据进行阈值处理
    
    Args:
        data: 数据DataFrame
        qc_indicators: 所有质量控制指标
        data_type: 数据类型
        
    Returns:
        阈值处理后的数据
    """
    # 转成float
    for col in data.columns:
        if col != 'record_time':
            data[col] = data[col].astype('float')
    
    try:
        for indicator in qc_indicators:
            for col in data.columns:
                # 不同数据类型的处理逻辑
                if data_type == 'aqi':
                    if re.sub(r"\W", "_", indicator["en_name"]).lower() == col:
                        condition = (data[col] < float(indicator['qc_lower_limit'])) | (data[col] > float(indicator['qc_upper_limit']))
                        data[col + "_threshold_limit"] = data[col]
                        data.loc[condition, col + "_threshold_limit"] = np.nan
                else:
                    if indicator['code'] == col:
                        condition = (data[col] < float(indicator['qc_lower_limit'])) | (data[col] > float(indicator['qc_upper_limit']))
                        data[col + "_threshold_limit"] = data[col]
                        data.loc[condition, col + "_threshold_limit"] = np.nan
    except Exception as e:
        print(f"阈值处理出错: {e}")
    
    return data


def threshold_limit_sapflow(data, qc_indicators):
    """
    对sapflow类型数据进行阈值处理
    
    Args:
        data: 数据DataFrame
        qc_indicators: 所有质量控制指标
        
    Returns:
        阈值处理后的数据
    """
    # 首先进行一般的阈值处理
    data = threshold_limit_general(data, qc_indicators, 'sapflow')
    
    # 对特定的列进行额外处理
    for indicator in qc_indicators:
        for col in data.columns:
            # 如果列名以 tc_dtca_ 开头，执行 del_abnormal_data_sapflow 函数
            if indicator['code'] == col and col.startswith('tc_dtca_'):
                data = del_abnormal_data_sapflow(data, ta_name="ta_1_2_1_threshold_limit", daca_name=col + "_threshold_limit")
    
    # 茎流速率 用5倍标准差再筛选一遍数据
    data = standard_deviation_limit(data)
    
    return data


def threshold_limit_aqi(data, qc_indicators):
    """
    对aqi类型数据进行阈值处理
    
    Args:
        data: 数据DataFrame
        qc_indicators: 所有质量控制指标
        
    Returns:
        阈值处理后的数据
    """
    # 首先进行一般的阈值处理
    data = threshold_limit_general(data, qc_indicators, 'aqi')
    
    # 补半点数据将用前后整点数据的均值来插补，若前后至少有一个是NaN那么这个半点的数据就是NaN
    # 将时间设为index
    data = data.set_index(pd.to_datetime(data['record_time'])).drop('record_time', axis=1)
    
    # 补全时间序列 半点数据置为NaN
    data = data.resample('30min').mean()
    
    # 将半点的值置为前后整点数据的均值
    for i in range(data.shape[0]):
        if data.iloc[i].name.minute == 30:
            data.iloc[i] = (data.iloc[i - 1] + data.iloc[i + 1]) / 2
    
    data = data.reset_index()
    return data


def del_abnormal_data_sapflow(raw_data, ta_name="ta_1_2_1_threshold_limit", daca_name="tc_dtca_1__threshold_limit"):
    """
    删除sapflow数据中的异常值
    
    Args:
        raw_data: 原始数据DataFrame
        ta_name: 温度列名
        daca_name: dtca列名
        
    Returns:
        处理后的数据
    """
    df = raw_data.copy()
    df[daca_name + "_old"] = df[daca_name]

    if ta_name in df.columns and 'record_time' in df.columns:
        df['record_time'] = pd.to_datetime(df['record_time'])
        df['date'] = df['record_time'].dt.date

        # 计算每日的平均温度
        daily_avg_temp = df.groupby('date')[ta_name].mean()

        daily_df = pd.DataFrame({
            'date': daily_avg_temp.index,
            'day_avg_tair': daily_avg_temp.values
        })

        # 以天为单位对 'ta' 列进行滚动平均，并确保窗口包含3天的数据
        daily_df['ta_three_avg'] = daily_df['day_avg_tair'].rolling(window=3, min_periods=3, center=True).mean()

        # 前后赋值最近的值
        first_non_nan = daily_df['ta_three_avg'].first_valid_index()
        last_non_nan = daily_df['ta_three_avg'].last_valid_index()
        
        if last_non_nan is not None:
            last_non_nan_value = daily_df.at[last_non_nan, 'ta_three_avg']
        else:
            last_non_nan_value = pd.NA  # 如果整个列都是 NaN，则这里也是 NaN

        # 用第一个非NaN值填充前面的NaN
        if first_non_nan is not None:
            daily_df['ta_three_avg'] = daily_df['ta_three_avg'].fillna(method='bfill',
                                                                   limit=daily_df.index.get_loc(first_non_nan))

        # 用最后一个非NaN值填充后面的NaN
        daily_df['ta_three_avg'] = daily_df['ta_three_avg'].fillna(last_non_nan_value)

        # 添加是否是生长季的列（温度是否小于5）
        daily_df['is_grow_season'] = (daily_df['ta_three_avg'] >= 5).astype(int)

        df = df.merge(daily_df[['date', 'is_grow_season']], on='date', how='left')
        
        # 在生长季剔除不在 [3, 12] 范围内的数据
        condition = (df['is_grow_season'] == 1) & ((df[daca_name] < 3) | (df[daca_name] > 12))
        df.loc[condition, daca_name] = pd.NA

        # 删除辅助列
        df.drop(['date', 'is_grow_season'], axis=1, inplace=True)

    return df


def standard_deviation_limit(data):
    """
    使用标准差对sapflow数据进行异常值检测
    
    Args:
        data: 数据DataFrame
        
    Returns:
        处理后的数据
    """
    sapflow_data = pd.DataFrame()
    
    # 提取需要处理的列
    for col in data.columns:
        if col.endswith('_limit'):
            sapflow_data[col+'_std'] = data[col]
    
    index = 0
    while index < sapflow_data.shape[0]:
        if (index + 479) > (sapflow_data.shape[0]):
            break
            
        # 获取当前窗口数据
        window_data = sapflow_data.iloc[index:index + 480]
        
        # 计算均值和标准差
        window_mean = window_data.mean()
        window_std = window_data.std()
        
        # 检查是否全为NaN
        if window_mean.isna().all():
            index += 96
            continue
            
        # 异常值检测：超出均值±标准差的值设为NaN
        upper_bound = window_mean + window_std
        lower_bound = window_mean - window_std
        
        for col in sapflow_data.columns:
            mask = (sapflow_data.iloc[index:index + 480][col] > upper_bound[col]) | \
                   (sapflow_data.iloc[index:index + 480][col] < lower_bound[col])
            sapflow_data.loc[index:index + 479, col].loc[mask] = np.nan
            
        index += 96
    
    # 添加时间列
    sapflow_data['record_time'] = data['record_time']
    
    # 合并数据
    full_data = pd.merge(data, sapflow_data, how='outer', on='record_time')
    
    # 只保留整点和半点数据
    full_data['record_time'] = pd.to_datetime(full_data['record_time'])
    new_data = full_data[~full_data['record_time'].dt.minute.isin([15, 45])]
    
    return new_data