"""Argo Pod tasks log to stdout only; not written to database."""

from loguru import logger


def log_task_info(task_uid: str | None, message: str) -> None:
    uid = task_uid or "-"
    logger.info("[task_uid={}] {}", uid, message)


def log_task_error(task_uid: str | None, message: str) -> None:
    uid = task_uid or "-"
    logger.error("[task_uid={}] {}", uid, message)
