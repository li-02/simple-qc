# ARIMA插补性能测试工具

本目录包含用于评估ARIMA插补算法性能的测试脚本。

## 文件说明

### 1. `arima_performance_test.py` - 完整测试工具
功能最全面的测试脚本，包含：
- 多种缺失值模式测试（随机、连续、周期性、块状）
- 多个缺失率水平测试
- 详细的性能指标计算
- 完整的报告生成
- 可视化图表输出

### 2. `quick_arima_test.py` - 快速测试工具
简化版本，适合快速评估：
- 随机缺失模式
- 基本性能指标
- 简单可视化
- 交互式使用界面

## 使用方法

### 快速测试（推荐）

```bash
cd test
python quick_arima_test.py
```

按提示输入：
- 数据文件路径（支持CSV/Excel）
- 要测试的列名
- 时间列名

### 完整测试

```bash
cd test  
python arima_performance_test.py
```

选择测试模式：
1. 快速测试（较少配置）
2. 完整测试（所有配置）
3. 自定义测试

### 编程接口使用

```python
from quick_arima_test import quick_arima_performance_test

# 快速测试
results = quick_arima_performance_test(
    data_path="../data/your_data.csv",
    column_name="pm2_5", 
    time_col="record_time",
    missing_rates=[0.05, 0.1, 0.2, 0.3],
    n_trials=5
)
```

## 测试原理

1. **数据准备**：加载完整的无缺失值数据作为"真值"
2. **缺失值模拟**：人工创建不同比例和模式的缺失值
3. **插补测试**：使用ARIMA方法进行插补
4. **性能评估**：比较插补值与真值，计算性能指标
5. **结果分析**：生成报告和可视化图表

## 性能指标

- **MAE**：平均绝对误差（越小越好）
- **RMSE**：均方根误差（越小越好）
- **R²**：决定系数（越接近1越好）
- **MAPE**：平均绝对百分比误差（越小越好）

## 测试配置

### 缺失率
- 低缺失率：5%, 10%
- 中等缺失率：15%, 20%  
- 高缺失率：30%

### 缺失模式
- **随机缺失**：数据点随机丢失
- **连续缺失**：连续时间段数据丢失
- **周期性缺失**：按一定周期规律缺失
- **块状缺失**：大块连续数据丢失

## 输出结果

### 控制台输出
- 实时测试进度
- 每次试验的性能指标
- 汇总统计结果

### 文件输出
- 测试报告（TXT格式）
- 性能图表（PNG格式）
- 详细数据（包含在测试类中）

## 注意事项

1. **数据要求**：
   - 时间序列数据，包含时间列和数值列
   - 原始数据应无缺失值和异常值
   - 数据应具有一定的时间规律性

2. **参数调整**：
   - 可根据数据特点调整ARIMA参数范围
   - 可修改测试的缺失率和试验次数
   - 可添加自定义的性能指标

3. **运行时间**：
   - 完整测试可能需要较长时间
   - 建议先使用快速测试了解大致性能
   - 大数据集建议减少试验次数

## 示例输出

```
测试结果汇总
========================================

缺失率: 0.05
成功试验: 3/3
MAE均值: 2.1543 ± 0.1234
RMSE均值: 3.2567 ± 0.2345
R²均值: 0.8765 ± 0.0123
MAPE均值: 12.34% ± 1.56%

缺失率: 0.1
成功试验: 3/3
MAE均值: 2.8976 ± 0.1567
RMSE均值: 4.1234 ± 0.2678
R²均值: 0.8234 ± 0.0234
MAPE均值: 15.67% ± 2.34%
```

## 故障排除

1. **导入错误**：确保ARIMA模块在正确路径
2. **数据格式错误**：检查CSV/Excel文件格式
3. **列名不存在**：确认列名拼写正确
4. **内存不足**：减少试验次数或使用更小的数据集 