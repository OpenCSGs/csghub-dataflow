
from typing import Annotated, Dict

from fastapi import Header, HTTPException, status

from data_server.utils.jwt_utils import JWTDecodeError, parse_jwt_token


async def get_validated_token_payload(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None
) -> Dict:

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
