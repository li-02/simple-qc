import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import sys
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# 添加父目录到路径以便导入ARIMA模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ARIMA.arima_imputation import fill_missing_values_multicolumn, arima_imputation_multicolumn

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False

class ARIMAPerformanceTest:
    """ARIMA插补性能测试类"""
    
    def __init__(self, data_path=None):
        """
        初始化测试类
        
        参数:
        data_path: str - 数据文件路径，如果为None则需要手动设置数据
        """
        self.data_path = data_path
        self.original_data = None
        self.test_results = {}
        self.performance_metrics = {}
        
    def load_data(self, data_path=None):
        """加载测试数据"""
        if data_path is None:
            data_path = self.data_path
            
        if data_path is None:
            raise ValueError("请提供数据文件路径")
            
        print(f"正在加载数据: {data_path}")
        
        try:
            # 尝试读取CSV文件
            if data_path.endswith('.csv'):
                self.original_data = pd.read_csv(data_path)
            elif data_path.endswith('.xlsx'):
                self.original_data = pd.read_excel(data_path)
            else:
                raise ValueError("不支持的文件格式，请使用CSV或Excel文件")
                
            print(f"数据加载成功: {self.original_data.shape}")
            print(f"列名: {list(self.original_data.columns)}")
            
            # 检查数据是否有缺失值
            missing_count = self.original_data.isnull().sum().sum()
            if missing_count > 0:
                print(f"警告: 原始数据包含 {missing_count} 个缺失值")
                
            return True
            
        except Exception as e:
            print(f"数据加载失败: {str(e)}")
            return False
    
    def create_missing_patterns(self, data, missing_rate=0.1, pattern_type='random'):
        """
        创建不同模式的缺失值
        
        参数:
        data: pandas.Series - 原始完整数据
        missing_rate: float - 缺失值比例 (0-1)
        pattern_type: str - 缺失模式类型
            - 'random': 随机缺失
            - 'consecutive': 连续缺失
            - 'periodic': 周期性缺失
            - 'block': 块状缺失
        """
        data_with_missing = data.copy()
        n_total = len(data)
        n_missing = int(n_total * missing_rate)
        
        if pattern_type == 'random':
            # 随机缺失
            missing_indices = np.random.choice(n_total, n_missing, replace=False)
            data_with_missing.iloc[missing_indices] = np.nan
            
        elif pattern_type == 'consecutive':
            # 连续缺失 - 随机选择几个连续段
            n_segments = min(5, max(1, n_missing // 10))  # 3-5个连续段
            segment_length = n_missing // n_segments
            
            for i in range(n_segments):
                start_idx = np.random.randint(0, n_total - segment_length)
                end_idx = start_idx + segment_length
                data_with_missing.iloc[start_idx:end_idx] = np.nan
                
        elif pattern_type == 'periodic':
            # 周期性缺失 - 每隔一定间隔缺失
            interval = max(1, n_total // n_missing)
            for i in range(0, n_total, interval):
                if np.random.random() < 0.7:  # 70%概率缺失
                    data_with_missing.iloc[i] = np.nan
                    
        elif pattern_type == 'block':
            # 块状缺失 - 几个大的连续块
            n_blocks = min(3, max(1, n_missing // 20))
            block_size = n_missing // n_blocks
            
            for i in range(n_blocks):
                start_idx = np.random.randint(0, n_total - block_size)
                end_idx = start_idx + block_size
                data_with_missing.iloc[start_idx:end_idx] = np.nan
        
        return data_with_missing
    
    def calculate_metrics(self, original, predicted, mask=None):
        """
        计算性能指标
        
        参数:
        original: array-like - 原始真实值
        predicted: array-like - 预测/插补值
        mask: array-like - 缺失值位置掩码，True表示缺失位置
        """
        if mask is not None:
            # 只计算缺失位置的指标
            original_masked = original[mask]
            predicted_masked = predicted[mask]
        else:
            original_masked = original
            predicted_masked = predicted
        
        # 移除可能的nan值
        valid_mask = ~(pd.isna(original_masked) | pd.isna(predicted_masked))
        if valid_mask.sum() == 0:
            return {
                'MAE': np.nan,
                'MSE': np.nan,
                'RMSE': np.nan,
                'MAPE': np.nan,
                'R2': np.nan,
                'valid_points': 0
            }
        
        orig_clean = original_masked[valid_mask]
        pred_clean = predicted_masked[valid_mask]
        
        # 计算各种指标
        mae = mean_absolute_error(orig_clean, pred_clean)
        mse = mean_squared_error(orig_clean, pred_clean)
        rmse = np.sqrt(mse)
        
        # MAPE - 平均绝对百分比误差
        mape = np.mean(np.abs((orig_clean - pred_clean) / orig_clean)) * 100
        
        # R²
        r2 = r2_score(orig_clean, pred_clean)
        
        return {
            'MAE': mae,
            'MSE': mse, 
            'RMSE': rmse,
            'MAPE': mape,
            'R2': r2,
            'valid_points': len(orig_clean)
        }
    
    def test_single_column(self, column_name, time_col='record_time', 
                          missing_rates=[0.05, 0.1, 0.2, 0.3], 
                          pattern_types=['random', 'consecutive', 'periodic', 'block'],
                          n_trials=5):
        """
        测试单列的插补性能
        
        参数:
        column_name: str - 要测试的列名
        time_col: str - 时间列名
        missing_rates: list - 测试的缺失率列表
        pattern_types: list - 测试的缺失模式列表
        n_trials: int - 每个配置的试验次数
        """
        print(f"\n开始测试列: {column_name}")
        print(f"缺失率: {missing_rates}")
        print(f"缺失模式: {pattern_types}")
        print(f"试验次数: {n_trials}")
        
        if column_name not in self.original_data.columns:
            raise ValueError(f"列 '{column_name}' 不存在于数据中")
        
        results = {}
        
        for missing_rate in missing_rates:
            for pattern_type in pattern_types:
                print(f"\n测试配置: 缺失率={missing_rate}, 模式={pattern_type}")
                
                trial_metrics = []
                
                for trial in range(n_trials):
                    # 创建带缺失值的数据
                    test_data = self.original_data.copy()
                    original_series = test_data[column_name].copy()
                    
                    # 创建缺失值
                    missing_series = self.create_missing_patterns(
                        original_series, missing_rate, pattern_type
                    )
                    test_data[column_name] = missing_series
                    
                    try:
                        # 使用ARIMA插补
                        filled_data, imputation_info = arima_imputation_multicolumn(
                            test_data, 
                            time_col=time_col, 
                            value_cols=[column_name],
                            max_p=3, max_d=1, max_q=3
                        )
                        
                        # 获取插补后的数据
                        filled_series = filled_data[column_name]
                        
                        # 计算性能指标 - 只评估插补的位置
                        missing_mask = missing_series.isna()
                        metrics = self.calculate_metrics(
                            original_series, filled_series, missing_mask
                        )
                        
                        # 添加额外信息
                        metrics['trial'] = trial + 1
                        metrics['missing_count'] = missing_mask.sum()
                        metrics['imputation_status'] = imputation_info['column_details'][column_name]['status']
                        
                        trial_metrics.append(metrics)
                        
                        print(f"  试验 {trial+1}: MAE={metrics['MAE']:.4f}, RMSE={metrics['RMSE']:.4f}, R²={metrics['R2']:.4f}")
                        
                    except Exception as e:
                        print(f"  试验 {trial+1} 失败: {str(e)}")
                        continue
                
                # 汇总试验结果
                if trial_metrics:
                    avg_metrics = {}
                    for key in ['MAE', 'MSE', 'RMSE', 'MAPE', 'R2']:
                        values = [m[key] for m in trial_metrics if not pd.isna(m[key])]
                        if values:
                            avg_metrics[f'{key}_mean'] = np.mean(values)
                            avg_metrics[f'{key}_std'] = np.std(values)
                            avg_metrics[f'{key}_min'] = np.min(values)
                            avg_metrics[f'{key}_max'] = np.max(values)
                    
                    avg_metrics['successful_trials'] = len(trial_metrics)
                    avg_metrics['total_trials'] = n_trials
                    
                    results[(missing_rate, pattern_type)] = {
                        'summary': avg_metrics,
                        'details': trial_metrics
                    }
        
        self.test_results[column_name] = results
        return results
    
    def generate_report(self, output_dir='test_results'):
        """生成测试报告"""
        if not self.test_results:
            print("没有测试结果可以生成报告")
            return
        
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 生成文本报告
        report_file = os.path.join(output_dir, f"arima_performance_report_{timestamp}.txt")
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("ARIMA插补性能测试报告\n")
            f.write("=" * 50 + "\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"数据形状: {self.original_data.shape}\n\n")
            
            for column_name, results in self.test_results.items():
                f.write(f"\n列: {column_name}\n")
                f.write("-" * 30 + "\n")
                
                # 创建结果表格
                summary_data = []
                for (missing_rate, pattern_type), result in results.items():
                    summary = result['summary']
                    row = {
                        '缺失率': missing_rate,
                        '缺失模式': pattern_type,
                        'MAE均值': f"{summary.get('MAE_mean', 0):.4f}",
                        'MAE标准差': f"{summary.get('MAE_std', 0):.4f}",
                        'RMSE均值': f"{summary.get('RMSE_mean', 0):.4f}",
                        'R²均值': f"{summary.get('R2_mean', 0):.4f}",
                        '成功试验': f"{summary.get('successful_trials', 0)}/{summary.get('total_trials', 0)}"
                    }
                    summary_data.append(row)
                
                # 写入表格
                if summary_data:
                    df_summary = pd.DataFrame(summary_data)
                    f.write(df_summary.to_string(index=False))
                    f.write("\n\n")
        
        print(f"文本报告已保存到: {report_file}")
        
        # 生成可视化图表
        self.plot_results(output_dir, timestamp)
        
        return report_file
    
    def plot_results(self, output_dir='test_results', timestamp=None):
        """生成可视化图表"""
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        for column_name, results in self.test_results.items():
            # 准备数据
            plot_data = []
            for (missing_rate, pattern_type), result in results.items():
                summary = result['summary']
                plot_data.append({
                    '缺失率': missing_rate,
                    '缺失模式': pattern_type,
                    'MAE': summary.get('MAE_mean', 0),
                    'RMSE': summary.get('RMSE_mean', 0),
                    'R²': summary.get('R2_mean', 0),
                    'MAPE': summary.get('MAPE_mean', 0)
                })
            
            if not plot_data:
                continue
                
            df_plot = pd.DataFrame(plot_data)
            
            # 创建子图
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f'ARIMA插补性能测试结果 - {column_name}', fontsize=16)
            
            # MAE vs 缺失率
            sns.lineplot(data=df_plot, x='缺失率', y='MAE', hue='缺失模式', marker='o', ax=axes[0,0])
            axes[0,0].set_title('平均绝对误差 (MAE)')
            axes[0,0].grid(True, alpha=0.3)
            
            # RMSE vs 缺失率
            sns.lineplot(data=df_plot, x='缺失率', y='RMSE', hue='缺失模式', marker='s', ax=axes[0,1])
            axes[0,1].set_title('均方根误差 (RMSE)')
            axes[0,1].grid(True, alpha=0.3)
            
            # R² vs 缺失率
            sns.lineplot(data=df_plot, x='缺失率', y='R²', hue='缺失模式', marker='^', ax=axes[1,0])
            axes[1,0].set_title('决定系数 (R²)')
            axes[1,0].grid(True, alpha=0.3)
            
            # MAPE vs 缺失率
            sns.lineplot(data=df_plot, x='缺失率', y='MAPE', hue='缺失模式', marker='D', ax=axes[1,1])
            axes[1,1].set_title('平均绝对百分比误差 (MAPE)')
            axes[1,1].grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # 保存图表
            plot_file = os.path.join(output_dir, f"arima_performance_plot_{column_name}_{timestamp}.png")
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"图表已保存到: {plot_file}")
    
    def quick_test(self, data_path, column_name, time_col='record_time'):
        """快速测试接口"""
        print("开始ARIMA插补性能快速测试")
        print("=" * 50)
        
        # 加载数据
        self.data_path = data_path
        if not self.load_data():
            return False
        
        # 运行测试
        results = self.test_single_column(
            column_name=column_name,
            time_col=time_col,
            missing_rates=[0.05, 0.1, 0.2],
            pattern_types=['random', 'consecutive'],
            n_trials=3
        )
        
        # 生成报告
        report_file = self.generate_report()
        
        print("\n测试完成!")
        print(f"详细报告: {report_file}")
        
        return True


def main():
    """主函数 - 演示如何使用测试类"""
    print("ARIMA插补性能测试工具")
    print("=" * 30)
    
    # 示例用法1: 快速测试
    print("\n选择测试模式:")
    print("1. 快速测试 (较少配置)")
    print("2. 完整测试 (所有配置)")
    print("3. 自定义测试")
    
    choice = input("请输入选择 (1-3): ").strip()
    
    # 获取数据文件路径
    default_data_path = "../data/2024_shisanling_flux_raw_data.csv"
    data_path = input(f"请输入数据文件路径 (默认: {default_data_path}): ").strip()
    if not data_path:
        data_path = default_data_path
    
    # 检查文件是否存在
    if not os.path.exists(data_path):
        print(f"文件不存在: {data_path}")
        return
    
    # 创建测试器
    tester = ARIMAPerformanceTest(data_path)
    
    if choice == '1':
        # 快速测试
        column_name = input("请输入要测试的列名: ").strip()
        time_col = input("请输入时间列名 (默认: record_time): ").strip()
        if not time_col:
            time_col = 'record_time'
            
        tester.quick_test(data_path, column_name, time_col)
        
    elif choice == '2':
        # 完整测试
        if not tester.load_data():
            return
            
        # 显示可用列
        numeric_cols = [col for col in tester.original_data.columns 
                       if tester.original_data[col].dtype in ['float64', 'int64', 'float32', 'int32']]
        print(f"\n可用的数值列: {numeric_cols}")
        
        column_name = input("请输入要测试的列名: ").strip()
        time_col = input("请输入时间列名 (默认: record_time): ").strip()
        if not time_col:
            time_col = 'record_time'
        
        # 运行完整测试
        results = tester.test_single_column(
            column_name=column_name,
            time_col=time_col,
            missing_rates=[0.05, 0.1, 0.15, 0.2, 0.3],
            pattern_types=['random', 'consecutive', 'periodic', 'block'],
            n_trials=5
        )
        
        # 生成报告
        tester.generate_report()
        
    elif choice == '3':
        # 自定义测试
        print("自定义测试功能，请参考代码中的类方法进行定制")
        
    else:
        print("无效选择")


if __name__ == "__main__":
    main() 