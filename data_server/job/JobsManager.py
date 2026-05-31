import yaml
import json
from io import StringIO
from data_server.algo_templates.utils.parse_algo_dslText import convert_raw_to_processed
from data_server.job.JobModels import Job
from data_server.schemas import responses
from sqlalchemy.orm import Session
from datetime import datetime
from data_server.logic.models import Recipe
from data_server.logic.utils import (
    read_jsonl_to_list,
    data_format,
    setup_executor,
    exclude_fields_config,
    strip_recipe_scheduler_fields,
)
import os
import shutil
import re
from data_server.database.session import get_sync_session
from multiprocessing import Process
from data_server.logic.utils import greate_task_uid
from data_server.job.SubTaskManager import clear_subtasks_for_parent, replace_subtasks_for_parent
from data_server.utils.csghub_dag_builder import build_pipeline_dag, build_tool_dag
from data_server.utils.csghub_client import (
    build_csghub_payload,
    build_job_flow_id,
    build_job_flow_id_restart,
    collect_repo_ids,
    ensure_csghub_job_create_success,
    submit_job_to_csghub,
    try_cancel_csghub_job,
    resolve_csghub_remote_job_id,
)
from data_server.utils.job_work_dir import init_local_job_work_dir
from data_server.utils.task_access import (
    apply_task_list_scope,
    attach_can_delete,
    can_delete_task,
    log_task_list_sql,
    resolve_organization_namespace_uuids_for_list,
    soft_delete_record,
    user_can_access_task,
)
from loguru import logger
from data_server.utils.csghub_namespace import (
    normalize_namespace_type,
    parse_namespace_fields,
)
from loguru import logger


def _serialize_tool_job_cfg(job_cfg) -> str:
    return json.dumps(job_cfg.model_dump(mode="json"), ensure_ascii=False)


def _extract_tool_config_from_stored_request(job: Job) -> dict:
    """Restore tool config from last submitted csghub_request_payload."""
    raw = getattr(job, "csghub_request_payload", None)
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    for task in payload.get("dag_tasks") or []:
        for param in task.get("parameters") or []:
            if param.get("name") != "task_params":
                continue
            try:
                task_params = json.loads(param.get("value") or "{}")
            except json.JSONDecodeError:
                continue
            cfg = task_params.get("config")
            if isinstance(cfg, dict) and cfg.get("name"):
                return cfg
    return {}


def _normalize_job_config(job: Job, job_cfg=None) -> dict:
    # Pipeline operator list uses yaml_config from dslText (frontend often sends process: [])
    if job.job_source == "pipeline" and job.yaml_config:
        yaml_buffer = StringIO(job.yaml_config)
        yaml_buffer.name = f"job_{job.job_id}_yaml_config"
        return strip_recipe_scheduler_fields(
            Recipe.parse_yaml(yaml_buffer).model_dump(mode="json")
        )

    if job.job_source == "tool" and job.yaml_config:
        try:
            stored = json.loads(job.yaml_config)
            if isinstance(stored, dict) and stored.get("name"):
                return stored
        except json.JSONDecodeError:
            pass

    if job_cfg is not None and hasattr(job_cfg, "model_dump"):
        return strip_recipe_scheduler_fields(job_cfg.model_dump(mode="json"))

    restored = _extract_tool_config_from_stored_request(job)
    if restored:
        return restored

    return {}


def _resolve_job_namespace(
    job: Job,
    namespace_uuid: str | None = None,
    namespace_type: str | None = None,
) -> tuple[str, str]:
    """Prefer Job stored namespace to avoid invalid default UUID at execution."""
    if job.namespace_uuid and str(job.namespace_uuid).strip():
        nu = str(job.namespace_uuid).strip()
        nt = normalize_namespace_type(namespace_type or job.namespace_type)
        return nu, nt
    return parse_namespace_fields(
        namespace_uuid=namespace_uuid,
        namespace_type=namespace_type,
    )


def _sync_job_fields_from_tool_config(job: Job, config: dict) -> None:
    if not config:
        return
    if config.get("namespace_uuid") and not job.namespace_uuid:
        job.namespace_uuid = str(config["namespace_uuid"]).strip()
    if config.get("namespace_type"):
        job.namespace_type = normalize_namespace_type(config["namespace_type"])
    if config.get("cluster_id") and not job.cluster_id:
        job.cluster_id = str(config["cluster_id"]).strip()
    if config.get("cluster_name") and not job.cluster_name:
        job.cluster_name = str(config["cluster_name"]).strip()
    if config.get("resource_id") is not None and job.resource_id is None:
        job.resource_id = config["resource_id"]
    if config.get("resource_name") and not job.resource_name:
        job.resource_name = config["resource_name"]
    if config.get("storage_size") and not getattr(job, "storage_size", None):
        job.storage_size = config["storage_size"]


def _ensure_tool_job_config_ready(job: Job, job_cfg=None) -> dict:
    config = _normalize_job_config(job, job_cfg=job_cfg)
    _sync_job_fields_from_tool_config(job, config)
    if job.job_source == "tool" and not config.get("name"):
        raise ValueError(
            "工具任务配置已丢失，无法执行。请重新创建任务；"
            "新建任务会自动保存配置，旧任务若从未成功提交过可能无法重启。"
        )
    return config


def _export_target_from_job(job: Job, job_cfg=None) -> tuple[str | None, str | None]:
    config = _normalize_job_config(job, job_cfg=job_cfg)
    export_repo_id = getattr(job, "export_repo_id", None) or config.get("repo_id")
    export_branch = (
        getattr(job, "export_branch_name", None)
        or config.get("branch")
        or job.branch
    )
    return export_repo_id, export_branch


def _build_job_task_params(
    job: Job,
    *,
    user_id=None,
    user_name=None,
    user_token=None,
    authorization: str | None = None,
    job_cfg=None,
    task_run_time: str | None = None,
) -> dict:
    config = _ensure_tool_job_config_ready(job, job_cfg=job_cfg)
    export_repo_id, export_branch = _export_target_from_job(job, job_cfg=job_cfg)
    if not export_branch:
        export_branch = job.branch or "main"
    task_params = {
        "job_id": job.job_id,
        "job_name": job.job_name,
        "job_source": job.job_source,
        "job_type": job.job_type,
        "repo_id": job.repo_id,
        "branch": job.branch,
        "export_repo_id": export_repo_id,
        "export_branch_name": export_branch,
        "user_id": user_id,
        "user_name": user_name,
        "user_token": user_token,
        "authorization": authorization,
        "owner_id": job.owner_id,
        "owner_org_id": job.owner_org_id,
        "owner_org_name": job.owner_org_name,
        "cluster_id": job.cluster_id,
        "cluster_name": job.cluster_name,
        "resource_id": job.resource_id,
        "resource_name": job.resource_name,
        "storage_size": getattr(job, "storage_size", None),
        "execute_time": task_run_time,
        "config": config,
    }
    if job.job_source != "pipeline":
        task_params["tool_name"] = task_params["config"].get("name") or job.job_name
    return task_params


def delete_directory_if_exists(directory_path):
    if not directory_path:
        print("Directory path is not provided.")
        return
    if os.path.exists(directory_path) and os.path.isdir(directory_path):
        try:
            shutil.rmtree(directory_path)
            print(
                f"Directory {directory_path} and all its contents have been deleted.")
        except Exception as e:
            print(
                f"An error occurred while trying to delete {directory_path}: {e}")
    else:
        print(
            f"Directory {directory_path} does not exist or is not a directory.")


def get_job_by_uid(session: Session, task_uid: str):
    if not task_uid:
        return None
    return session.query(Job).filter(Job.uuid == task_uid).first()


def enrich_job_for_list(job: Job, *, user_id=None, isadmin: bool = False):
    """List view: include CSGHub log fields explicitly (avoid serialization drop)."""
    show = responses.ShowJob.model_validate(job)
    remote_id = None
    if job.csghub_job_id or job.flow_id:
        remote_id = resolve_csghub_remote_job_id(
            job.csghub_job_id or job.flow_id,
            flow_id=job.flow_id,
            csghub_response_payload=job.csghub_response_payload,
        )
    payload = show.model_copy(
        update={
            "uuid": job.uuid,
            "namespace_uuid": job.namespace_uuid,
            "flow_id": job.flow_id,
            "csghub_job_id": job.csghub_job_id,
            "csghub_remote_job_id": remote_id or job.csghub_job_id or job.flow_id,
            "owner_id": job.owner_id,
        }
    )
    return payload.model_copy(
        update={
            "can_delete": can_delete_task(
                owner_id=job.owner_id, user_id=user_id, isadmin=isadmin
            ),
        }
    )


def build_job_log_context(job: Job | None) -> dict | None:
    """Return job metadata for frontend CSGHub log access (not log content)."""
    if job is None:
        return None
    remote_id = None
    if job.csghub_job_id or job.flow_id:
        remote_id = resolve_csghub_remote_job_id(
            job.csghub_job_id or job.flow_id,
            flow_id=job.flow_id,
            csghub_response_payload=job.csghub_response_payload,
        )
    return {
        "job_id": job.job_id,
        "uuid": job.uuid,
        "namespace_uuid": job.namespace_uuid,
        "flow_id": job.flow_id,
        "csghub_job_id": job.csghub_job_id,
        "csghub_remote_job_id": remote_id or job.csghub_job_id or job.flow_id,
        "cluster_name": job.cluster_name,
        "resource_name": job.resource_name,
    }


def list_jobs(
    user_id,
    session: Session,
    isadmin=False,
    page: int = None,
    page_size: int = None,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    job_source: str | None = None,
):
    query = session.query(Job)
    query = apply_task_list_scope(
        query,
        Job,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )
    if job_source:
        query = query.filter(Job.job_source == job_source)
    query = query.order_by(Job.job_id.desc())

    list_label = f"job/{job_source}" if job_source else "job"
    log_task_list_sql(
        query,
        label=list_label,
        session=session,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
        page=page,
        page_size=page_size,
        job_source=job_source,
    )
    if page is not None and page_size is not None:
        total = query.count()
        jobs = query.offset((page - 1) * page_size).limit(page_size).all()
        total_pages = (total + page_size - 1) // page_size
        return jobs, total, total_pages
    else:
        jobs = query.all()
        if jobs is None:
            jobs = []  # ensure not return None
        return jobs


def get_job_data(
    job_id: int,
    user_id,
    session: Session,
    isadmin=False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    user_name: str | None = None,
    authorization: str | None = None,
    user_token: str | None = None,
):
    if organization_namespace_uuids is None and not isadmin:
        organization_namespace_uuids = resolve_organization_namespace_uuids_for_list(
            user_name=user_name,
            authorization=authorization,
            user_token=user_token,
            isadmin=isadmin,
        )
    item = session.query(Job).filter(Job.job_id == job_id, Job.is_active.is_(True)).first()
    if item and user_can_access_task(
        item,
        user_id,
        isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    ):
        return item
    return None


def retreive_job(
    job_id: int,
    user_id,
    session: Session,
    isadmin=False,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
):
    updated_job_details = {'job': {}, 'config_content': {}}
    item = get_job_data(
        job_id,
        user_id,
        session,
        isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )

    if item is None:
        return item

    job_details: responses.JobDetails = item
    try:
        work_dir = job_details.work_dir


        config_file = os.path.join(work_dir, 'config.yaml')
        # read config.yaml
        with open(config_file, 'r') as f:
            config_content = Recipe.parse_yaml(f.read())
        trace_dir = os.path.join(work_dir, 'trace')

        # init process
        process = config_content.process
        # set op.status to responses.JOB_STATUS.FAILED.value, if the Job status is responses.JOB_STATUS.FAILED.value
        if job_details.status == responses.JOB_STATUS.FAILED.value:
            for op in process:
                op.status = responses.JOB_STATUS.FAILED.value

        for filename in os.listdir(trace_dir):
            name_without_ext = filename.split('.')[0].split('-')[1]

            if filename.endswith('.jsonl'):
                jsonl_filepath = os.path.join(trace_dir, filename)
                data_list = read_jsonl_to_list(jsonl_filepath)
                for op in process:
                    if op.name == name_without_ext:
                        if not op.type:
                            op.type = 'Others'
                        op.data = data_format(data_list, op.type)
            count_filename = f"count-{name_without_ext}.txt"
            if filename == count_filename:
                count_filepath = os.path.join(trace_dir, count_filename)
                if os.path.exists(count_filepath):
                    with open(count_filepath, 'r') as f:
                        data_lines = f.read().strip()
                        for op in process:
                            if op.name == name_without_ext:
                                op.status = responses.JOB_STATUS.FINISHED.value
                                op.data_lines = int(data_lines)
        # handle blank datas
        for op in process:
            if not op.data:
                if not op.type:
                    op.type = 'Others'
                op.data = data_format(op.data, op.type)
        config_dict = config_content.model_dump()
        config_dict['process'] = process
        updated_job_details = {
            'job': job_details,
            'config_content': config_dict
        }
    except Exception as e:
        print(f"Warn: retreive job config_content failed, maybe it's caused by the job_source is tool: {str(e)}")
        updated_job_details = {
            'job': job_details,
            'config_content': {}
        }
    return updated_job_details


def retreive_log(job_id: int, user_id, session: Session, isadmin=False):
    current_job = None
    if isadmin:
        current_job = session.query(Job).filter(Job.job_id == job_id).first()
    else:
        current_job = session.query(Job).filter(
            Job.owner_id == user_id).filter(Job.job_id == job_id).first()
    if current_job is None:
        return {"session_log": "No permission to get this job's log or cannot found this job's data"}
    if not current_job.work_dir or current_job.work_dir.strip() == "":
        return {"session_log": "No session log found"}

    log_dir = os.path.join(current_job.work_dir, 'log')
    if not os.path.exists(log_dir) or not os.path.isdir(log_dir):
        return {"session_log": "No session log found: log directory does not exist"}
    
    latest_time = None
    latest_file = None
    time_pattern = re.compile(r'time_(\d{14})\.txt$')
    try:
        for filename in os.listdir(log_dir):
            match = time_pattern.search(filename)
            if match:
                file_time = datetime.strptime(match.group(1), '%Y%m%d%H%M%S')
                if not latest_time or file_time > latest_time:
                    latest_time = file_time
                    latest_file = filename
    except Exception as e:
        logger.error(f"An exception occurred while listing log directory {log_dir}: {e}")
        return {"session_log": f"No session log found: {str(e)}"}

    if not latest_file:
        return {"session_log": "No session log found"}

    # read latest log
    latest_file_path = os.path.join(log_dir, latest_file)
    file_content = ''
    try:
        # Try UTF-8 first, then fallback to other encodings
        encodings = ['utf-8', 'gbk', 'latin-1']
        read_success = False
        for encoding in encodings:
            try:
                with open(latest_file_path, 'r', encoding=encoding) as f:
                    file_content = f.read()
                read_success = True
                break
            except UnicodeDecodeError:
                continue
        if not read_success:
            raise Exception(f"Failed to decode log file with encodings: {encodings}")
    except Exception as e:
        logger.error(f"An exception occurred while reading log file {latest_file_path}: {e}")
        file_content = f"No session log got: {str(e)}"
    return {"session_log": file_content}


def _is_job_queued_status(status: str | None) -> bool:
    return (status or "").strip() == responses.JOB_STATUS.QUEUED.value


def _submit_job_to_csghub(
    session: Session,
    job: Job,
    job_cfg,
    user_token: str | None,
    namespace: str,
    user_id=None,
    user_name=None,
    authorization: str | None = None,
    *,
    flow_id: str | None = None,
    reset_work_dir: bool = False,
    task_run_time: str | None = None,
):
    resolved_flow_id = flow_id or build_job_flow_id(job.job_source or "tool", job.job_id)
    job.flow_id = resolved_flow_id
    export_repo_id, _export_branch = _export_target_from_job(job, job_cfg=job_cfg)
    if export_repo_id and not getattr(job, "export_repo_id", None):
        job.export_repo_id = export_repo_id
    config_yaml = getattr(job, "yaml_config", None) or ""
    if not config_yaml and job_cfg is not None:
        try:
            config_yaml = job_cfg.yaml(exclude=exclude_fields_config)
        except Exception:
            config_yaml = ""
    if reset_work_dir or not job.work_dir:
        job.work_dir = init_local_job_work_dir(
            resolved_flow_id,
            config_yaml=config_yaml if config_yaml else None,
        )
    task_params = _build_job_task_params(
        job,
        user_id=user_id,
        user_name=user_name,
        user_token=user_token,
        authorization=authorization,
        job_cfg=job_cfg,
        task_run_time=task_run_time,
    )
    task_params["flow_id"] = resolved_flow_id
    if job.job_source == "pipeline":
        dag_tasks = build_pipeline_dag(resolved_flow_id, task_params)
    else:
        dag_tasks = build_tool_dag(resolved_flow_id, job.job_name, task_params)
    if job_cfg is not None and hasattr(job_cfg, "model_dump") and job.job_source == "tool":
        job.yaml_config = _serialize_tool_job_cfg(job_cfg)
    elif job.job_source == "tool" and not job.yaml_config:
        restored_cfg = _normalize_job_config(job, job_cfg=None)
        if restored_cfg:
            job.yaml_config = json.dumps(restored_cfg, ensure_ascii=False)
    job_desc = None
    if job_cfg is not None:
        job_desc = getattr(job_cfg, "description", None)
    if not job_desc:
        config = _normalize_job_config(job, job_cfg=job_cfg)
        job_desc = (config.get("description") if config else None) or job.job_name
    payload = build_csghub_payload(
        job_id=resolved_flow_id,
        job_name=job.job_name,
        job_desc=job_desc,
        resource_id=job.resource_id,
        resource_name=job.resource_name,
        storage_size=getattr(job, "storage_size", None),
        repo_ids=collect_repo_ids(job.repo_id, getattr(job, "export_repo_id", None)),
        dag_tasks=dag_tasks,
    )
    job.csghub_request_payload = json.dumps(payload, ensure_ascii=False)
    response = submit_job_to_csghub(
        payload, namespace=namespace, user_token=user_token, authorization=authorization
    )
    job.csghub_response_payload = json.dumps(response, ensure_ascii=False)
    parsed = ensure_csghub_job_create_success(response)
    job.csghub_job_id = parsed["job_id"]
    job.csghub_status = parsed.get("status") or "Submitted"
    job.status = responses.JOB_STATUS.QUEUED.value
    job.date_finish = None
    replace_subtasks_for_parent(
        session=session,
        parent_type=job.job_source or "tool",
        parent_id=job.job_id,
        flow_id=resolved_flow_id,
        dag_tasks=dag_tasks,
    )
    return response


def _mark_job_submit_failed(
    job: Job,
    error: Exception | str | None = None,
    session: Session | None = None,
):
    job.status = responses.JOB_STATUS.FAILED.value
    job.date_finish = datetime.now()
    job.csghub_status = "Failed"
    if session is not None and job.job_id:
        clear_subtasks_for_parent(
            session,
            parent_type=job.job_source or "tool",
            parent_id=job.job_id,
        )
    if error is not None:
        logger.error("Job CSGHub submit failed: {}", error)


# def create_new_job(job_cfg, user_id, user_name, user_token,yaml_config):
def create_new_job(
    job_cfg, user_id, user_name, user_token, owner_org_id=None, owner_org_name=None, authorization=None
):
    # replace space to underscore in project name, as the space will lead to job run error
    # print(job_cfg.accelerator)
    nu, nt = parse_namespace_fields(
        namespace_uuid=job_cfg.namespace_uuid,
        namespace_type=job_cfg.namespace_type,
    )
    tool_yaml_config = (
        _serialize_tool_job_cfg(job_cfg)
        if getattr(job_cfg, "job_source", None) == "tool"
        and hasattr(job_cfg, "model_dump")
        else None
    )
    job = Job(job_name=job_cfg.project_name.replace(" ", "_"), data_source=job_cfg.dataset_path,
              data_target=job_cfg.export_path,
              repo_id=job_cfg.repo_id, branch=job_cfg.branch,
              status=responses.JOB_STATUS.QUEUED.value, job_type=job_cfg.type, job_source=job_cfg.job_source,
              owner_id=user_id,
              owner_org_id=owner_org_id,
              owner_org_name=owner_org_name,
              cluster_id=job_cfg.cluster_id,
              cluster_name=job_cfg.cluster_name,
              resource_id=job_cfg.resource_id,
              resource_name=job_cfg.resource_name,
              storage_size=getattr(job_cfg, "storage_size", None),
              namespace_uuid=nu,
              namespace_type=nt,
              yaml_config=tool_yaml_config,
              )

    with get_sync_session() as session:
        with session.begin():
            session.add(job)
            session.flush()
        session.refresh(job)
        try:
            _submit_job_to_csghub(
                session,
                job,
                job_cfg,
                user_token,
                nu,
                user_id=user_id,
                user_name=user_name,
                authorization=authorization,
            )
        except Exception as e:
            _mark_job_submit_failed(job, e, session)
            session.commit()
            raise
        session.commit()
    # from data_server.job.JobExecutor import run_executor
    # executor = setup_executor()
    # executor.submit(run_executor, job_cfg, job.job_id,
    #                 job.job_name, user_id, user_name, user_token)

    result = {"job_id": job.job_id,
              "job_name": job.job_name, "status": job.status}

    return result


def create_pipline_new_job(
    job_cfg,
    user_id,
    user_name,
    user_token,
    yaml_config,
    owner_org_id=None,
    owner_org_name=None,
    authorization=None,
):
    # replace space to underscore in project name, as the space will lead to job run error
    # create uuid
    task_uuid = greate_task_uid()
    nu, nt = parse_namespace_fields(
        namespace_uuid=job_cfg.namespace_uuid,
        namespace_type=job_cfg.namespace_type,
    )
    job = Job(uuid=task_uuid,job_name=job_cfg.project_name.replace(" ", "_"), data_source=job_cfg.dataset_path, data_target=job_cfg.export_path,
              repo_id=job_cfg.repo_id, branch=job_cfg.branch,
              status=responses.JOB_STATUS.QUEUED.value, job_type=job_cfg.type, job_source=job_cfg.job_source,
              owner_id=user_id, owner_org_id=owner_org_id, owner_org_name=owner_org_name,
              dslText=job_cfg.dslText, yaml_config=yaml_config,
              cluster_id=job_cfg.cluster_id, cluster_name=job_cfg.cluster_name,
              resource_id=job_cfg.resource_id, resource_name=job_cfg.resource_name,
              storage_size=getattr(job_cfg, "storage_size", None),
              namespace_uuid=nu,
              namespace_type=nt)

    with get_sync_session() as session:
        with session.begin():
            session.add(job)
            session.flush()
        session.refresh(job)
        if job_cfg.is_run:
            try:
                _submit_job_to_csghub(
                    session,
                    job,
                    job_cfg,
                    user_token,
                    nu,
                    user_id=user_id,
                    user_name=user_name,
                    authorization=authorization,
                )
            except Exception as e:
                _mark_job_submit_failed(job, e, session)
                session.commit()
                raise
            session.commit()
    result = {"job_id": job.job_id,
              "job_name": job.job_name, "status": job.status}

    return result


def _submit_existing_job_record(
    session: Session,
    job: Job,
    *,
    user_id,
    user_name,
    user_token,
    authorization,
    task_run_time: str | None = None,
):
    """Waiting: first submit this Job record to CSGHub (fixed flow_id=AC/AD{id})."""
    _ensure_tool_job_config_ready(job)
    nu, nt = _resolve_job_namespace(job)
    job.namespace_uuid = nu
    job.namespace_type = nt
    _submit_job_to_csghub(
        session,
        job,
        None,
        user_token,
        nu,
        user_id=user_id,
        user_name=user_name,
        authorization=authorization,
        flow_id=build_job_flow_id(job.job_source or "tool", job.job_id),
        reset_work_dir=not bool(job.work_dir),
        task_run_time=task_run_time,
    )


def _restart_job_record(
    session: Session,
    job: Job,
    *,
    user_id,
    user_name,
    user_token,
    authorization,
    task_run_time: str | None = None,
):
    """Non-waiting: restart with new flow_id to avoid duplicate CSGHub job_id."""
    _ensure_tool_job_config_ready(job)
    nu, nt = _resolve_job_namespace(job)
    job.namespace_uuid = nu
    job.namespace_type = nt
    backup_request_payload = job.csghub_request_payload
    backup_response_payload = job.csghub_response_payload
    if job.job_source == "tool" and not job.yaml_config:
        restored_cfg = _extract_tool_config_from_stored_request(job)
        if restored_cfg:
            job.yaml_config = json.dumps(restored_cfg, ensure_ascii=False)
    job.csghub_job_id = None
    job.csghub_status = None
    restart_flow_id = build_job_flow_id_restart(job.job_source or "tool", job.job_id)
    try:
        _submit_job_to_csghub(
            session,
            job,
            None,
            user_token,
            nu,
            user_id=user_id,
            user_name=user_name,
            authorization=authorization,
            flow_id=restart_flow_id,
            reset_work_dir=True,
            task_run_time=task_run_time,
        )
    except Exception:
        if backup_request_payload and not job.csghub_request_payload:
            job.csghub_request_payload = backup_request_payload
        if backup_response_payload and not job.csghub_response_payload:
            job.csghub_response_payload = backup_response_payload
        raise


def execute_job(
    job,
    user_id,
    user_name,
    user_token,
    session,
    namespace_uuid,
    namespace_type,
    task_run_time: str = None,
    authorization=None,
) -> tuple[bool, str | None]:
    """
    List "Execute":
    - Queued (waiting): first CSGHub create with this record; do not resubmit same job_id
    - Other terminal/failed states: restart with new flow_id
    """
    try:
        nu, nt = _resolve_job_namespace(
            job,
            namespace_uuid=namespace_uuid,
            namespace_type=namespace_type,
        )
    except ValueError as exc:
        return False, str(exc)
    job.namespace_uuid = nu
    job.namespace_type = nt

    if job.status == responses.JOB_STATUS.PROCESSING.value:
        return False, "任务执行中，无法重复执行"

    try:
        if _is_job_queued_status(job.status):
            if job.csghub_job_id:
                return False, "任务已在等待执行，无需重复提交"
            _submit_existing_job_record(
                session,
                job,
                user_id=user_id,
                user_name=user_name,
                user_token=user_token,
                authorization=authorization,
                task_run_time=task_run_time,
            )
        elif job.status in {
            responses.JOB_STATUS.FINISHED.value,
            responses.JOB_STATUS.FAILED.value,
            responses.JOB_STATUS.CANCELED.value,
            responses.JOB_STATUS.TIMEOUT.value,
        }:
            _restart_job_record(
                session,
                job,
                user_id=user_id,
                user_name=user_name,
                user_token=user_token,
                authorization=authorization,
                task_run_time=task_run_time,
            )
        else:
            return False, f"当前状态不支持执行: {job.status}"

        session.flush()
        session.commit()
        return True, None
    except Exception as e:
        _mark_job_submit_failed(job, e, session)
        session.flush()
        session.commit()
        return False, str(e)


def run_pipline_job_only(
    job,
    user_id,
    user_name,
    user_token,
    session,
    namespace_uuid,
    namespace_type,
    task_run_time: str = None,
    authorization=None,
):
    """Legacy caller; delegates to execute_job."""
    return execute_job(
        job,
        user_id,
        user_name,
        user_token,
        session,
        namespace_uuid,
        namespace_type,
        task_run_time,
        authorization,
    )



def stop_pipline_task(
    db_session: Session,
    job: Job,
    authorization: str | None = None,
):
    """Cancel pipeline/tool task: CSGHub DELETE first, then mark canceled locally."""
    resolved_job_id = resolve_csghub_remote_job_id(
        job.csghub_job_id,
        flow_id=job.flow_id,
        csghub_response_payload=job.csghub_response_payload,
    )
    if resolved_job_id:
        job.csghub_job_id = resolved_job_id
    remote_ok, remote_err = try_cancel_csghub_job(
        namespace_uuid=job.namespace_uuid,
        csghub_job_id=job.csghub_job_id,
        authorization=authorization,
        flow_id=job.flow_id,
        csghub_response_payload=job.csghub_response_payload,
    )
    now = datetime.now()
    job.status = responses.JOB_STATUS.CANCELED.value
    if job.date_finish is None:
        job.date_finish = now
    job.csghub_status = "Canceled"
    db_session.commit()
    logger.info(
        "Job marked canceled | job_id={} | flow_id={} | remote_ok={}",
        job.job_id,
        job.flow_id,
        remote_ok,
    )
    if remote_ok:
        return True, "任务已取消"
    return True, f"任务已取消（CSGHub 停止失败: {remote_err}）"



def parse_yaml_config(yaml_string: str,config):
    fields_to_insert = {
        "project_name": config.project_name,
        "repo_id": config.repo_id,
        "text_keys": config.text_keys,
        "branch": config.branch,
        "np": '1',
        "open_tracer": 'true',
        "trace_num": '1',
    }

    dsl_data = yaml.safe_load(yaml_string)

    dsl_data.update(fields_to_insert)

    new_dsl_data = yaml.dump(dsl_data, sort_keys=False, default_flow_style=False, indent=2, width=float("inf"))
    return convert_raw_to_processed(new_dsl_data)


def delete_job_by_id(id: int, session: Session):
    matched_job = (
        session.query(Job)
        .filter(Job.job_id == id, Job.is_active.is_(True))
        .first()
    )
    if not matched_job:
        return 0
    soft_delete_record(session, matched_job)
    return 1


def search_job(
    query: str,
    user_id,
    session: Session,
    isadmin=False,
    page: int = None,
    page_size: int = None,
    organization_namespace_uuids: list[str] | None = None,
    namespace_uuid: str | None = None,
    job_source: str | None = None,
):
    query = query.strip().replace(" ", "_")
    query_obj = session.query(Job).filter(Job.job_name.contains(query))
    query_obj = apply_task_list_scope(
        query_obj,
        Job,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
    )
    if job_source:
        query_obj = query_obj.filter(Job.job_source == job_source)
    query_obj = query_obj.order_by(Job.job_id.desc())

    search_label = f"job_search/{job_source}" if job_source else "job_search"
    log_task_list_sql(
        query_obj,
        label=search_label,
        session=session,
        user_id=user_id,
        isadmin=isadmin,
        organization_namespace_uuids=organization_namespace_uuids,
        namespace_uuid=namespace_uuid,
        search=query,
        page=page,
        page_size=page_size,
        job_source=job_source,
    )
    if page is not None and page_size is not None:
        total = query_obj.count()
        jobs = query_obj.offset((page - 1) * page_size).limit(page_size).all()
        total_pages = (total + page_size - 1) // page_size
        return jobs, total, total_pages
    else:
        jobs = query_obj.all()
        return jobs
