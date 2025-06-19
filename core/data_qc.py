"""
数据质量控制模块
"""

import pandas as pd
import numpy as np
from config.constants import CAMPBELL_SITES, NOT_CONVERT_LIST, NEEDED_INDICES
from processors.storage_correction import (
    do_add_strg,
    not_add_strg,
    filter_flux_by_qc_flags,
    copy_flux_columns_without_qc_filter,
    handle_campbell_special_case,
)
from processors.thresholds import threshold_limit
from processors.gap_filling import gap_fill_par, gapfill
from processors.despiking import despiking_data
from processors.abnormal_data import del_abnormal_data
from processors.partitioning import ustar_data
from ARIMA.arima_imputation import fill_missing_values_multicolumn, fill_environmental_data

class DataQc:
    """
    数据质量控制类

    对flux, aqi, sapflow, nai数据进行质量控制
    """

    def __init__(
        self,
        data,
        filename,
        longitude,
        latitude,
        qc_flag_list,
        is_strg,
        timezone,
        qc_indicators,
        data_type,
        task_id,
        ftp,
        logger,
        despiking_z=4,
        time_freq="30min",
    ):
        """
        初始化数据质量控制类

        Args:
            data: 原始数据
            filename: 文件名
            longitude: 经度
            latitude: 纬度
            qc_flag_list: 质量标记列表（已废弃，保留以确保向后兼容性）
            is_strg: 是否进行存储项校正
            timezone: 时区
            qc_indicators: 质量控制指标
            data_type: 数据类型
            task_id: 任务ID
            ftp: FTP站点
            logger: 日志记录器
            despiking_z: 去尖峰的z值，默认为4
            time_freq: 时间间隔，默认为"30min"
        """
        self.filename = filename
        self.qc_flag_list = qc_flag_list  # 保留以确保向后兼容性，但不再使用
        self.is_strg = is_strg
        self.task_id = task_id
        self.despiking_z = despiking_z
        self.longitude = longitude
        self.latitude = latitude
        self.timezone = timezone
        self.ftp = ftp
        self.qc_indicators = qc_indicators
        self.data_type = data_type
        self.logger = logger
        self.time_freq = time_freq

        # 将列表数据转换为DataFrame
        if isinstance(data, list):
            self.raw_data = pd.DataFrame(data)
            if len(data) > 0:
                self.data_start_time = data[0]["record_time"]
                self.data_end_time = data[-1]["record_time"]
        else:
            self.raw_data = data
            if not data.empty:
                self.data_start_time = data["record_time"].min()
                self.data_end_time = data["record_time"].max()

    def data_qc(self):
        """
        执行数据质量控制

        Returns:
            处理后的数据DataFrame
        """
        self.logger.info("数据预处理")
        self._preprocess_data()

        if self.data_type == "flux":
            self.logger.info("flux数据质量控制")
            self._process_flux_data()
        elif self.data_type == "aqi":
            self.logger.info("阈值限制")
            self._threshold_limit()
            self.logger.info("aqi数据质量控制")
            self._process_aqi_data()
        elif self.data_type == "nai":
            self.logger.info("阈值限制")
            self._threshold_limit()
            self.logger.info("nai数据质量控制")
            self._process_nai_data()
        elif self.data_type == "sapflow":
            self.logger.info("阈值限制")
            self._threshold_limit()
            self.logger.info("sapflow数据质量控制")
            self._process_sapflow_data()
        else:
            self.logger.info(f"{self.data_type}数据质量控制")
            # 其他数据类型的处理逻辑...
            # 原始数据里需要包括下面的这些列
            if self.ftp in ["cuihu", "yeyahu", "yuankeyuan"]:
                flux_indicators = ["record_time", "vpd", "rh", "ppfd_1_1_1"]
            elif self.ftp == "badaling":
                flux_indicators = [
                    "record_time",
                    "short_up_avg",
                    "rh_10m_avg",
                    "ta_1_2_1",
                    "ppfd_1_1_1",
                ]
            else:
                flux_indicators = ["record_time", "vpd", "rh", "rg_1_1_2", "ta_1_2_1"]
            self.logger.info("根据阈值进行数据过滤")
            self._threshold_limit()
            self.logger.info("插补")
            self._gap_fill()
        return self.raw_data

    def _preprocess_data(self):
        """数据预处理"""
        # 删除id列
        if "id" in self.raw_data.columns:
            self.logger.info("删除id列")
            self.raw_data = self.raw_data.drop("id", axis=1)

        # NAN值处理
        self.logger.info("NAN值处理")
        self.raw_data = self.raw_data.replace(
            ["NaN", "nan", "NAN", "N/A", "N/a", "n/a", "N/A", " ", ""], np.nan
        )

        # 转换数据类型为float
        self.logger.info("数据转换float")
        for col in self.raw_data.columns:
            if col not in NOT_CONVERT_LIST:
                self.raw_data[col] = pd.to_numeric(self.raw_data[col], errors="coerce")

        # 确保必要的列存在 (仅对flux类型数据)
        if self.data_type == "flux":
            for col in NEEDED_INDICES:
                if col not in self.raw_data.columns:
                    self.raw_data[col] = np.nan

    def _process_flux_data(self):
        """处理flux类型数据"""
        # 复制通量数据
        self.logger.info("复制通量数据")
        self._filter_by_quality()

        # 添加存储项
        self.logger.info("添加存储项")
        self._add_strg()

        # 删除不需要的指标
        self._remove_unnecessary_columns()

        # 根据阈值进行数据筛选
        self.logger.info("根据阈值筛选数据")
        self._threshold_limit()

        # 插补par光合有效辐射
        self.logger.info("插补par光合有效辐射 ppfd_1_1_1")
        self._gap_fill_par()

        # 对co2 h2o le h进行despiking
        self.logger.info("对co2 h2o le h进行despiking")
        self._despiking()

        # 异常值过滤
        self.logger.info("异常值过滤")
        self._del_abnormal_value()

        # 插补
        self.logger.info("插补")
        self._ustar_fill_partition()

    def _filter_by_quality(self):
        """复制通量数据（已移除QC标记筛选功能）"""
        if self.ftp in CAMPBELL_SITES:
            self.raw_data = handle_campbell_special_case(self.raw_data)
        else:
            self.raw_data = copy_flux_columns_without_qc_filter(self.raw_data)

    def _add_strg(self):
        """进行存储项校正"""
        if self.is_strg == "1":
            self.raw_data = do_add_strg(self.raw_data)
        else:
            self.raw_data = not_add_strg(self.raw_data)

    def _remove_unnecessary_columns(self):
        """删除不需要的列"""
        columns_to_remove = ["short_up_avg", "rh_12m_avg", "rh_10m_avg", "ta_12m_avg"]

        for col in columns_to_remove:
            if col in self.raw_data.columns:
                self.raw_data = self.raw_data.drop(col, axis=1)

    def _threshold_limit(self):
        """阈值限制"""
        self.raw_data = threshold_limit(
            self.raw_data, self.qc_indicators, self.data_type
        )

    def _gap_fill_par(self):
        """插补光合有效辐射"""
        self.raw_data = gap_fill_par(
            self.filename, self.longitude, self.latitude, self.timezone, self.raw_data
        )

    def _despiking(self):
        """去尖峰处理"""
        self.raw_data = despiking_data(self.raw_data, self.despiking_z)

    def _del_abnormal_value(self):
        """删除异常值"""
        self.raw_data = del_abnormal_data(
            self.raw_data, nee_name="co2_despiking", par_name="Par_f"
        )

    def _ustar_fill_partition(self):
        """
        对co2 flux进行u*计算、插补和分区
        对其它指标只进行插补
        """
        self.raw_data = ustar_data(
            self.filename,
            self.longitude,
            self.latitude,
            self.timezone,
            self.raw_data,
            self.qc_indicators,
        )

    def _gap_fill(self):
        """插补处理，对非flux数据保留原始列并创建_filled列"""
        if self.data_type == "flux":
            # flux数据使用原有的R脚本插补
            self.raw_data = gapfill(self.filename, self.longitude,
                                    self.latitude, self.timezone, self.raw_data,
                                    self.qc_indicators, self.data_type)
        else:
            # 其他数据类型使用ARIMA插补，保留原始列
            self.logger.info(f"对{self.data_type}数据进行插补，保留原始列并创建_filled列")
            self.raw_data = fill_missing_values_multicolumn(self.raw_data, time_col='record_time', 
                                                          time_freq=self.time_freq, keep_original=True)
    
    def _process_aqi_data(self):
        """处理aqi数据"""
        self.logger.info("对aqi数据进行插补，保留原始列并创建_filled列")
        self.raw_data = fill_environmental_data(self.raw_data, time_col='record_time', 
                                              time_freq=self.time_freq, keep_original=True)

    def _process_nai_data(self):
        """处理nai数据"""
        self.logger.info("对nai数据进行插补，保留原始列并创建_filled列")
        self.raw_data = fill_missing_values_multicolumn(self.raw_data, time_col='record_time', 
                                                      value_cols=['nai'], time_freq=self.time_freq, 
                                                      keep_original=True)

    def _process_sapflow_data(self):
        """处理sapflow数据"""
        self.logger.info("对sapflow数据进行插补，保留原始列并创建_filled列")
        self.raw_data = fill_missing_values_multicolumn(self.raw_data, time_col='record_time', 
                                                      time_freq=self.time_freq, keep_original=True)