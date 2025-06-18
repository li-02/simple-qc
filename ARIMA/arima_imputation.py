import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf
from statsmodels.tsa.seasonal import seasonal_decompose
import warnings
warnings.filterwarnings('ignore')


def arima_imputation_single_column(series, max_p=5, max_d=2, max_q=5, ic='aic'):
    """
    对单个时间序列进行ARIMA插补
    """
    # 平稳性检验
    def check_stationarity(ts):
        ts_clean = ts.dropna()
        if len(ts_clean) < 10:
            return False, 1
        
        result = adfuller(ts_clean)
        is_stationary = result[1] <= 0.05
        return is_stationary, result[1]
    
    # 确定差分阶数
    def find_diff_order(ts, max_d=2):
        for d in range(max_d + 1):
            if d == 0:
                test_series = ts
            else:
                test_series = ts.diff(d).dropna()
            
            is_stat, p_value = check_stationarity(test_series)
            if is_stat:
                return d
        return max_d
    
    # 自动选择ARIMA参数
    def auto_arima_params(ts, max_p, max_d, max_q, ic='aic'):
        ts_clean = ts.dropna()
        
        if len(ts_clean) < 20:
            return (1, 1, 1)
        
        d = find_diff_order(ts_clean, max_d)
        
        best_ic = float('inf')
        best_params = (1, d, 1)
        
        for p in range(max_p + 1):
            for q in range(max_q + 1):
                try:
                    model = ARIMA(ts_clean, order=(p, d, q))
                    fitted_model = model.fit()
                    
                    if ic == 'aic':
                        ic_value = fitted_model.aic
                    elif ic == 'bic':
                        ic_value = fitted_model.bic
                    else:
                        ic_value = fitted_model.hqic
                    
                    if ic_value < best_ic:
                        best_ic = ic_value
                        best_params = (p, d, q)
                except:
                    continue
        
        return best_params
    
    # 分段插补处理
    def interpolate_missing_segments(ts, params):
        series_filled = ts.copy()
        missing_mask = ts.isna()
        
        # 处理首尾缺失值
        if missing_mask.iloc[0]:
            first_valid = ts.first_valid_index()
            if first_valid is not None:
                series_filled.loc[:first_valid] = series_filled.loc[first_valid]
        
        if missing_mask.iloc[-1]:
            last_valid = ts.last_valid_index()
            if last_valid is not None:
                series_filled.loc[last_valid:] = series_filled.loc[last_valid]
        
        # 找到缺失段
        missing_segments = []
        start_idx = None
        
        for i, is_missing in enumerate(missing_mask):
            if is_missing and start_idx is None:
                start_idx = i
            elif not is_missing and start_idx is not None:
                missing_segments.append((start_idx, i-1))
                start_idx = None
        
        if start_idx is not None:
            missing_segments.append((start_idx, len(missing_mask)-1))
        
        # 对每个缺失段进行ARIMA插补
        for start_idx, end_idx in missing_segments:
            try:
                before_data = series_filled.iloc[:start_idx].dropna()
                after_data = series_filled.iloc[end_idx+1:].dropna()
                
                if len(before_data) >= 10:
                    model = ARIMA(before_data, order=params)
                    fitted_model = model.fit()
                    
                    n_missing = end_idx - start_idx + 1
                    forecast = fitted_model.forecast(steps=n_missing)
                    series_filled.iloc[start_idx:end_idx+1] = forecast
                
                elif len(after_data) >= 10:
                    reversed_data = after_data.iloc[::-1]
                    model = ARIMA(reversed_data, order=params)
                    fitted_model = model.fit()
                    
                    n_missing = end_idx - start_idx + 1
                    forecast = fitted_model.forecast(steps=n_missing)
                    series_filled.iloc[start_idx:end_idx+1] = forecast[::-1]
                
                else:
                    series_filled.iloc[start_idx:end_idx+1] = series_filled.interpolate().iloc[start_idx:end_idx+1]
                    
            except Exception as e:
                series_filled.iloc[start_idx:end_idx+1] = series_filled.interpolate().iloc[start_idx:end_idx+1]
        
        return series_filled
    
    # 执行插补
    missing_count = series.isna().sum()
    if missing_count == 0:
        return series, {"status": "complete", "missing_count": 0}
    
    # 计算数据的合理范围（用于后续验证）
    valid_data = series.dropna()
    if len(valid_data) > 0:
        data_min = valid_data.min()
        data_max = valid_data.max() 
        data_mean = valid_data.mean()
        data_std = valid_data.std()
        # 设置合理的上下界（均值±3倍标准差，但不超过原数据范围的5倍）
        reasonable_lower = max(data_min - data_std, data_min * 0.1)
        reasonable_upper = min(data_max + data_std, data_max * 3)
    else:
        reasonable_lower, reasonable_upper = 0, 100  # 默认范围
        data_mean = 50
    
    try:
        optimal_params = auto_arima_params(series, max_p, max_d, max_q, ic)
        filled_series = interpolate_missing_segments(series, optimal_params)
        
        # 检查插补结果的合理性
        missing_positions = series.isna()
        filled_values = filled_series[missing_positions]
        unreasonable_mask = (filled_values < reasonable_lower) | (filled_values > reasonable_upper)
        
        if unreasonable_mask.any():
            print(f"  警告: 检测到{unreasonable_mask.sum()}个不合理的插补值 (范围: {reasonable_lower:.2f} - {reasonable_upper:.2f})，使用线性插值替代")
            # 对不合理的值使用更保守的插值方法
            conservative_filled = series.interpolate(method='linear')
            # 如果线性插值也有缺失，进一步处理
            if conservative_filled.isna().any():
                conservative_filled = conservative_filled.fillna(method='ffill').fillna(method='bfill').fillna(data_mean)
            
            # 只替换不合理的插补值
            unreasonable_positions = missing_positions.copy()
            unreasonable_positions.loc[missing_positions] = unreasonable_mask
            filled_series[unreasonable_positions] = conservative_filled[unreasonable_positions]
        
        # 模型验证
        final_model = ARIMA(filled_series, order=optimal_params)
        fitted_final = final_model.fit()
        
        residuals = fitted_final.resid
        mse = np.mean(residuals**2)
        mae = np.mean(np.abs(residuals))
        
        result_info = {
            "status": "success",
            "missing_count": missing_count,
            "arima_params": optimal_params,
            "model_aic": fitted_final.aic,
            "model_bic": fitted_final.bic,
            "mse": mse,
            "mae": mae,
            "unreasonable_corrections": unreasonable_mask.sum() if 'unreasonable_mask' in locals() else 0
        }
        
        return filled_series, result_info
        
    except Exception as e:
        print(f"  ARIMA插补失败: {str(e)}, 使用线性插值")
        filled_series = series.interpolate(method='linear')
        # 如果线性插值仍有缺失值，用前后值填充
        if filled_series.isna().any():
            filled_series = filled_series.fillna(method='ffill').fillna(method='bfill')
            # 如果还有缺失值，用均值填充
            if filled_series.isna().any():
                filled_series = filled_series.fillna(data_mean if 'data_mean' in locals() else 0)
        
        result_info = {
            "status": "fallback_interpolation", 
            "missing_count": missing_count,
            "error": str(e)
        }
        return filled_series, result_info


def arima_imputation_multicolumn(df, time_col='record_time', value_cols=None, 
                                max_p=3, max_d=1, max_q=3, ic='aic', time_freq='30min', keep_original=False):
    """
    使用ARIMA模型对多列时间序列数据进行缺失值插补
    
    参数:
    df: pandas.DataFrame - 包含时间序列数据的DataFrame
    time_col: str - 时间列名 (默认: 'record_time')
    value_cols: list - 需要插补的数值列名列表 (默认: None, 自动识别)
    max_p: int - AR项最大阶数 (默认: 5)
    max_d: int - 差分最大阶数 (默认: 2)  
    max_q: int - MA项最大阶数 (默认: 5)
    ic: str - 信息准则 ('aic', 'bic', 'hqic') (默认: 'aic')
    time_freq: str - 时间间隔 (默认: '30min')
    keep_original: bool - 是否保留原始列并创建新的填充列 (默认: False)
    
    返回:
    pandas.DataFrame - 插补后的完整数据
    dict - 各列的模型信息和统计结果
    """
    
    # 数据预处理
    df_work = df.copy()
    
    # 检查时间列是否存在
    if time_col not in df_work.columns:
        raise ValueError(f"时间列 '{time_col}' 不存在于数据中。可用的列: {list(df_work.columns)}")
    
    df_work[time_col] = pd.to_datetime(df_work[time_col])
    df_work = df_work.sort_values(time_col).reset_index(drop=True)
    
    # 自动识别数值列
    if value_cols is None:
        value_cols = [col for col in df_work.columns if col != time_col and df_work[col].dtype in ['float64', 'int64', 'float32', 'int32']]
    
    print(f"检测到需要插补的列: {value_cols}")
    
    # 设置时间索引
    df_work.set_index(time_col, inplace=True)
    
    # 创建完整的时间索引，使用传入的时间间隔
    full_index = pd.date_range(start=df_work.index.min(), 
                              end=df_work.index.max(), 
                              freq=time_freq)
    df_full = df_work.reindex(full_index)
    
    # 存储各列的插补结果信息
    imputation_results = {}
    
    # 对每一列进行插补
    for col in value_cols:
        print(f"\n正在处理列: {col}")
        missing_before = df_full[col].isna().sum()
        print(f"  缺失值数量: {missing_before}")
        
        if missing_before > 0:
            filled_series, col_info = arima_imputation_single_column(
                df_full[col], max_p, max_d, max_q, ic
            )
            
            if keep_original:
                # 保留原始列，创建新的填充列
                filled_col_name = f"{col}_filled"
                df_full[filled_col_name] = filled_series
                print(f"  创建插补列: {filled_col_name}")
            else:
                # 覆盖原始列
                df_full[col] = filled_series
            
            print(f"  插补状态: {col_info['status']}")
            if col_info['status'] == 'success':
                print(f"  最优参数: {col_info['arima_params']}")
                print(f"  模型AIC: {col_info['model_aic']:.2f}")
            
            imputation_results[col] = col_info
        else:
            print(f"  无缺失值，跳过")
            if keep_original:
                # 即使没有缺失值，也创建filled列以保持一致性
                filled_col_name = f"{col}_filled"
                df_full[filled_col_name] = df_full[col]
                print(f"  创建副本列: {filled_col_name}")
            imputation_results[col] = {"status": "complete", "missing_count": 0}
    
    # 返回原始索引范围的数据
    result_df = df_full.reset_index()
    
    # 修复时间列名称问题：reset_index()可能会将时间列重命名为'index'
    if 'index' in result_df.columns and time_col not in result_df.columns:
        result_df = result_df.rename(columns={'index': time_col})
    
    # 确保原始数据有时间列用于比较
    if time_col not in df.columns:
        # 如果原始数据的时间列是索引，需要重置
        if hasattr(df.index, 'dtype') and 'datetime' in str(df.index.dtype):
            original_times = df.index
        else:
            # 如果索引不是datetime类型，尝试从重置索引后获取
            df_reset = df.reset_index()
            if time_col in df_reset.columns:
                original_times = df_reset[time_col]
            else:
                # 如果重置索引后仍然没有时间列，直接使用索引
                original_times = df.index
    else:
        original_times = df[time_col]
    
    # 安全地过滤数据，确保时间列存在
    try:
        result_df = result_df[result_df[time_col].isin(original_times)]
    except (KeyError, TypeError) as e:
        # 如果过滤失败，记录警告并返回完整结果
        print(f"警告: 无法按时间范围过滤数据 ({e})，返回完整插补结果")
        pass
    
    # 汇总信息
    summary_info = {
        "processed_columns": value_cols,
        "total_columns": len(value_cols),
        "successful_imputations": sum(1 for info in imputation_results.values() if info['status'] == 'success'),
        "fallback_imputations": sum(1 for info in imputation_results.values() if info['status'] == 'fallback_interpolation'),
        "complete_columns": sum(1 for info in imputation_results.values() if info['status'] == 'complete'),
        "column_details": imputation_results,
        "keep_original": keep_original
    }
    
    return result_df, summary_info


# 简化版本的入口函数（多列）
def fill_missing_values_multicolumn(df, time_col='record_time', value_cols=None, time_freq='30min', keep_original=False):
    """
    简化的多列插补调用接口
    
    参数:
    df: pandas.DataFrame - 包含时间序列数据的DataFrame  
    time_col: str - 时间列名
    value_cols: list - 需要插补的列名列表，None时自动识别数值列
    time_freq: str - 时间间隔 (默认: '30min')
    keep_original: bool - 是否保留原始列并创建新的填充列 (默认: False)
    
    返回:
    pandas.DataFrame - 插补后的数据
    """
    # 对于环境数据使用更保守的ARIMA参数
    result_df, _ = arima_imputation_multicolumn(df, time_col, value_cols, 
                                               max_p=3, max_d=1, max_q=3, ic='aic', 
                                               time_freq=time_freq, keep_original=keep_original)
    return result_df


def fill_environmental_data(df, time_col='record_time', value_cols=None, time_freq='30min', keep_original=False):
    """
    专门针对环境数据的插补函数（AQI、气象数据等）
    使用更保守的参数和更严格的数值检查
    
    参数:
    df: pandas.DataFrame - 包含时间序列数据的DataFrame  
    time_col: str - 时间列名
    value_cols: list - 需要插补的列名列表，None时自动识别数值列
    time_freq: str - 时间间隔 (默认: '30min')
    keep_original: bool - 是否保留原始列并创建新的填充列 (默认: False)
    
    返回:
    pandas.DataFrame - 插补后的数据
    """
    print("使用环境数据专用插补策略")
    
    # 使用非常保守的ARIMA参数，减少模型复杂度
    result_df, info = arima_imputation_multicolumn(
        df, time_col, value_cols, 
        max_p=2, max_d=1, max_q=2, ic='aic', time_freq=time_freq, keep_original=keep_original
    )
    
    # 打印插补信息
    if 'column_details' in info:
        for col, col_info in info['column_details'].items():
            if col_info['status'] == 'success':
                corrections = col_info.get('unreasonable_corrections', 0)
                if corrections > 0:
                    print(f"  {col}: 已纠正 {corrections} 个异常插补值")
                else:
                    print(f"  {col}: 插补正常")
    
    return result_df


# 保持原有的单列函数以便向后兼容
def fill_missing_values(df, time_col='record_time', value_col='pm2_5', time_freq='30min'):
    """
    单列插补（向后兼容）
    """
    result_df, _ = arima_imputation_multicolumn(df, time_col, [value_col], 
                                               max_p=5, max_d=2, max_q=5, ic='aic', time_freq=time_freq)
    return result_df

"""
# 自动识别所有数值列进行插补
result_df = fill_missing_values_multicolumn(your_dataframe)

# 指定特定列进行插补
result_df = fill_missing_values_multicolumn(
    your_dataframe, 
    time_col='record_time',
    value_cols=['pm2.5', 'pm10', 'co2', 'co']
)

# 高级调用
result_df, detailed_info = arima_imputation_multicolumn(
    df=your_dataframe,
    time_col='record_time',
    value_cols=['pm2.5', 'pm10', 'co2', 'co'],  # None时自动识别
    max_p=5,
    max_d=2, 
    max_q=5,
    ic='aic'
)

"""