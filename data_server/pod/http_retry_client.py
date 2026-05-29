"""Pod calls DataFlow API: retry at fixed intervals unless auth failure."""

from __future__ import annotations

import json
import os
import time
from typing import Any
from urllib import error, request

from loguru import logger

# After first failure: immediate once, then 30s / 1min / 3min / 5min (stop on success)
RETRY_DELAYS_AFTER_FAILURE_SECONDS = (0, 30, 60, 180, 300)

AUTH_HTTP_STATUS = frozenset({401, 403})
AUTH_API_CODES = frozenset({401, 403})


class DataflowApiAuthError(RuntimeError):
    """Auth failure; do not retry."""


class DataflowApiRetryableError(RuntimeError):
    """Retryable failure."""


def _parse_response_body(raw: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {"raw": parsed}
    except json.JSONDecodeError:
        return {"raw": raw}


def _is_auth_failure(*, http_status: int | None, body: dict[str, Any]) -> bool:
    if http_status is not None and http_status in AUTH_HTTP_STATUS:
        return True
    api_code = body.get("code")
    try:
        if int(api_code) in AUTH_API_CODES:
            return True
    except (TypeError, ValueError):
        pass
    return False


def _is_success_body(body: dict[str, Any]) -> bool:
    api_code = body.get("code")
    if api_code is None:
        return True
    try:
        return int(api_code) == 200
    except (TypeError, ValueError):
        return False


def _single_post(
    *,
    url: str,
    data: bytes,
    headers: dict[str, str],
    timeout: int,
    label: str,
) -> dict[str, Any]:
    req = request.Request(url, data=data, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            http_status = getattr(resp, "status", None) or 200
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        body = _parse_response_body(detail)
        http_status = exc.code
        if _is_auth_failure(http_status=http_status, body=body):
            raise DataflowApiAuthError(
                f"{label} HTTP {http_status}: {body.get('msg') or detail}"
            ) from exc
        raise DataflowApiRetryableError(
            f"{label} HTTP {http_status}: {body.get('msg') or detail}"
        ) from exc
    except error.URLError as exc:
        raise DataflowApiRetryableError(f"{label} network error: {exc.reason}") from exc

    body = _parse_response_body(raw)
    if _is_auth_failure(http_status=http_status, body=body):
        raise DataflowApiAuthError(
            f"{label} API auth failed: {body.get('msg') or body}"
        )
    if not _is_success_body(body):
        raise DataflowApiRetryableError(
            f"{label} API code={body.get('code')}: {body.get('msg') or body}"
        )
    return body


def post_json_with_retry(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int | None = None,
    label: str = "DataFlow API",
) -> dict[str, Any]:
    """
    Up to 6 requests total: 1 initial + retries at 0s, 30s, 60s, 180s, 300s after failure.
    Auth failures raise immediately without retry.
    """
    if timeout is None:
        timeout = int(os.getenv("CSGHUB_HTTP_TIMEOUT", "30") or "30")
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    delays = RETRY_DELAYS_AFTER_FAILURE_SECONDS
    max_attempts = len(delays) + 1
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            delay = delays[attempt - 2]
            if delay > 0:
                logger.warning(
                    "{} retry {}/{} after {}s | url={}",
                    label,
                    attempt,
                    max_attempts,
                    delay,
                    url,
                )
                time.sleep(delay)
            else:
                logger.warning(
                    "{} retry {}/{} immediately | url={}",
                    label,
                    attempt,
                    max_attempts,
                    url,
                )

        try:
            return _single_post(
                url=url,
                data=data,
                headers=headers,
                timeout=timeout,
                label=label,
            )
        except DataflowApiAuthError:
            raise
        except DataflowApiRetryableError as exc:
            last_error = exc
            logger.warning(
                "{} attempt {}/{} failed: {}",
                label,
                attempt,
                max_attempts,
                exc,
            )
        except Exception as exc:
            last_error = DataflowApiRetryableError(f"{label} unexpected: {exc}")
            logger.warning(
                "{} attempt {}/{} unexpected: {}",
                label,
                attempt,
                max_attempts,
                exc,
            )

    assert last_error is not None
    raise last_error
