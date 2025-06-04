#!/usr/bin/env python
"""
REddyProc 数据质量控制和处理主程序
"""
import sys
import pandas as pd
import argparse
import os
import datetime
from core.data_qc import DataQc
from utils.fill_time import fill_time
from utils.validators import validate_args
from utils.logging import setup_logger, close_logger


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="数据质量控制工具")
    parser.add_argument(
        "--file-path",
        "-d",
        type=str,
        default="./data/2024_shisanling_flux_raw_data.csv",
        help="数据文件路径",
    )
    parser.add_argument("--data-type", "-t", type=str, default="flux", help="数据类型")
    parser.add_argument("--ftp", "-f", type=str, default="shisanling", help="站点ftp")
    parser.add_argument(
        "--longitude", "-lon", type=float, default=116.28824, help="经度"
    )
    parser.add_argument(
        "--latitude", "-lat", type=float, default=40.265635, help="纬度"
    )
    parser.add_argument("--is-strg", "-s", type=int, default=0, help="是否做存储项校正")
    parser.add_argument(
        "--despiking-z", "-z", type=float, default=4.0, help="去噪声的z值"
    )
    args = parser.parse_args()

    # 初始化日志
    logger = setup_logger(ftp=args.ftp)

    try:
        logger.info("数据质量控制工具开始运行")
        logger.info(
            f"参数信息: file-path={args.file_path}, data-type={args.data_type}, "
            f"ftp={args.ftp}, longitude={args.longitude}, latitude={args.latitude}"
        )

        # 验证参数
        logger.info("验证输入参数")
        valid, error_msgs = validate_args(args)
        if not valid:
            logger.error("参数验证失败")
            for msg in error_msgs:
                logger.error(msg)
                print(msg)
            close_logger(logger, success=False)
            sys.exit(1)
        else:
            logger.info("参数验证成功")

        # 创建任务ID
        task_id = args.ftp + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        logger.info(f"创建任务ID: {task_id}")

        # 读取数据
        logger.info("开始读取数据文件")
        if not os.path.exists(args.file_path):
            logger.error(f"文件 {args.file_path} 不存在")
            close_logger(logger, success=False)
            sys.exit(1)
        try:
            data = pd.read_csv(args.file_path)
            logger.info(
                f"数据时间范围：{data['record_time'].min()} 至 {data['record_time'].max()}"
            )
        except Exception as e:
            logger.error(f"读取数据文件失败: {str(e)}")
            close_logger(logger, success=False)
            sys.exit(1)
        # 确保数据文件时间间隔为半小时
        data = fill_time(data, time_freq="30min")

        # 读取质量控制指标
        logger.info(f"执行{args.data_type}类型数据的质量控制")
        try:
            qc_indicators = pd.read_csv("qc_indicators.csv")
            qc_indicators = qc_indicators.to_dict("records")
        except Exception as e:
            logger.error(f"读取质量控制指标文件失败: {str(e)}")
            close_logger(logger, success=False)
            sys.exit(1)

        # 数据质量控制
        dc = DataQc(
            task_id=task_id,
            data=data,
            data_type=args.data_type,
            ftp=args.ftp,
            qc_indicators=qc_indicators,
            qc_flag_list=["0", "1", "2"],
            is_strg=args.is_strg,
            despiking_z=args.despiking_z,
            longitude=args.longitude,
            latitude=args.latitude,
            timezone=8,
            filename=args.file_path,
            logger=logger,
        )

        # 执行质量控制
        processed_data = dc.data_qc()

        # 保存处理后的数据
        output_path = f"{args.ftp}_{args.data_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        processed_data.to_csv(output_path, index=False)
        logger.info(f"数据处理完成，结果保存至: {output_path}")

        close_logger(logger, success=True)
        return processed_data

    except Exception as e:
        logger.error(f"程序执行出错: {str(e)}")
        close_logger(logger, success=False)
        sys.exit(1)


if __name__ == "__main__":
    main()
# python .\main.py -d D:\Code\QC\data\train\miyun_pm2_5_manual_missing.csv -t aqi
