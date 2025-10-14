"""
ID生成工具模块

提供雪花ID和UUID7生成功能，用于分布式系统中的唯一ID生成。

特性：
- 雪花ID生成器（Snowflake ID）
- UUID7生成（基于时间的UUID）
- 线程安全
- 高性能
"""

import time
import threading
import random
import uuid as uuid_lib
from typing import Optional
from datetime import datetime, timezone


class SnowflakeGenerator:
    """雪花ID生成器

    雪花ID结构（64位）：
    0 - 0000000000 0000000000 0000000000 0000000000 0 - 00000 - 00000 - 000000000000
    1位符号位（始终为0） + 41位时间戳 + 5位数据中心ID + 5位机器ID + 12位序列号

    特性：
    - 支持最多32个数据中心
    - 每个数据中心支持最多32台机器
    - 每台机器每毫秒可生成4096个ID
    - 时间戳部分可使用约69年
    """

    # 各部分的位数
    TIMESTAMP_BITS = 41
    DATACENTER_BITS = 5
    WORKER_BITS = 5
    SEQUENCE_BITS = 12

    # 最大值
    MAX_DATACENTER_ID = (1 << DATACENTER_BITS) - 1
    MAX_WORKER_ID = (1 << WORKER_BITS) - 1
    MAX_SEQUENCE = (1 << SEQUENCE_BITS) - 1

    # 偏移量
    TIMESTAMP_SHIFT = SEQUENCE_BITS + WORKER_BITS + DATACENTER_BITS
    DATACENTER_SHIFT = SEQUENCE_BITS + WORKER_BITS
    WORKER_SHIFT = SEQUENCE_BITS

    # 起始时间戳（2024-01-01 00:00:00 UTC）
    EPOCH = 1704067200000

    def __init__(self, datacenter_id: int = 0, worker_id: int = 0):
        """
        初始化雪花ID生成器

        Args:
            datacenter_id: 数据中心ID (0-31)
            worker_id: 机器ID (0-31)

        Raises:
            ValueError: 当datacenter_id或worker_id超出范围时抛出
        """
        if datacenter_id > self.MAX_DATACENTER_ID or datacenter_id < 0:
            raise ValueError(f"数据中心ID必须在0-{self.MAX_DATACENTER_ID}之间")

        if worker_id > self.MAX_WORKER_ID or worker_id < 0:
            raise ValueError(f"机器ID必须在0-{self.MAX_WORKER_ID}之间")

        self.datacenter_id = datacenter_id
        self.worker_id = worker_id
        self.sequence = 0
        self.last_timestamp = -1
        self._lock = threading.Lock()

    def _currentTimestamp(self) -> int:
        """获取当前时间戳（毫秒）"""
        return int(time.time() * 1000)

    def _wait_next_millis(self, last_timestamp: int) -> int:
        """等待下一毫秒"""
        timestamp = self._currentTimestamp()
        while timestamp <= last_timestamp:
            timestamp = self._currentTimestamp()
        return timestamp

    def generate(self) -> int:
        """生成雪花ID

        Returns:
            int: 64位的雪花ID

        Raises:
            Exception: 当系统时钟回拨时抛出
        """
        with self._lock:
            timestamp = self._currentTimestamp()

            # 检查时钟回拨
            if timestamp < self.last_timestamp:
                raise Exception("系统时钟回拨，拒绝生成ID")

            # 同一毫秒内生成多个ID
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.MAX_SEQUENCE
                if self.sequence == 0:
                    # 序列号用完，等待下一毫秒
                    timestamp = self._wait_next_millis(self.last_timestamp)
            else:
                self.sequence = 0

            self.last_timestamp = timestamp

            # 生成ID
            return ((timestamp - self.EPOCH) << self.TIMESTAMP_SHIFT) | \
                   (self.datacenter_id << self.DATACENTER_SHIFT) | \
                   (self.worker_id << self.WORKER_SHIFT) | \
                self.sequence

    def parse(self, snowflake_id: int) -> dict:
        """解析雪花ID

        Args:
            snowflake_id: 雪花ID

        Returns:
            dict: 包含各组成部分的字典
        """
        timestamp = (snowflake_id >> self.TIMESTAMP_SHIFT) + self.EPOCH
        datacenter_id = (snowflake_id >> self.DATACENTER_SHIFT) & self.MAX_DATACENTER_ID
        worker_id = (snowflake_id >> self.WORKER_SHIFT) & self.MAX_WORKER_ID
        sequence = snowflake_id & self.MAX_SEQUENCE

        return {
            'timestamp': timestamp,
            'datetime': datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc),
            'datacenter_id': datacenter_id,
            'worker_id': worker_id,
            'sequence': sequence
        }


class UUID7Generator:
    """UUID7生成器

    UUIDv7是基于时间的有序UUID，结构：
    - 48位：Unix时间戳（毫秒）
    - 12位：随机数A
    - 4位：版本（7）
    - 2位：变体（10）
    - 14位：随机数B
    - 48位：随机数C

    特性：
    - 基于时间排序，适合数据库索引
    - 比传统UUIDv4具有更好的局部性
    - 符合RFC 9562标准
    """

    @staticmethod
    def generate(methods: str = "uuid") -> str:
        """生成UUIDv7

        Args:
            methods: 生成UUID的方法，可选值："uuid","int", "hex"

        Returns:
            str: 指定格式的UUIDv7字符串

        Raises:
            ValueError: 当methods参数无效时抛出
        """

        # 获取当前时间戳（毫秒）
        timestamp_ms = int(time.time() * 1000)

        # 生成随机字节
        rand_bytes = random.getrandbits(74).to_bytes(10, 'big')

        # 构建UUIDv7的16字节
        uuid_bytes = bytearray(16)

        # 前6字节：时间戳（48位）
        uuid_bytes[0:6] = timestamp_ms.to_bytes(6, 'big')

        # 第6-8字节：版本4位 + 随机数A的12位
        uuid_bytes[6] = (uuid_bytes[6] & 0x0F) | 0x70  # 设置版本为7
        uuid_bytes[6] = (uuid_bytes[6] & 0xF0) | ((rand_bytes[0] & 0xF0) >> 4)
        uuid_bytes[7] = rand_bytes[1]

        # 第8字节：变体2位 + 随机数B的前6位
        uuid_bytes[8] = (rand_bytes[2] & 0x3F) | 0x80  # 设置变体为10

        # 第9-15字节：随机数B的后部分 + 随机数C
        uuid_bytes[9:16] = rand_bytes[3:10]
        if methods == "hex":
            return uuid_bytes.hex()
        elif methods == "int":
            return int.from_bytes(uuid_bytes, 'big')
        else:
            return str(uuid_lib.UUID(bytes=bytes(uuid_bytes)))

    @staticmethod
    def generateMany(count: int = 1) -> list[str]:
        """批量生成UUIDv7

        Args:
            count: 生成数量

        Returns:
            list[str]: UUIDv7列表
        """
        return [UUID7Generator.generate() for _ in range(count)]

    @staticmethod
    def get_timestamp(uuid_str: str) -> Optional[int]:
        """从UUIDv7中提取时间戳

        Args:
            uuid_str: UUIDv7字符串

        Returns:
            Optional[int]: 时间戳（毫秒），如果不是有效的UUIDv7则返回None
        """
        try:
            uuid_obj = uuid_lib.UUID(uuid_str)
            if uuid_obj.version != 7:
                return None

            # 提取前48位时间戳
            uuid_bytes = uuid_obj.bytes
            timestamp_bytes = bytes([uuid_bytes[0] & 0xFF,
                                     uuid_bytes[1] & 0xFF,
                                     uuid_bytes[2] & 0xFF,
                                     uuid_bytes[3] & 0xFF,
                                     uuid_bytes[4] & 0xFF,
                                     uuid_bytes[5] & 0xFF])
            return int.from_bytes(timestamp_bytes, 'big')
        except (ValueError, AttributeError):
            return None


# 全局默认生成器实例
_default_snowflake = SnowflakeGenerator()


def snowflakeID(datacenter_id: int = 0, worker_id: int = 0) -> int:
    """生成雪花ID（便捷函数）

    Args:
        datacenter_id: 数据中心ID
        worker_id: 机器ID

    Returns:
        int: 雪花ID
    """
    if datacenter_id == 0 and worker_id == 0:
        return _default_snowflake.generate()
    else:
        generator = SnowflakeGenerator(datacenter_id, worker_id)
        return generator.generate()


def uuid7() -> str:
    """生成UUIDv7（便捷函数）

    Returns:
        str: UUIDv7字符串
    """
    return UUID7Generator.generate()


def parseSnowflake(snowflake_id: int) -> dict:
    """解析雪花ID（便捷函数）

    Args:
        snowflake_id: 雪花ID

    Returns:
        dict: 解析结果
    """
    return _default_snowflake.parse(snowflake_id)


if __name__ == '__main__':
    # 测试代码
    print("雪花ID测试:")
    snow_id = snowflakeID()
    print(f"生成的雪花ID: {snow_id}")
    print(f"解析结果: {parseSnowflake(snow_id)}")

    print("\nUUID7测试:")
    uuid7_str = uuid7()
    print(f"生成的UUID7: {uuid7_str}")
    print(f"时间戳: {UUID7Generator.get_timestamp(uuid7_str)}")

    print("\n批量生成测试:")
    uuids = UUID7Generator.generateMany(3)
    for u in uuids:
        print(f"  {u}")
