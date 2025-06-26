from fastapi import APIRouter, Header, HTTPException, status
from typing import Annotated
from data_server.logic.models import Recipe
from data_server.logic.config import TEMPLATE_DIR, build_templates
import pathlib
import os
import uuid

router = APIRouter()


@router.get("", response_model_exclude_none=True)
async def templates(
    user_id: Annotated[str | None, Header(alias="user_id")] = None, 
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None
) -> list[Recipe]:
    try:
        return build_templates(user_id, isadmin)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("")
async def create_template(
    template: Recipe, 
    user_id: Annotated[str | None, Header(alias="user_id")] = None
):
    try:
        """
        1. Create template from scratch, no template_id
        2. Create based on buildin template, no template_id
        3. Update user created template, has template_id
        """
        template_uuid = ''
        if not template.template_id:
            template_uuid = user_id + "_" + str(uuid.uuid4())
            template.template_id = template_uuid
        else:
            template_uuid = template.template_id

        # make sure the "buildin" is false
        template.buildin = False
        base_dir = pathlib.Path().resolve()
        template_path = os.path.join(
            base_dir, TEMPLATE_DIR, template_uuid + '.yaml')
        with open(template_path, "w") as file:
            file.write(template.yaml())
        return {"msg": "successful create"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/{template_id}")
async def remove_template(
    template_id: str, 
    user_id: Annotated[str | None, Header(alias="user_id")] = None, 
    isadmin: Annotated[bool | None, Header(alias="isadmin")] = None
):
    try:
        if not isadmin and template_id.split("_")[0] != user_id:
            raise HTTPException(status_code=403, detail="You cannot delete template not belong to you.")

        base_dir = pathlib.Path().resolve()
        template_path = os.path.join(base_dir, TEMPLATE_DIR, template_id + '.yaml')

        if os.path.exists(template_path):
            os.remove(template_path)
        return {"detail": "Successfully deleted."}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )