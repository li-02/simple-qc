"""
常量配置文件
"""

# 站点信息
CAMPBELL_SITES = ['aosen', 'badaling']

# 数据类型
VALID_DATA_TYPES = ["flux", "aqi", "sapflow", "nai", "micro_meteorology"]

# 不需要转换为float的列
NOT_CONVERT_LIST = ['record_time']

# 无需使用的列表
NO_USE_LIST = ['co2_flux', 'h2o_flux', 'le', 'h']

# 需要的索引
NEEDED_INDICES = [
    'record_time', 'rg_1_1_2', 'ppfd_1_1_1', 'ta_1_2_1', 'tsoil', 
    'rh', 'vpd', 'u_', 'short_up_avg', 'rh_12m_avg', 
    'ta_12m_avg', 'rh_10m_avg'
]

# 格式列表
FORMAT_LIST = [
    'co2_flux_add_strg', 'h2o_flux_add_strg', 'le_add_strg', 
    'h_add_strg', 'rh', 'rg', 'vpd', 'record_time', 
    'tair', 'tsoil', 'ustar'
]

# R格式列表
R_FORMAT_LIST = [
    'NEE', 'H2O', 'LE', 'H', 'rH', 'Rg', 'VPD', 
    'DateTime', 'Tair', 'Tsoil', 'Ustar'
]

# 删除列表
DEL_LIST = [
    'NEE_orig', 'H2O_orig', 'LE_orig', 'H_orig', 
    'Tair_orig', 'Tsoil_orig', 'VPD_orig', 'Rg_orig', 
    'rH', 'Rg', 'Tair', 'VPD'
]