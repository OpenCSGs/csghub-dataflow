from fastapi import APIRouter, HTTPException, status, Header
from data_server.logic.models import Tool
from data_server.logic.config import build_tools
from typing import Annotated


router = APIRouter()

@router.get("")
async def tools(
    user_id: Annotated[str | None, Header(alias="User-Id")] = None, 
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None
) -> dict[str, Tool]:
    try:
        return build_tools(user_id, isadmin)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )