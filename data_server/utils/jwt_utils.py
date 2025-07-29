"""
JWT Token 解析工具模块
用于解析前端传来的JWT token并提取所有信息
"""
from typing import Dict
import base64
import json
from datetime import datetime


class JWTDecodeError(Exception):
    """JWT解码异常"""
    pass


def parse_jwt_token(authorization: str) -> Dict:
    """
    解析JWT token并返回所有信息

    Args:
        authorization: Authorization header值，格式: "Bearer <token>"

    Returns:
        Dict: 包含token所有信息的字典：
        {
        "header": {
        "alg": "HS256",
        "typ": "JWT"
        },
        "payload": {
        "uuid": "oNU8p6hC-gtqdfcy35UL-mmuv7QI",
        "current_user": "LBWhite55",
        "iss": "OpenCSG",
        "exp": 1753163093
        },
        "signature": "gYwlD3lBUTkwM3Rv-irVL479Qga14Frv6zf_nIU1Trg",
        "exp_datetime": datetime(2025, 7, 21, 16, 31, 33),
        "is_expired": False
}

    Raises:
        JWTDecodeError: 解析失败时抛出
    """
    try:
        # 检查Authorization header格式
        if not authorization:
            raise JWTDecodeError("Authorization header is missing")

        if not authorization.startswith("Bearer "):
            raise JWTDecodeError("Authorization header must start with 'Bearer '")

        # 提取token
        token = authorization[7:].strip()
        if not token:
            raise JWTDecodeError("Token is empty after 'Bearer ' prefix")

        # JWT token由三部分组成：header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            raise JWTDecodeError("Invalid JWT format: token must have 3 parts separated by dots")

        # 解码header部分
        header_part = parts[0]
        header_padding = 4 - len(header_part) % 4
        if header_padding != 4:
            header_part += '=' * header_padding
        header_bytes = base64.urlsafe_b64decode(header_part)
        header = json.loads(header_bytes.decode('utf-8'))

        # 解码payload部分
        payload_part = parts[1]
        payload_padding = 4 - len(payload_part) % 4
        if payload_padding != 4:
            payload_part += '=' * payload_padding
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_bytes.decode('utf-8'))

        # 获取签名部分
        signature = parts[2]

        # 处理过期时间
        exp_datetime = None
        is_expired = None
        if payload.get("exp"):
            try:
                exp_datetime = datetime.fromtimestamp(payload["exp"])
                is_expired = datetime.now() > exp_datetime
            except (ValueError, OSError):
                pass

        # 返回完整信息
        return {
            "header": header,
            "payload": payload,
            "signature": signature,
            "exp_datetime": exp_datetime,
            "is_expired": is_expired
        }

    except json.JSONDecodeError as e:
        raise JWTDecodeError(f"Failed to parse JWT as JSON: {str(e)}")
    except Exception as e:
        if isinstance(e, JWTDecodeError):
            raise
        raise JWTDecodeError(f"Failed to decode JWT token: {str(e)}")

if __name__ == "__main__":
    # 测试
    token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1dWlkIjoib05VOHA2aEMtZ3RxZGZjeTM1VUwtbW11djdRSSIsImN1cnJlbnRfdXNlciI6IkxCV2hpdGU1NSIsImlzcyI6Ik9wZW5DU0ciLCJleHAiOjE3NTM1ODQ0MzN9.9nTj0_YXfXD_5W7MBJvkzpNK4N5zEkodEhWZxsVfvUU"
    print(parse_jwt_token(token))