"""Task list scope, access, and delete permissions.

- Personal tasks: owner_id == current logged-in user.
- Organization tasks: namespace_type=organization and namespace_uuid in user's organizations.
- Admin: all tasks by default (is_active only); optional namespace_uuid to narrow scope.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import and_, or_
from sqlalchemy.orm import Query, Session

from data_server.utils.csghub_namespace import (
    NAMESPACE_TYPE_ORGANIZATION,
    NAMESPACE_TYPE_PERSONAL,
)
from data_server.utils.csghub_user_namespaces import fetch_organization_admin_uuids, fetch_organization_namespace_uuids


def normalize_user_id(user_id) -> int | None:
    """Matches User-Id header at task creation: use for owner_id filter only if parseable as int."""
    if user_id is None or user_id == "":
        return None
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        return None
    return uid


def normalize_isadmin(isadmin) -> bool:
    if isadmin is None:
        return False
    if isinstance(isadmin, bool):
        return isadmin
    return str(isadmin).strip().lower() in ("1", "true", "yes", "on")


def normalize_namespace_uuid(namespace_uuid: str | None) -> str | None:
    if namespace_uuid is None:
        return None
    value = str(namespace_uuid).strip()
    return value or None


def _dedupe_namespace_uuids(uuids: list[str] | None) -> list[str]:
    if not uuids:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in uuids:
        normalized = normalize_namespace_uuid(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def resolve_organization_namespace_uuids_for_list(
    *,
    user_name: str | None = None,
    authorization: str | None = None,
    user_token: str | None = None,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
) -> list[str] | None:
    """
    Non-admin: resolve all organization namespace_uuid for current user.
    Admin: return None (no organization filter).
    """
    if isadmin:
        return None
    if organization_namespace_uuids is not None:
        return _dedupe_namespace_uuids(organization_namespace_uuids)
    return fetch_organization_namespace_uuids(
        user_name,
        authorization=authorization,
        user_token=user_token,
    )


def resolve_organization_admin_uuids_for_delete(
    *,
    user_name: str | None = None,
    authorization: str | None = None,
    user_token: str | None = None,
    isadmin: bool = False,
) -> list[str]:
    """
    Return organization namespace UUIDs where user has admin role.
    Used for delete permission check: org admin can delete tasks in their org.
    System admin does not need this check (returns empty list).
    """
    if isadmin:
        return []
    return fetch_organization_admin_uuids(
        user_name,
        authorization=authorization,
        user_token=user_token,
    )


def _model_has_namespace_fields(model) -> bool:
    return hasattr(model, "namespace_uuid") and hasattr(model, "namespace_type")


def _organization_namespaces_clause(model, namespace_uuids: list[str]):
    """Organization task condition; self_group ensures explicit SQL parens with owner_id OR."""
    return and_(
        model.namespace_type == NAMESPACE_TYPE_ORGANIZATION,
        model.namespace_uuid.in_(namespace_uuids),
    ).self_group()


def _organization_namespace_clause(model, namespace_uuid: str):
    return and_(
        model.namespace_type == NAMESPACE_TYPE_ORGANIZATION,
        model.namespace_uuid == namespace_uuid,
    ).self_group()


def _task_list_sql_logging_enabled() -> bool:
    return os.getenv("DATAFLOW_LOG_TASK_LIST_SQL", "true").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def log_task_list_sql(
    query: Query,
    *,
    label: str,
    session: Session | None = None,
    user_id=None,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    **extra: Any,
) -> None:
    """Log final task list SQL (with filter context). Set DATAFLOW_LOG_TASK_LIST_SQL=false to disable."""
    if not _task_list_sql_logging_enabled():
        return
    try:
        bind = session.get_bind() if session is not None else None
        dialect = bind.dialect if bind is not None else None
        stmt = query.statement
        if dialect is not None:
            sql_text = str(
                stmt.compile(dialect=dialect, compile_kwargs={"literal_binds": True})
            )
        else:
            sql_text = str(stmt.compile(compile_kwargs={"literal_binds": True}))
    except Exception as exc:
        try:
            sql_text = str(query.statement)
        except Exception:
            sql_text = repr(query)
        sql_text = f"{sql_text}\n-- compile with literal_binds failed: {exc}"

    extra_parts = ", ".join(f"{k}={v!r}" for k, v in extra.items()) if extra else ""
    logger.info(
        "[TaskListSQL] {} | user_id={} | isadmin={} | org_uuids={} | filter_ns={}{}\n{}",
        label,
        user_id,
        isadmin,
        organization_namespace_uuids,
        namespace_uuid,
        f" | {extra_parts}" if extra_parts else "",
        sql_text,
    )


def apply_task_list_scope(
    query: Query,
    model,
    *,
    user_id,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
) -> Query:
    """
    List scope:
    - Admin: all; optional namespace_uuid filters that org + personal tasks.
    - Regular user: owner_id=self OR (namespace_type=organization and uuid in org list).
    """
    query = apply_active_filter(query, model)
    ns_uuid = normalize_namespace_uuid(namespace_uuid)
    isadmin = normalize_isadmin(isadmin)

    if isadmin:
        if ns_uuid and _model_has_namespace_fields(model):
            return query.filter(
                or_(
                    _organization_namespace_clause(model, ns_uuid),
                    model.namespace_type == NAMESPACE_TYPE_PERSONAL,
                    model.namespace_type.is_(None),
                    model.namespace_type == "",
                )
            )
        return query

    uid = normalize_user_id(user_id)
    org_uuids = _dedupe_namespace_uuids(organization_namespace_uuids)

    personal_clause = None
    if uid is not None and hasattr(model, "owner_id"):
        # Matches owner_id=user_id at creation (User-Id header)
        personal_clause = model.owner_id == uid

    org_clause = None
    if org_uuids and _model_has_namespace_fields(model):
        org_clause = _organization_namespaces_clause(model, org_uuids)

    if personal_clause is not None and org_clause is not None:
        # owner_id = ? OR (namespace_type = organization AND namespace_uuid IN (...))
        return query.filter(or_(personal_clause, org_clause))
    if personal_clause is not None:
        return query.filter(personal_clause)
    if org_clause is not None:
        return query.filter(org_clause)

    logger.warning(
        "Task list scope has no filter | model={} | user_id={!r} | parsed_uid={} | org_uuids={}",
        getattr(model, "__name__", model),
        user_id,
        uid,
        org_uuids,
    )
    return query


def user_can_access_task(
    record: Any,
    user_id,
    isadmin: bool = False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
) -> bool:
    if record is None:
        return False
    if getattr(record, "is_active", True) is False:
        return False
    if normalize_isadmin(isadmin):
        return True

    uid = normalize_user_id(user_id)
    owner = getattr(record, "owner_id", None)
    if uid is not None and owner is not None and str(owner) == str(uid):
        return True

    if getattr(record, "namespace_type", None) != NAMESPACE_TYPE_ORGANIZATION:
        return False

    record_ns = normalize_namespace_uuid(getattr(record, "namespace_uuid", None))
    if not record_ns:
        return False

    allowed = set(_dedupe_namespace_uuids(organization_namespace_uuids))
    ctx_ns = normalize_namespace_uuid(namespace_uuid)
    if ctx_ns:
        allowed.add(ctx_ns)
    return record_ns in allowed


def apply_active_filter(query: Query, model) -> Query:
    if hasattr(model, "is_active"):
        return query.filter(model.is_active.is_(True))
    return query


def can_delete_task(
    *,
    owner_id,
    user_id,
    isadmin: bool = False,
    org_admin_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    namespace_type: str | None = None,
) -> bool:
    """Check if user can delete a task: system admin, task creator, or org admin."""
    if isadmin:
        logger.info(
            "can_delete_task | owner_id={} | user_id={} | isadmin=True | "
            "is_creator=N/A | is_org_admin=N/A | can_delete=True",
            owner_id,
            user_id,
        )
        return True
    uid = normalize_user_id(user_id)
    is_creator = uid is not None and owner_id is not None and str(owner_id) == str(uid)
    if is_creator:
        logger.info(
            "can_delete_task | owner_id={} | user_id={} (uid={}) | isadmin=False | "
            "is_creator=True | is_org_admin=N/A | can_delete=True",
            owner_id,
            user_id,
            uid,
        )
        return True
    ns = normalize_namespace_uuid(namespace_uuid)
    org_admin_set = set(org_admin_uuids or [])
    is_org_admin = bool(org_admin_uuids and namespace_type == NAMESPACE_TYPE_ORGANIZATION and ns and ns in org_admin_set)
    result = is_org_admin
    logger.info(
        "can_delete_task | owner_id={} | user_id={} (uid={}) | isadmin=False | "
        "is_creator=False | is_org_admin={} | "
        "namespace_uuid={} | namespace_type={} | org_admin_uuids={} | "
        "can_delete={}",
        owner_id,
        user_id,
        uid,
        is_org_admin,
        namespace_uuid,
        namespace_type,
        org_admin_uuids,
        result,
    )
    return result


def attach_can_delete(
    payload: dict,
    *,
    owner_id,
    user_id,
    isadmin: bool = False,
    org_admin_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    namespace_type: str | None = None,
) -> dict:
    payload["can_delete"] = can_delete_task(
        owner_id=owner_id,
        user_id=user_id,
        isadmin=isadmin,
        org_admin_uuids=org_admin_uuids,
        namespace_uuid=namespace_uuid,
        namespace_type=namespace_type,
    )
    return payload


def soft_delete_record(session: Session, record: Any) -> None:
    if hasattr(record, "is_active"):
        record.is_active = False
    if hasattr(record, "deleted_at"):
        record.deleted_at = datetime.now()
    session.commit()
