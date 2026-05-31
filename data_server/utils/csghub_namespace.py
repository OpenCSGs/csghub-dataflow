"""CSGHub DataFlow namespace from request namespace_uuid + namespace_type.

For personal tasks, use server default when namespace_uuid is omitted (may become required once frontend is ready).
"""

NAMESPACE_TYPE_PERSONAL = "personal"
NAMESPACE_TYPE_ORGANIZATION = "organization"

# Default personal namespace UUID (backend fallback before frontend integration)
DEFAULT_PERSONAL_NAMESPACE_UUID = "83f7649d-2373-4434-b159-411e161e0f35"

_ALLOWED_NAMESPACE_TYPES = frozenset({NAMESPACE_TYPE_PERSONAL, NAMESPACE_TYPE_ORGANIZATION})


def normalize_namespace_type(namespace_type: str | None) -> str:
    t = (namespace_type or NAMESPACE_TYPE_PERSONAL).strip().lower()
    if t not in _ALLOWED_NAMESPACE_TYPES:
        raise ValueError("namespace_type 必须为 personal 或 organization")
    return t


def parse_namespace_fields(
    *,
    namespace_uuid: str | None,
    namespace_type: str | None = None,
) -> tuple[str, str]:
    """Return (namespace_uuid, namespace_type) for persistence and CSGHub URL."""
    nt = normalize_namespace_type(namespace_type)
    if namespace_uuid and str(namespace_uuid).strip():
        nu = str(namespace_uuid).strip()
    elif nt == NAMESPACE_TYPE_PERSONAL:
        nu = DEFAULT_PERSONAL_NAMESPACE_UUID
    else:
        raise ValueError("组织任务必须在请求体中提供 namespace_uuid")
    return nu, nt
