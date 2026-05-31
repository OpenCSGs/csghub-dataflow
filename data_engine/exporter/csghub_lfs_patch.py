"""
Workaround for pycsghub upload_large_folder LFS preupload.

Git LFS batch API allows the server to omit ``actions`` when the object
already exists (response is only ``{oid, size}``). csghub-sdk 0.7.x–0.9.x
treats that as a hard error. Datasource re-uploads often hit this path.
"""

from __future__ import annotations

import time
import traceback

from loguru import logger

from data_server.pod.http_retry_client import RETRY_DELAYS_AFTER_FAILURE_SECONDS

_PATCH_FLAG = "_dataflow_lfs_exists_patch_applied"
_LFS_PREUPLOAD_LABEL = "LFS preupload"
_MAX_PREUPLOAD_ATTEMPTS = len(RETRY_DELAYS_AFTER_FAILURE_SECONDS) + 1
_preupload_failure_counts: dict[str, int] = {}


def apply_csghub_lfs_exists_patch() -> None:
    from pycsghub.upload_large_folder import workers as lfs_workers

    if getattr(lfs_workers, _PATCH_FLAG, False):
        return

    original_preupload = lfs_workers._preupload_lfs

    def _preupload_lfs_patched(item, status, api, repo_id, repo_type, revision, endpoint, token):
        paths, metadata = item
        try:
            return original_preupload(
                item, status, api, repo_id, repo_type, revision, endpoint, token
            )
        except ValueError as exc:
            if not _is_lfs_object_already_exists_error(exc, metadata):
                raise
            logger.warning(
                "{} file already exists on server, skipping slice upload | file={}",
                _LFS_PREUPLOAD_LABEL,
                paths.path_in_repo,
            )
            _preupload_failure_counts.pop(paths.file_path, None)
            metadata.lfs_upload_part_count = 0
            metadata.is_uploaded = True
            metadata.save(paths)

    def _execute_job_pre_upload_lfs_patched(
        items, status, api, repo_id, repo_type, revision, endpoint, token
    ):
        item = items[0]
        paths, metadata = item
        action = "preupload"
        try:
            if status.is_lfs_upload_completed(item):
                action = f"{action} check complete"
                lfs_workers._preupload_lfs_done(item=item, status=status)
                _preupload_failure_counts.pop(paths.file_path, None)
                status.queue_commit.put(item)
            elif metadata.is_uploaded:
                _preupload_failure_counts.pop(paths.file_path, None)
                status.queue_commit.put(item)
            else:
                action = f"{action} fetch batch info"
                lfs_workers._preupload_lfs(
                    item=item,
                    status=status,
                    api=api,
                    endpoint=endpoint,
                    token=token,
                    repo_id=repo_id,
                    repo_type=repo_type,
                    revision=revision,
                )
                paths, metadata = item
                if metadata.is_uploaded:
                    _preupload_failure_counts.pop(paths.file_path, None)
                    status.queue_commit.put(item)
                else:
                    status.queue_preupload_lfs.put(item)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            if _maybe_handle_already_exists_from_exception(exc, item):
                status.queue_commit.put(item)
            else:
                _handle_retryable_preupload_failure(
                    paths=paths,
                    action=action,
                    error=exc,
                    status=status,
                    item=item,
                )
        finally:
            with status.lock:
                status.nb_workers_preupload_lfs -= 1

    lfs_workers._preupload_lfs = _preupload_lfs_patched
    lfs_workers._execute_job_pre_upload_lfs = _execute_job_pre_upload_lfs_patched
    setattr(lfs_workers, _PATCH_FLAG, True)
    logger.debug("Applied CSGHub LFS already-exists patch for upload_large_folder")


def _maybe_handle_already_exists_from_exception(exc: Exception, item) -> bool:
    if not isinstance(exc, ValueError):
        return False
    paths, metadata = item
    if not _is_lfs_object_already_exists_error(exc, metadata):
        return False
    logger.warning(
        "{} file already exists on server, skipping slice upload | file={}",
        _LFS_PREUPLOAD_LABEL,
        paths.path_in_repo,
    )
    _preupload_failure_counts.pop(paths.file_path, None)
    metadata.lfs_upload_part_count = 0
    metadata.is_uploaded = True
    metadata.save(paths)
    return True


def _handle_retryable_preupload_failure(*, paths, action, error, status, item) -> None:
    fail_key = paths.file_path
    fail_count = _preupload_failure_counts.get(fail_key, 0) + 1
    _preupload_failure_counts[fail_key] = fail_count

    logger.warning(
        "{} attempt {}/{} failed | action={} | file={} | error={}",
        _LFS_PREUPLOAD_LABEL,
        fail_count,
        _MAX_PREUPLOAD_ATTEMPTS,
        action,
        paths.path_in_repo,
        error,
    )
    traceback.print_exc()

    if fail_count >= _MAX_PREUPLOAD_ATTEMPTS:
        raise RuntimeError(
            f"{_LFS_PREUPLOAD_LABEL} failed after {fail_count} attempts for "
            f"{paths.path_in_repo}: {error}"
        ) from error

    delay = RETRY_DELAYS_AFTER_FAILURE_SECONDS[fail_count - 1]
    next_attempt = fail_count + 1
    if delay > 0:
        logger.warning(
            "{} retry {}/{} after {}s | file={}",
            _LFS_PREUPLOAD_LABEL,
            next_attempt,
            _MAX_PREUPLOAD_ATTEMPTS,
            delay,
            paths.path_in_repo,
        )
        time.sleep(delay)
    else:
        logger.warning(
            "{} retry {}/{} immediately | file={}",
            _LFS_PREUPLOAD_LABEL,
            next_attempt,
            _MAX_PREUPLOAD_ATTEMPTS,
            paths.path_in_repo,
        )
    status.queue_preupload_lfs.put(item)


def _is_lfs_object_already_exists_error(exc: ValueError, metadata) -> bool:
    message = str(exc)
    if "no slices batch actions info found" not in message:
        return False
    remote_oid = _extract_remote_oid(message)
    if not remote_oid or not metadata.sha256:
        return False
    return remote_oid == metadata.sha256


def _extract_remote_oid(message: str) -> str | None:
    marker = "from server: "
    idx = message.find(marker)
    if idx < 0:
        return None
    payload = message[idx + len(marker):].strip()
    if not payload.startswith("{"):
        return None
    try:
        import ast

        parsed = ast.literal_eval(payload)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    oid = parsed.get("oid")
    return str(oid) if oid else None
