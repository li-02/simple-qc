import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ARIMA.arima_imputation import arima_imputation_multicolumn
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def quick_arima_performance_test(data_path, column_name, time_col='record_time', 
                                missing_rates=[0.05, 0.1, 0.2], n_trials=3):
    """
    快速ARIMA插补性能测试
    
    参数:
    data_path: str - 数据文件路径
    column_name: str - 要测试的列名
    time_col: str - 时间列名
    missing_rates: list - 测试的缺失率
    n_trials: int - 每个缺失率的试验次数
    
    返回:
    dict - 测试结果
    """
    print("开始ARIMA插补性能快速测试")
    print("=" * 40)
    
    # 加载数据
    print(f"加载数据: {data_path}")
    if data_path.endswith('.csv'):
        data = pd.read_csv(data_path)
    elif data_path.endswith('.xlsx'):
        data = pd.read_excel(data_path)
    else:
        raise ValueError("不支持的文件格式")
    
    print(f"数据形状: {data.shape}")
    print(f"测试列: {column_name}")
    
    if column_name not in data.columns:
        print(f"可用列: {list(data.columns)}")
        raise ValueError(f"列 '{column_name}' 不存在")
    
    # 检查原始数据的缺失值
    original_missing = data[column_name].isnull().sum()
    if original_missing > 0:
        print(f"警告: 原始数据包含 {original_missing} 个缺失值")
    
    results = {}
    
    for missing_rate in missing_rates:
        print(f"\n测试缺失率: {missing_rate}")
        print("-" * 30)
        
        trial_results = []
        
        for trial in range(n_trials):
            # 创建测试数据
            test_data = data.copy()
            original_series = test_data[column_name].copy()
            
            # 随机创建缺失值
            n_total = len(original_series)
            n_missing = int(n_total * missing_rate)
            
            missing_indices = np.random.choice(n_total, n_missing, replace=False)
            test_data.loc[missing_indices, column_name] = np.nan
            
            try:
                # ARIMA插补
                filled_data, info = arima_imputation_multicolumn(
                    test_data, 
                    time_col=time_col, 
                    value_cols=[column_name],
                    max_p=3, max_d=1, max_q=3,
                    time_freq='60min'
                )
                
                # 计算性能指标 - 只评估插补位置
                filled_series = filled_data[column_name]
                original_values = original_series.iloc[missing_indices]
                filled_values = filled_series.iloc[missing_indices]
                
                # 移除nan值
                valid_mask = ~(pd.isna(original_values) | pd.isna(filled_values))
                if valid_mask.sum() > 0:
                    orig_clean = original_values[valid_mask]
                    fill_clean = filled_values[valid_mask]
                    
                    mae = mean_absolute_error(orig_clean, fill_clean)
                    mse = mean_squared_error(orig_clean, fill_clean)
                    rmse = np.sqrt(mse)
                    r2 = r2_score(orig_clean, fill_clean)
                    
                    # MAPE
                    mape = np.mean(np.abs((orig_clean - fill_clean) / orig_clean)) * 100
                    
                    trial_result = {
                        'trial': trial + 1,
                        'MAE': mae,
                        'MSE': mse,
                        'RMSE': rmse,
                        'R2': r2,
                        'MAPE': mape,
                        'status': info['column_details'][column_name]['status'],
                        'missing_count': n_missing,
                        'valid_predictions': len(orig_clean)
                    }
                    
                    trial_results.append(trial_result)
                    print(f"  试验 {trial+1}: MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}")
                    
            except Exception as e:
                print(f"  试验 {trial+1} 失败: {str(e)}")
                continue
        
        # 汇总结果
        if trial_results:
            avg_results = {}
            for metric in ['MAE', 'MSE', 'RMSE', 'R2', 'MAPE']:
                values = [r[metric] for r in trial_results]
                avg_results[f'{metric}_mean'] = np.mean(values)
                avg_results[f'{metric}_std'] = np.std(values)
            
            avg_results['successful_trials'] = len(trial_results)
            avg_results['total_trials'] = n_trials
            avg_results['details'] = trial_results
            
            results[missing_rate] = avg_results
    
    # 打印汇总结果
    print("\n" + "=" * 40)
    print("测试结果汇总")
    print("=" * 40)
    
    for missing_rate, result in results.items():
        print(f"\n缺失率: {missing_rate}")
        print(f"成功试验: {result['successful_trials']}/{result['total_trials']}")
        print(f"MAE均值: {result['MAE_mean']:.4f} ± {result['MAE_std']:.4f}")
        print(f"RMSE均值: {result['RMSE_mean']:.4f} ± {result['RMSE_std']:.4f}")
        print(f"R²均值: {result['R2_mean']:.4f} ± {result['R2_std']:.4f}")
        print(f"MAPE均值: {result['MAPE_mean']:.2f}% ± {result['MAPE_std']:.2f}%")
    
    # 生成简单的可视化
    if len(results) > 1:
        plot_quick_results(results, column_name)
    
    return results

def plot_quick_results(results, column_name):
    """快速绘制结果图表"""
    missing_rates = list(results.keys())
    mae_means = [results[mr]['MAE_mean'] for mr in missing_rates]
    mae_stds = [results[mr]['MAE_std'] for mr in missing_rates]
    rmse_means = [results[mr]['RMSE_mean'] for mr in missing_rates]
    r2_means = [results[mr]['R2_mean'] for mr in missing_rates]
    
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(f'ARIMA插补性能测试 - {column_name}', fontsize=14)
    
    # MAE
    axes[0].errorbar(missing_rates, mae_means, yerr=mae_stds, marker='o', capsize=5)
    axes[0].set_xlabel('缺失率')
    axes[0].set_ylabel('MAE')
    axes[0].set_title('平均绝对误差')
    axes[0].grid(True, alpha=0.3)
    
    # RMSE
    axes[1].plot(missing_rates, rmse_means, marker='s', color='orange')
    axes[1].set_xlabel('缺失率')
    axes[1].set_ylabel('RMSE')
    axes[1].set_title('均方根误差')
    axes[1].grid(True, alpha=0.3)
    
    # R²
    axes[2].plot(missing_rates, r2_means, marker='^', color='green')
    axes[2].set_xlabel('缺失率')
    axes[2].set_ylabel('R²')
    axes[2].set_title('决定系数')
    axes[2].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plot_file = f"arima_quick_test_{column_name}_{timestamp}.png"
    plt.savefig(plot_file, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"\n图表已保存: {plot_file}")

def main():
    """主函数"""
    print("ARIMA插补快速性能测试")
    print("=" * 30)
    
    # 默认参数
    default_data_path = "../data/2024_shisanling_flux_raw_data.csv"
    
    # 获取用户输入
    data_path = input(f"数据文件路径 (默认: {default_data_path}): ").strip()
    if not data_path:
        data_path = default_data_path
    
    if not os.path.exists(data_path):
        print(f"文件不存在: {data_path}")
        return
    
    # 预览数据列
    if data_path.endswith('.csv'):
        preview_data = pd.read_csv(data_path)
    else:
        preview_data = pd.read_excel(data_path)
    
    numeric_cols = [col for col in preview_data.columns 
                   if preview_data[col].dtype in ['float64', 'int64', 'float32', 'int32']]
    print(f"\n可用的数值列: {numeric_cols}")
    
    column_name = input("要测试的列名: ").strip()
    time_col = input("时间列名 (默认: record_time): ").strip()
    if not time_col:
        time_col = 'record_time'
    
    # 运行测试
    try:
        results = quick_arima_performance_test(
            data_path=data_path,
            column_name=column_name,
            time_col=time_col,
            missing_rates=[0.05, 0.1, 0.2, 0.3],
            n_trials=3
        )
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")

if __name__ == "__main__":
    main() 