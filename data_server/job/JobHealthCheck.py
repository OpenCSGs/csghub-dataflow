"""
Job Health Check Module

This module provides functionality to detect and fix orphaned jobs
that remain in 'Processing' state after service restart or unexpected interruptions.
"""

import datetime
import os
from typing import Dict

from sqlalchemy.orm import Session
from loguru import logger

from data_server.database.session import get_sync_session
from data_server.job.JobModels import Job
from data_server.schemas.responses import JOB_STATUS
from data_server.utils.csghub_client import fetch_platform_job_status
from data_server.utils.csghub_status_sync import RUNNING_STATUSES, _entity_namespace_uuid, _status_key


def fix_orphaned_jobs() -> Dict[str, any]:
    """
    Fix orphaned jobs after service restart.

    This function checks all jobs in 'Processing' state and verifies if they are
    actually running in CSGHub. If not, marks them as 'Failed'.

    Returns:
        dict: Statistics about fixed jobs
            - fixed_count: Number of jobs marked as failed
            - skipped_count: Number of jobs still running
            - fixed_jobs: List of fixed job details
    """
    logger.info("Starting orphaned jobs health check...")

    fixed_count = 0
    skipped_count = 0
    fixed_jobs = []

    try:
        with get_sync_session() as session:
            # Query all jobs in Processing state
            processing_jobs = session.query(Job).filter(
                Job.status == JOB_STATUS.PROCESSING.value
            ).all()

            total_jobs = len(processing_jobs)
            logger.info(f"Found {total_jobs} jobs in Processing state")

            if total_jobs == 0:
                logger.info("No jobs to check, health check completed")
                return {
                    'fixed_count': 0,
                    'skipped_count': 0,
                    'fixed_jobs': []
                }

            for job in processing_jobs:
                try:
                    is_running = _check_job_actually_running(job)

                    if not is_running:
                        # Job is not running, mark as failed
                        _mark_job_as_failed(session, job, "Job was interrupted by service restart")

                        fixed_jobs.append({
                            'job_id': job.job_id,
                            'job_name': job.job_name,
                            'job_source': job.job_source,
                            'flow_id': job.flow_id or 'N/A',
                            'csghub_job_id': job.csghub_job_id or 'N/A',
                        })
                        fixed_count += 1

                        logger.warning(
                            f"Job {job.job_id} ({job.job_name}): "
                            f"Not running in backend, marked as Failed"
                        )
                    else:
                        skipped_count += 1
                        logger.info(
                            f"Job {job.job_id} ({job.job_name}): "
                            f"Still running, skipping"
                        )

                except Exception as e:
                    logger.error(
                        f"Error checking job {job.job_id}: {str(e)}, "
                        f"marking as Failed for safety"
                    )
                    # If we can't verify, mark as failed for safety
                    try:
                        _mark_job_as_failed(session, job, f"Health check failed: {str(e)}")
                        fixed_count += 1
                    except Exception as mark_error:
                        logger.error(f"Failed to mark job {job.job_id} as Failed: {mark_error}")

            # Commit all changes
            session.commit()

            logger.info(
                f"Orphaned jobs health check completed: "
                f"{fixed_count} jobs marked as Failed, "
                f"{skipped_count} jobs still running"
            )

            return {
                'fixed_count': fixed_count,
                'skipped_count': skipped_count,
                'fixed_jobs': fixed_jobs
            }

    except Exception as e:
        logger.error(f"Failed to complete orphaned jobs health check: {str(e)}")
        raise


def _check_job_actually_running(job: Job) -> bool:
    """
    Check if a job is actually running in the backend.

    For jobs submitted to CSGHub, checks CSGHub main task status.
    For records without CSGHub identifiers, assumes not running after restart.

    Args:
        job: Job object to check

    Returns:
        bool: True if job is actually running, False otherwise
    """
    if job.flow_id or job.csghub_job_id:
        logger.debug(
            f"Job {job.job_id}: Checking CSGHub task flow_id={job.flow_id}, job_id={job.csghub_job_id}"
        )
        return _check_csghub_job_running(job)

    logger.debug(
        f"Job {job.job_id}: No CSGHub identifier found, "
        f"assuming not running (job_source: {job.job_source})"
    )
    return False


def _check_csghub_job_running(job: Job) -> bool:
    """
    Check if a CSGHub task is actually running.

    Args:
        job: Job record

    Returns:
        bool: True if task is in running state, False otherwise
    """
    namespace = _entity_namespace_uuid(job)
    user_token = os.getenv("CSGHUB_HEALTH_CHECK_TOKEN", "").strip() or None
    if not namespace or not user_token:
        logger.warning(
            "Job {}: skip CSGHub status check (need namespace_uuid and CSGHUB_HEALTH_CHECK_TOKEN)",
            job.job_id,
        )
        return False

    try:
        parsed = fetch_platform_job_status(
            namespace=namespace,
            csghub_job_id=job.csghub_job_id,
            flow_id=job.flow_id,
            user_token=user_token,
            csghub_response_payload=job.csghub_response_payload,
        )
        task_status = parsed.get("status") or ""
        is_running = _status_key(task_status) in RUNNING_STATUSES

        logger.debug(
            f"CSGHub task flow_id={job.flow_id}, job_id={job.csghub_job_id}: status = {task_status}, "
            f"is_running = {is_running}"
        )

        return is_running

    except Exception as e:
        logger.warning(
            f"Failed to check CSGHub task for job {job.job_id}: {str(e)}, "
            f"assuming not running"
        )
        return False


def _mark_job_as_failed(session: Session, job: Job, reason: str):
    """
    Mark a job as failed with proper logging.

    Args:
        session: Database session
        job: Job object to mark as failed
        reason: Reason for marking as failed
    """
    old_status = job.status
    job.status = JOB_STATUS.FAILED.value

    if not job.date_finish:
        job.date_finish = datetime.datetime.now()

    logger.warning(
        f"Marking job {job.job_id} ({job.job_name}) as Failed: "
        f"previous_status={old_status}, reason={reason}"
    )

