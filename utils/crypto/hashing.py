"""
哈希算法工具模块

提供各种哈希算法的实现，包括安全哈希、快速哈希和密码哈希功能。
支持字符串、文件和流数据的哈希计算。

特性：
- 多种哈希算法（MD5, SHA系列, BLAKE2等）
- 文件哈希计算
- 流式哈希计算
- 密码哈希（加盐、迭代）
- 哈希验证功能
"""

import hashlib
import hmac
import os
import sys
from typing import Dict, Callable, Any, Union, BinaryIO, Optional, Literal
from pathlib import Path

HashAlgorithm = Literal[
    "md5", "sha1", "sha224", "sha256", "sha384", "sha512",
    "sha3_224", "sha3_256", "sha3_384", "sha3_512",
    "blake2b", "blake2s"
]
# 类型别名，提高可读性
HasherFactory = Callable[[], hashlib._Hash]


class HashTool:

    # 支持的哈希算法
    SUPPORTED_ALGORITHMS: Dict[HashAlgorithm, HasherFactory] = {
        "md5": hashlib.md5,
        "sha1": hashlib.sha1,
        "sha224": hashlib.sha224,
        "sha256": hashlib.sha256,
        "sha384": hashlib.sha384,
        "sha512": hashlib.sha512,
        "sha3_224": hashlib.sha3_224,
        "sha3_256": hashlib.sha3_256,
        "sha3_384": hashlib.sha3_384,
        "sha3_512": hashlib.sha3_512,
        "blake2b": hashlib.blake2b,
        "blake2s": hashlib.blake2s,
    }

    @classmethod
    def getAvailableAlgorithms(cls) -> list:
        """获取可用的哈希算法列表"""
        return list(cls.SUPPORTED_ALGORITHMS.keys())

    def hashString(cls, s: str, algorithm: str = "sha256", encoding: str = "utf-8") -> str:
        """
        计算字符串的哈希值

        Args:
            data: 要哈希的字符串
            algorithm: 哈希算法，默认"sha256"
            encoding: 字符串编码，默认"utf-8"
        Returns:
            str: 十六进制哈希值
        Raises:
            ValueError: 不支持的哈希算法时抛出
        """
        if algorithm not in cls.SUPPORTED_ALGORITHMS:
            raise ValueError(
                f"不支持的哈希算法: {algorithm}。"
                f"可用算法: {", ".join(cls.getAvailableAlgorithms())}"
            )

        hash_factory = cls.SUPPORTED_ALGORITHMS[algorithm]
        hash_func = hash_factory()
        hash_func.update(s.encode(encoding))
        return hash_func.hexdigest()
