"""
异常值处理模块
"""
import numpy as np
import pandas as pd
from utils.data_helpers import judge_day_night


def del_abnormal_data(raw_data, ta_name="ta_1_2_1_threshold_limit", 
                      par_name="ppfd_1_1_1_threshold_limit",
                      nee_name="co2_flux_threshold_limit"):
    """
    删除异常值
    
    Args:
        raw_data: 原始数据DataFrame
        ta_name: 温度列名
        par_name: 光合有效辐射列名
        nee_name: NEE列名
        
    Returns:
        处理后的数据
    """
    # 添加白天/黑夜标记
    df = judge_day_night(data=raw_data, ppfd_column=par_name)
    
    # 保存原始值
    df[nee_name + "_old"] = df[nee_name]
    
    if ta_name in df.columns and 'record_time' in df.columns:
        df['record_time'] = pd.to_datetime(df['record_time'])
        df['date'] = df['record_time'].dt.date
        
        # 计算每日的平均温度
        daily_avg_temp = df.groupby('date')[ta_name].mean()

        daily_df = pd.DataFrame({
            'date': daily_avg_temp.index,
            'day_avg_tair': daily_avg_temp.values
        })

        # 滚动平均计算3天平均温度
        daily_df['ta_three_avg'] = daily_df['day_avg_tair'].rolling(window=3, min_periods=3, center=True).mean()
        
        # 处理前后的NaN值
        first_non_nan = daily_df['ta_three_avg'].first_valid_index()
        last_non_nan = daily_df['ta_three_avg'].last_valid_index()
        
        if last_non_nan is not None:
            last_non_nan_value = daily_df.at[last_non_nan, 'ta_three_avg']
        else:
            last_non_nan_value = pd.NA
            
        # 填充前面的NaN
        if first_non_nan is not None:
            daily_df['ta_three_avg'] = daily_df['ta_three_avg'].fillna(
                method='bfill', limit=daily_df.index.get_loc(first_non_nan))
            
        # 填充后面的NaN
        daily_df['ta_three_avg'] = daily_df['ta_three_avg'].fillna(last_non_nan_value)

        # 判断是否是生长季（温度是否大于等于5℃）
        daily_df['is_grow_season'] = (daily_df['ta_three_avg'] >= 5).astype(int)

        # 合并生长季信息到原数据
        df = df.merge(daily_df[['date', 'is_grow_season']], on='date', how='left')

        # 根据条件删除异常值
        condition = (
            # 冬季白天NEE超出[-1, 1]范围
            ((df['is_day_night'] == 1) & (df[nee_name] <= -1) & (df[nee_name] >= 1) & (df['is_grow_season'] == 0)) | 
            # 冬季夜间NEE < -0.2
            ((df['is_day_night'] == 0) & (df[nee_name] < -0.2) & (df['is_grow_season'] == 0))
        )
        df.loc[condition, nee_name] = pd.NA

        # 删除辅助列
        df.drop(['date', 'is_grow_season'], axis=1, inplace=True)
        
    return df