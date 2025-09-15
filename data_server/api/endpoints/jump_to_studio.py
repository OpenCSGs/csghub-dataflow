import os
import httpx
from fastapi import APIRouter, Header
from loguru import logger
from typing import Optional

from data_server.schemas.responses import response_success

router = APIRouter()


BASE_STUDIO_URL = os.getenv("STUDIO_JUMP_URL", "http://192.168.2.6:8080")


@router.post("/jump-to-studio", tags=["studio"])
async def jump_to_studio(
    authorization: Optional[str] = Header(None, alias="authorization"),
    user_token: Optional[str] = Header(None, alias="user_token"),
    user_name: Optional[str] = Header(None, alias="user_name"),
):
    """Jump to studio with credentials from headers."""

    if user_name:
        target_url = f"{BASE_STUDIO_URL}/user/login_verfy/?email={user_name}@qq.com"
    else:
        target_url = f"{BASE_STUDIO_URL}/user/login_verfy/?email=z275748353@qq.com"

    # Prepare the JSON payload with credentials from headers
    payload = {
        "authorization": authorization,
        "user_token": user_token,
        "user_name": user_name,
    }
    # Filter out credentials that were not provided
    payload = {k: v for k, v in payload.items() if v is not None}

    # Prepare forward headers, keeping it minimal
    fwd_headers = {
        'Content-Type': 'application/json'
    }

    print(f"final_url:{target_url}")
    print(f"payload:{payload}")
    try:
        async with httpx.AsyncClient() as client:
            # Send the payload in the JSON body of the POST request
            response = await client.post(target_url, data=payload)
            response.raise_for_status()  # Raise an exception for 4xx/5xx responses
            target_url = f"{BASE_STUDIO_URL}/user/login_reques/?email={user_name}@qq.com"
            return response_success(data=target_url)
    except httpx.RequestError as exc:
        logger.error(f"Request to studio failed: {exc}")
        return response_success(data=None, msg=f"Request to studio failed: {exc}")
    except httpx.HTTPStatusError as exc:
        logger.error(f"Studio returned an error: {exc.response.status_code} {exc.response.text}")
        return response_success(
            data=exc.response.text,
            msg=f"Studio returned an error: {exc.response.status_code}",
        )
