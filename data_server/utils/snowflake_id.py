import time
import random

class SnowflakeID:
    """
    雪花ID生成器，用于生成分布式唯一ID
    类似于MyBatisPlus的assign_id策略
    """
    
    def __init__(self, worker_id=None, datacenter_id=None):
        # 开始时间戳 (2023-01-01 00:00:00 UTC)
        self.twepoch = 1672531200000
        
        # 各部分占位长度
        self.worker_id_bits = 5  # 机器ID所占位数
        self.datacenter_id_bits = 5  # 数据中心ID所占位数
        self.sequence_bits = 12  # 序列所占位数
        
        # 最大值
        self.max_worker_id = -1 ^ (-1 << self.worker_id_bits)  # 最大机器ID
        self.max_datacenter_id = -1 ^ (-1 << self.datacenter_id_bits)  # 最大数据中心ID
        
        # 偏移量
        self.worker_id_shift = self.sequence_bits  # 机器ID偏移量
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits  # 数据中心ID偏移量
        self.timestamp_shift = self.sequence_bits + self.worker_id_bits + self.datacenter_id_bits  # 时间戳偏移量
        
        # 掩码
        self.sequence_mask = -1 ^ (-1 << self.sequence_bits)  # 序列掩码
        
        # 实例变量
        self.worker_id = worker_id if worker_id is not None else random.randint(0, self.max_worker_id)
        self.datacenter_id = datacenter_id if datacenter_id is not None else random.randint(0, self.max_datacenter_id)
        self.sequence = 0
        self.last_timestamp = -1
        
        # 参数校验
        if self.worker_id > self.max_worker_id or self.worker_id < 0:
            raise ValueError(f"worker_id不能大于{self.max_worker_id}或小于0")
        if self.datacenter_id > self.max_datacenter_id or self.datacenter_id < 0:
            raise ValueError(f"datacenter_id不能大于{self.max_datacenter_id}或小于0")
    
    def next_id(self):
        """
        生成下一个ID
        """
        timestamp = self.get_time()
        
        # 如果当前时间小于上一次ID生成时间，说明系统时钟回退，抛出异常
        if timestamp < self.last_timestamp:
            raise RuntimeError(f"时钟回拨，拒绝生成ID，上次生成时间: {self.last_timestamp}, 当前时间: {timestamp}")
        
        # 如果是同一时间生成的，则进行序列递增
        if timestamp == self.last_timestamp:
            self.sequence = (self.sequence + 1) & self.sequence_mask
            # 同一毫秒的序列数已经达到最大
            if self.sequence == 0:
                # 阻塞到下一个毫秒，获得新的时间戳
                timestamp = self.wait_next_millis(self.last_timestamp)
        else:
            # 时间戳改变，序列重置
            self.sequence = 0
        
        # 更新上次生成ID的时间戳
        self.last_timestamp = timestamp
        
        # 组合成64位ID
        return ((timestamp - self.twepoch) << self.timestamp_shift) | \
               (self.datacenter_id << self.datacenter_id_shift) | \
               (self.worker_id << self.worker_id_shift) | \
               self.sequence
    
    def get_time(self):
        """
        获取当前毫秒时间戳
        """
        return int(time.time() * 1000)
    
    def wait_next_millis(self, last_timestamp):
        """
        阻塞到下一个毫秒，直到获得新的时间戳
        """
        timestamp = self.get_time()
        while timestamp <= last_timestamp:
            timestamp = self.get_time()
        return timestamp

class CompactIDGenerator:
    """
    紧凑型10位ID生成器
    生成范围：1000000000 - 9999999999
    """

    def __init__(self):
        self.sequence = 0
        self.last_second = 0
        self.machine_id = random.randint(0, 99)  # 机器ID：0-99

    def next_id(self):
        """
        生成10位ID
        组成：时间戳6位 + 机器ID2位 + 序列2位
        """
        current_second = int(time.time())

        # 如果是同一秒，序列号递增
        if current_second == self.last_second:
            self.sequence = (self.sequence + 1) % 100
            # 如果序列号用完，等待下一秒
            if self.sequence == 0:
                while current_second <= self.last_second:
                    current_second = int(time.time())
        else:
            self.sequence = 0

        self.last_second = current_second

        # 取时间戳的后6位
        time_part = current_second % 1000000

        # 组合ID：时间6位 + 机器2位 + 序列2位
        id_value = time_part * 10000 + self.machine_id * 100 + self.sequence

        # 确保是10位数
        if id_value < 1000000000:
            id_value += 1000000000

        return id_value % 10000000000

# 创建全局ID生成器实例
compact_id_generator = CompactIDGenerator()

# 原有的雪花ID生成器
snowflake = SnowflakeID()

def generate_id():
    """
    生成一个10位数字的ID
    """
    return compact_id_generator.next_id()