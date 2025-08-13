"""
本模块定义了API端点可重用的依赖项。
"""
from typing import Annotated, Dict

from fastapi import Header, HTTPException, status

from data_server.utils.jwt_utils import JWTDecodeError, parse_jwt_token


async def get_validated_token_payload(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None
) -> Dict:
    """
    一个依赖项，用于从 Authorization 头中解析和验证 JWT token。

    如果成功，它会返回解码后的 token payload。
    如果失败（如 header 缺失、token 格式错误、过期等），它会直接抛出相应的 HTTPException。

    Raises:
        HTTPException: 如果 token 无效、过期或缺失，则抛出 401 异常。

    Returns:
        Dict: 包含 token payload 所有信息的字典。
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        token_info = parse_jwt_token(authorization)
    except JWTDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_info.get("is_expired"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = token_info.get("payload")
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload
