from datetime import datetime
import pytz


def parse_shanghai_datetime(datetime):

    shanghai_tz = pytz.timezone('Asia/Shanghai')

    shanghai_datetime = shanghai_tz.localize(datetime)
    return shanghai_datetime


def parse_shanghai_datetime_to_utc(datetime_str):


    shanghai_datetime = parse_shanghai_datetime(datetime_str)

    utc_tz = pytz.UTC
    utc_datetime = shanghai_datetime.astimezone(utc_tz)
    return utc_datetime
