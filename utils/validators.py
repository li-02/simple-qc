"""
参数验证模块
"""
import os
from config.constants import VALID_DATA_TYPES


def validate_args(args):
    """
    验证输入参数是否符合要求
    
    Args:
        args: 命令行参数对象
        
    Returns:
        valid: 是否验证通过
        error_msgs: 验证失败的错误信息列表
    """
    valid = True
    error_msgs = []
    
    # 检查文件路径
    if not os.path.exists(args.file_path):
        valid = False
        error_msgs.append(f"错误：文件 {args.file_path} 不存在")
    
    # 检查数据类型
    if args.data_type not in VALID_DATA_TYPES:
        valid = False
        error_msgs.append(f"错误：数据类型 {args.data_type} 不合法，有效选项为: {', '.join(VALID_DATA_TYPES)}")
    
    # 检查经纬度
    if args.longitude < -180 or args.longitude > 180:
        valid = False
        error_msgs.append(f"错误：经度 {args.longitude} 超出有效范围 [-180, 180]")
        
    if args.latitude < -90 or args.latitude > 90:
        valid = False
        error_msgs.append(f"错误：纬度 {args.latitude} 超出有效范围 [-90, 90]")
    
    return valid, error_msgs