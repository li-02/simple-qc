"""
数据分区模块
"""
import pandas as pd
from r_scripts import robjects, StrVector, FloatVector, IntVector, pandas2ri
from rpy2.robjects.conversion import localconverter
from config.constants import DEL_LIST, NO_USE_LIST


def ustar_data(file_name, longitude, latitude, timezone, data, qc_indicators,logger=None):
    """
    执行u*筛选、插补和分区
    """
    def log_info(message):
        if logger:
            logger.info(message)
        else:
            print(message)
    try:
        log_info("开始执行u*筛选、插补和分区...")
        
        # 格式化时间
        log_info("正在格式化时间数据...")
        data['record_time'] = pd.to_datetime(data['record_time'])
        
        # 重命名列为R格式
        log_info("正在重命名列为R格式...")
        data = data.rename(columns={'record_time': 'DateTime'})
        
        # 准备R需要的列
        log_info("正在准备R需要的变量...")
        data['NEE'] = data['co2_despiking']
        data['rH'] = data['rh_threshold_limit']
        data['Rg'] = data['rg_1_1_2_threshold_limit']
        data['Tair'] = data['ta_1_2_1_threshold_limit']
        data['VPD'] = data['vpd_threshold_limit'] * 0.01  # Pa to hPa
        log_info(f"NEE数据点数: {data['NEE'].notna().sum()}")
        log_info(f"有效数据比例: {data['NEE'].notna().sum()/len(data)*100:.1f}%")
        
        # 准备R函数参数
        log_info("正在准备R函数参数...")
        pandas2ri.activate()
        r_filename = StrVector([file_name])
        r_longitude = FloatVector([longitude])
        r_latitude = FloatVector([latitude])
        r_timezone = IntVector([timezone])
        
        # 准备插补指标
        log_info("正在准备插补指标...")
        gapfill_indicators = []
        for indicator in qc_indicators:
            if indicator['is_gapfill'] == 1 and indicator['code'] not in NO_USE_LIST:
                if indicator['belong_to'] == 'flux' and indicator['code'] in data.columns:
                    gapfill_indicators.append(indicator['code'] + '_threshold_limit')
        
        gapfill_indicators += ['h2o_despiking', 'le_despiking', 'h_despiking']
        log_info(f"需要插补的指标: {gapfill_indicators}")
        
        # 转换数据为R格式
        log_info("正在转换数据为R格式...")
        with localconverter(robjects.default_converter + pandas2ri.converter):
            data_r = robjects.conversion.py2rpy(data)
        r_gapfill_indicators = StrVector(gapfill_indicators)
        
        # 调用R函数
        log_info("正在调用R函数进行u*筛选、插补和分区...")
        log_info("这可能需要几分钟时间，请耐心等待...")
        result_data = robjects.r['r_co2_flux'](
            r_filename, r_longitude, r_latitude, r_timezone, data_r, r_gapfill_indicators
        )
        log_info("R函数执行完成")
        
        # 检查R函数返回结果
        log_info(f"R函数返回结果类型: {type(result_data)}")
        if result_data is None:
            log_info("错误: R函数返回了None")
            return data  # 返回原始数据
        
        # 将R结果转回Python
        log_info("正在转换R结果回Python...")
        try:
            with localconverter(robjects.default_converter + pandas2ri.converter):
                result_data = robjects.conversion.rpy2py(result_data)
            log_info(f"转换后Python对象类型: {type(result_data)}")
            log_info(f"转换后数据形状: {result_data.shape if hasattr(result_data, 'shape') else '无形状信息'}")
        except Exception as e:
            log_info(f"数据转换失败: {str(e)}")
            return data  # 转换失败时返回原始数据
        
        log_info("正在处理结果数据...")
        
        # 检查结果数据是否为空
        if result_data is None or (hasattr(result_data, 'empty') and result_data.empty):
            log_info("警告: 转换后的结果数据为空，返回原始数据")
            return data
        
        # 处理结果数据
        try:
            result_data = result_data.rename(columns={'DateTime': 'record_time'})
            log_info("已重命名DateTime列为record_time")
            
            if 'record_time' in result_data.columns:
                result_data['record_time'] = result_data['record_time'].dt.tz_localize(None)
                result_data = result_data.set_index('record_time')
                log_info("已设置record_time为索引")
            else:
                log_info("警告: 结果中缺少record_time列")
            
            # 删除不需要的列
            for col in DEL_LIST:
                if col in result_data.columns:
                    result_data = result_data.drop(col, axis=1)
                    log_info(f"已删除列: {col}")
            
            # 转换列名为小写
            result_data.columns = [col.lower() for col in result_data.columns]
            log_info("已转换列名为小写")
            
            # 重置索引
            result_data = result_data.reset_index()
            log_info(f"最终结果数据形状: {result_data.shape}")
            log_info(f"最终结果列名: {list(result_data.columns)}")
            
            return result_data
            
        except Exception as e:
            log_info(f"处理结果数据时出错: {str(e)}")
            return data  # 处理失败时返回原始数据
        
    except Exception as e:
        log_info(f"u*处理过程出错: {str(e)}")
        return data  # 出错时返回原始数据