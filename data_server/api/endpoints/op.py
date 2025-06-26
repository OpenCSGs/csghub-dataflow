from fastapi import APIRouter, HTTPException, status
from data_server.logic.models import Op
from data_server.logic.constant import BUILDIN_OPS


router = APIRouter()

@router.get("")
async def ops() -> dict[str, Op]:
    try:
        return BUILDIN_OPS
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )