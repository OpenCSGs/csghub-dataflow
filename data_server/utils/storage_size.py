from __future__ import annotations

import re

STORAGE_SIZE_PRESETS: tuple[str, ...] = (
    "1Gi",
    "2Gi",
    "4Gi",
    "8Gi",
    "12Gi",
    "16Gi",
    "24Gi",
    "32Gi",
    "64Gi",
    "128Gi",
    "200Gi",
)
DEFAULT_STORAGE_SIZE = "4Gi"
_MAX_GIB = 2000


def normalize_storage_size(value: str | int | float | None) -> str:
    """
    Normalize user input to Kubernetes quantity string with Gi unit, e.g. 4Gi.
    Accepts: 4, "4", "4Gi", "4G", "4gi".
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        return DEFAULT_STORAGE_SIZE

    raw = str(value).strip()
    match = re.match(r"^(\d+(?:\.\d+)?)\s*(Gi|G|gi|giB)?$", raw, re.IGNORECASE)
    if not match:
        raise ValueError(f"无效的 storage_size: {value}，请使用如 4Gi 的格式")

    amount = float(match.group(1))
    if amount <= 0:
        raise ValueError("storage_size 必须大于 0")
    if amount > _MAX_GIB:
        raise ValueError(f"storage_size 不能超过 {_MAX_GIB}Gi")

    if amount == int(amount):
        return f"{int(amount)}Gi"
    return f"{amount}Gi"


def resolve_storage_size(
    value: str | int | float | None,
    *,
    fallback: str | None = None,
) -> str:
    if value is None or (isinstance(value, str) and not str(value).strip()):
        if fallback:
            return normalize_storage_size(fallback)
        return DEFAULT_STORAGE_SIZE
    return normalize_storage_size(value)
