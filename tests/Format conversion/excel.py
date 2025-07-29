import os
import traceback
import logging
import pandas as pd
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('excel_conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('ExcelConverter')


def excel_to_formats(input_path, output_dir, **kwargs):
    """
    将Excel文件转换为多种格式
    :param input_path: Excel文件路径
    :param output_dir: 输出目录
    :param kwargs: 额外参数
    :return: 转换结果字典
    """
    try:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 错误日志文件
        error_log_path = output_dir / "conversion_errors.log"

        def log_error(msg):
            with open(error_log_path, "a", encoding="utf-8") as f:
                f.write(msg + "\n")
            logger.error(msg)

        logger.info(f"开始处理Excel文件: {input_path}")

        try:
            sheets_dict = pd.read_excel(input_path, sheet_name=None)
            logger.info(f"成功读取Excel文件，共{len(sheets_dict)}个工作表")
        except Exception as e:
            err_msg = f"读取Excel文件失败: {e}\n{traceback.format_exc()}"
            log_error(err_msg)
            raise

        results = {}
        for sheet_name, df in sheets_dict.items():
            sanitized_sheet_name = sheet_name.replace(" ", "_").replace("/", "_")
            file_prefix = f"output_data_from_excel_{sanitized_sheet_name}"

            # 保存JSON
            try:
                json_path = output_dir / f"{file_prefix}.json"
                df.to_json(json_path, orient='records', force_ascii=False, indent=4)
                logger.info(f"已保存为JSON: {json_path}")
                results[f"json_{sanitized_sheet_name}"] = str(json_path)
            except Exception as e:
                err_msg = f"保存{file_prefix}.json失败: {e}\n{traceback.format_exc()}"
                log_error(err_msg)
                results[f"json_{sanitized_sheet_name}"] = f"失败: {str(e)}"

            # 保存CSV
            try:
                csv_path = output_dir / f"{file_prefix}.csv"
                df.to_csv(csv_path, index=False)
                logger.info(f"已保存为CSV: {csv_path}")
                results[f"csv_{sanitized_sheet_name}"] = str(csv_path)
            except Exception as e:
                err_msg = f"保存{file_prefix}.csv失败: {e}\n{traceback.format_exc()}"
                log_error(err_msg)
                results[f"csv_{sanitized_sheet_name}"] = f"失败: {str(e)}"

            # 保存Parquet
            try:
                parquet_path = output_dir / f"{file_prefix}.parquet"
                df.to_parquet(parquet_path, engine='pyarrow', index=False)
                logger.info(f"已保存为Parquet: {parquet_path}")
                results[f"parquet_{sanitized_sheet_name}"] = str(parquet_path)
            except Exception as e:
                err_msg = f"保存{file_prefix}.parquet失败: {e}\n{traceback.format_exc()}"
                log_error(err_msg)
                results[f"parquet_{sanitized_sheet_name}"] = f"失败: {str(e)}"

        logger.info(f"所有工作表转换完成: {input_path}")
        return results

    except Exception as e:
        logger.error(f"Excel转换失败: {str(e)}", exc_info=True)
        raise
