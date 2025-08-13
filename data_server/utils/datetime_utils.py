from datetime import datetime
import pytz


def parse_shanghai_datetime(datetime):
    # 获取上海时区
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    # 将naive datetime转换为上海时区的aware datetime
    shanghai_datetime = shanghai_tz.localize(datetime)
    return shanghai_datetime


def parse_shanghai_datetime_to_utc(datetime_str):
    """
    将 yyyy-MM-dd HH:mm:ss 格式的时间字符串转换为UTC时间的datetime对象
    Args:
        datetime_str (str): 格式为 'yyyy-MM-dd HH:mm:ss' 的时间字符串
    Returns:
        datetime: UTC时区的datetime对象
    """
    # 先转换为上海时区
    shanghai_datetime = parse_shanghai_datetime(datetime_str)
    # 转换为UTC时区
    utc_tz = pytz.UTC
    utc_datetime = shanghai_datetime.astimezone(utc_tz)
    return utc_datetime
