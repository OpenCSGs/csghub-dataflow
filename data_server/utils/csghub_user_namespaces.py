"""Fetch organization namespace UUIDs accessible to current user from CSGHub."""
from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, parse, request

from loguru import logger

from data_server.utils.csghub_client import _get_http_timeout

# CSGHub /user/{username} namespaces.Type values (differs from stored personal/organization)
_CSGHUB_NS_TYPE_USER = frozenset({"user", "personal"})
_CSGHUB_NS_TYPE_ORGANIZATION = frozenset({"organization", "org"})


def is_csghub_organization_namespace(ns_type: str | None) -> bool:
    """Organizations only; exclude Type=user (personal space)."""
    t = str(ns_type or "").strip().lower()
    if t in _CSGHUB_NS_TYPE_USER:
        return False
    return t in _CSGHUB_NS_TYPE_ORGANIZATION


def _normalize_namespace_item(item: dict[str, Any]) -> dict[str, str] | None:
    if not isinstance(item, dict):
        return None
    ns_type = str(item.get("Type") or item.get("type") or "").strip().lower()
    uuid = str(item.get("UUID") or item.get("uuid") or "").strip()
    if not uuid:
        return None
    return {"type": ns_type, "uuid": uuid}


def _iter_namespace_dicts_from_user_root(root: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect namespace items from data.namespaces and data.orgs[].namespace."""
    items: list[dict[str, Any]] = []
    for key in ("namespaces", "Namespaces"):
        raw_list = root.get(key)
        if isinstance(raw_list, list):
            items.extend(x for x in raw_list if isinstance(x, dict))

    orgs = root.get("orgs") or root.get("Orgs") or []
    if isinstance(orgs, list):
        for org in orgs:
            if not isinstance(org, dict):
                continue
            nested = org.get("namespace") or org.get("Namespace")
            if isinstance(nested, dict):
                items.append(nested)
            else:
                org_uuid = str(org.get("uuid") or org.get("UUID") or "").strip()
                if org_uuid:
                    items.append({"Type": "organization", "UUID": org_uuid})

    return items


def is_csghub_personal_namespace(ns_type: str | None) -> bool:
    return str(ns_type or "").strip().lower() in _CSGHUB_NS_TYPE_USER


def parse_user_namespace_scopes(body: Any) -> tuple[str | None, list[str]]:
    """
    Parse (personal namespace_uuid, organization namespace_uuid list) from CSGHub user info.
    Personal Type=user, organization Type=organization; kept separate to avoid cross-query leakage.
    """
    if not isinstance(body, dict):
        return None, []
    root = body.get("data") if isinstance(body.get("data"), dict) else body
    if not isinstance(root, dict):
        return None, []

    personal_uuid: str | None = None
    org_uuids: list[str] = []
    org_seen: set[str] = set()
    for raw in _iter_namespace_dicts_from_user_root(root):
        item = _normalize_namespace_item(raw)
        if not item:
            continue
        if is_csghub_personal_namespace(item["type"]):
            if personal_uuid is None:
                personal_uuid = item["uuid"]
            continue
        if not is_csghub_organization_namespace(item["type"]):
            continue
        if item["uuid"] in org_seen:
            continue
        org_seen.add(item["uuid"])
        org_uuids.append(item["uuid"])
    return personal_uuid, org_uuids


def parse_organization_namespace_uuids(body: Any) -> list[str]:
    """Organization namespace_uuid only (legacy)."""
    _, org_uuids = parse_user_namespace_scopes(body)
    return org_uuids


def fetch_user_namespace_scopes(
    user_name: str | None,
    *,
    authorization: str | None = None,
    user_token: str | None = None,
) -> tuple[str | None, list[str]]:
    """Call CSGHub GET /user/{username}; return (personal namespace_uuid, org namespace_uuid list)."""
    name = str(user_name or "").strip()
    if not name:
        return None, []

    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    if not endpoint:
        logger.warning("CSGHUB_ENDPOINT not set; skip loading user namespaces")
        return None, []

    path = os.getenv("CSGHUB_USER_NAMESPACES_API_PATH", "/api/v1/user/{username}").strip()
    if not path.startswith("/"):
        path = f"/{path}"
    if "{username}" not in path:
        path = "/user/{username}"
    url = parse.urljoin(
        f"{endpoint}/",
        path.replace("{username}", parse.quote(name, safe="")).lstrip("/"),
    )

    headers = {"Accept": "application/json"}
    if authorization and str(authorization).strip():
        headers["Authorization"] = str(authorization).strip()
    elif user_token and str(user_token).strip():
        token = str(user_token).strip()
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"

    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            raw = resp.read().decode("utf-8")
        body = json.loads(raw) if raw else {}
        personal_uuid, org_uuids = parse_user_namespace_scopes(body)
        logger.debug(
            "Loaded user namespaces for user={} | personal={} | org_count={}",
            name,
            bool(personal_uuid),
            len(org_uuids),
        )
        return personal_uuid, org_uuids
    except error.HTTPError as exc:
        logger.warning(
            "CSGHub user namespaces HTTP error | user={} | status={} | url={}",
            name,
            exc.code,
            url,
        )
    except Exception as exc:
        logger.warning(
            "CSGHub user namespaces request failed | user={} | url={} | err={}",
            name,
            url,
            exc,
        )
    return None, []


def fetch_organization_namespace_uuids(
    user_name: str | None,
    *,
    authorization: str | None = None,
    user_token: str | None = None,
) -> list[str]:
    """Return organization namespace_uuid list only (legacy)."""
    _, org_uuids = fetch_user_namespace_scopes(
        user_name,
        authorization=authorization,
        user_token=user_token,
    )
    return org_uuids
