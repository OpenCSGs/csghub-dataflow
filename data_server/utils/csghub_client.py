import json
import os
import re
from typing import Any
from urllib import error, parse, request

from loguru import logger

from data_server.utils.storage_size import normalize_storage_size, resolve_storage_size


DEFAULT_JOB_API_PATH = "/api/v1/platform/dataflow/{namespace}/jobs"
DEFAULT_JOB_DELETE_API_PATH = "/api/v1/platform/dataflow/{namespace}/jobs/{job_id}"
DEFAULT_JOB_GET_API_PATH = "/api/v1/platform/dataflow/{namespace}/jobs/{job_id}"
DEFAULT_JOB_LOGS_API_PATH = "/api/v1/platform/dataflow/{namespace}/jobs/{job_id}/logs"
# Legacy default (no namespace segment); auto-correct to DEFAULT_JOB_API_PATH if env still points here
_LEGACY_JOB_CREATE_PATH = "/api/v1/dataflow/internal/jobs"
DEFAULT_JOB_SUBTASK_STATUS_API_PATH = "/api/v1/dataflow/internal/jobs/subtasks/test-status"
# DataFlow trace sync path (fixed, not from env; internal for CSGHub-side APIs only)
TRACE_SYNC_API_PATH = "/api/v1/dataflow/trace/sync"
WORKFLOW_SYNC_API_PATH = "/api/v1/dataflow/workflow/sync"
DEFAULT_ENTRYPOINT = "dataflow-dag-main"
TEMPLATE_NAME_PREFIX = "template-job-"


def get_csghub_entrypoint() -> str:
    return os.getenv("CSGHUB_DATAFLOW_ENTRYPOINT", DEFAULT_ENTRYPOINT).strip() or DEFAULT_ENTRYPOINT


def build_container_template_name(job_id: str) -> str:
    normalized = str(job_id or "").strip().lower()
    if not normalized:
        raise ValueError("job_id is required for container template name")
    custom = os.getenv("CSGHUB_DATAFLOW_TEMPLATE_NAME", "").strip()
    if custom:
        return custom.replace("{job_id}", normalized).lower()
    prefix = os.getenv("CSGHUB_DATAFLOW_TEMPLATE_NAME_PREFIX", TEMPLATE_NAME_PREFIX)
    return f"{prefix}{normalized}".lower()


def get_csghub_job_delete_url(namespace: str, csghub_job_id: str) -> str:
    if not namespace or not str(namespace).strip():
        raise ValueError("namespace is required")
    if not csghub_job_id or not str(csghub_job_id).strip():
        raise ValueError("csghub_job_id is required")
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    path = os.getenv(
        "CSGHUB_DATAFLOW_JOB_DELETE_API_PATH",
        DEFAULT_JOB_DELETE_API_PATH,
    ).strip()
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured")
    if not path.startswith("/"):
        path = f"/{path}"
    if "{namespace}" not in path or "{job_id}" not in path:
        raise ValueError(
            "CSGHUB_DATAFLOW_JOB_DELETE_API_PATH 必须包含 {namespace} 与 {job_id} 占位符，"
            f"例如 {DEFAULT_JOB_DELETE_API_PATH}。当前值: {path}"
        )
    encoded_namespace = parse.quote(str(namespace).strip(), safe="")
    encoded_job_id = parse.quote(str(csghub_job_id).strip(), safe="")
    rendered_path = path.replace("{namespace}", encoded_namespace).replace(
        "{job_id}", encoded_job_id
    )
    return parse.urljoin(f"{endpoint}/", rendered_path.lstrip("/"))


def get_csghub_platform_job_url(namespace: str, csghub_job_id: str) -> str:
    """GET platform task details/status: /api/v1/platform/dataflow/{namespace}/jobs/{job_id}"""
    if not namespace or not str(namespace).strip():
        raise ValueError("namespace is required")
    if not csghub_job_id or not str(csghub_job_id).strip():
        raise ValueError("csghub_job_id is required")
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    path = os.getenv("CSGHUB_DATAFLOW_JOB_GET_API_PATH", DEFAULT_JOB_GET_API_PATH).strip()
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured")
    if not path.startswith("/"):
        path = f"/{path}"
    if "{namespace}" not in path or "{job_id}" not in path:
        raise ValueError(
            "CSGHUB_DATAFLOW_JOB_GET_API_PATH 必须包含 {namespace} 与 {job_id} 占位符，"
            f"例如 {DEFAULT_JOB_GET_API_PATH}。当前值: {path}"
        )
    encoded_namespace = parse.quote(str(namespace).strip(), safe="")
    encoded_job_id = parse.quote(str(csghub_job_id).strip(), safe="")
    rendered_path = path.replace("{namespace}", encoded_namespace).replace(
        "{job_id}", encoded_job_id
    )
    return parse.urljoin(f"{endpoint}/", rendered_path.lstrip("/"))


def get_csghub_job_logs_url(
    namespace: str,
    csghub_job_id: str,
    *,
    stream: bool = False,
    dag_task_id: str | None = None,
) -> str:
    """
    CSGHub job logs: without dag_task_id = full main task log; with dag_task_id = DAG subtask log.
    """
    if not namespace or not str(namespace).strip():
        raise ValueError("namespace is required")
    if not csghub_job_id or not str(csghub_job_id).strip():
        raise ValueError("csghub_job_id is required")
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    path = os.getenv("CSGHUB_DATAFLOW_JOB_LOGS_API_PATH", DEFAULT_JOB_LOGS_API_PATH).strip()
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured")
    if not path.startswith("/"):
        path = f"/{path}"
    if "{namespace}" not in path or "{job_id}" not in path:
        raise ValueError(
            "CSGHUB_DATAFLOW_JOB_LOGS_API_PATH 必须包含 {namespace} 与 {job_id} 占位符，"
            f"例如 {DEFAULT_JOB_LOGS_API_PATH}。当前值: {path}"
        )
    encoded_namespace = parse.quote(str(namespace).strip(), safe="")
    encoded_job_id = parse.quote(str(csghub_job_id).strip(), safe="")
    rendered_path = path.replace("{namespace}", encoded_namespace).replace(
        "{job_id}", encoded_job_id
    )
    url = parse.urljoin(f"{endpoint}/", rendered_path.lstrip("/"))
    query: dict[str, str] = {}
    if stream:
        query["stream"] = "true"
    if dag_task_id and str(dag_task_id).strip():
        query["dag_task_id"] = str(dag_task_id).strip()
    if query:
        url = f"{url}?{parse.urlencode(query)}"
    return url


def get_csghub_job_create_url(namespace: str) -> str:
    if not namespace or not str(namespace).strip():
        raise ValueError("namespace is required")
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    path = os.getenv("CSGHUB_DATAFLOW_JOB_API_PATH", DEFAULT_JOB_API_PATH).strip()
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured")
    if not path.startswith("/"):
        path = f"/{path}"
    if "{namespace}" not in path:
        legacy = _LEGACY_JOB_CREATE_PATH.strip()
        if path.rstrip("/") == legacy.rstrip("/") or path.rstrip("/").endswith("/dataflow/internal/jobs"):
            logger.warning(
                "CSGHUB_DATAFLOW_JOB_API_PATH is legacy path without namespace ({}), auto-corrected to {}",
                path,
                DEFAULT_JOB_API_PATH,
            )
            path = DEFAULT_JOB_API_PATH
        else:
            raise ValueError(
                "CSGHUB_DATAFLOW_JOB_API_PATH 必须包含 {namespace} 占位符，"
                f"例如 {DEFAULT_JOB_API_PATH}。当前值: {path}"
            )
    encoded_namespace = parse.quote(str(namespace).strip(), safe="")
    rendered_path = path.replace("{namespace}", encoded_namespace)
    return parse.urljoin(f"{endpoint}/", rendered_path.lstrip("/"))


def get_csghub_job_subtask_status_url(
    *,
    flow_id: str | None = None,
    csghub_job_id: str | None = None,
) -> str:
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").rstrip("/")
    path = os.getenv("CSGHUB_DATAFLOW_JOB_SUBTASK_STATUS_API_PATH", DEFAULT_JOB_SUBTASK_STATUS_API_PATH).strip()
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured")
    if not path.startswith("/"):
        path = f"/{path}"

    encoded_flow_id = parse.quote(str(flow_id or ""), safe="")
    encoded_job_id = parse.quote(str(csghub_job_id or ""), safe="")
    rendered_path = path.replace("{flow_id}", encoded_flow_id).replace("{job_id}", encoded_job_id)
    url = parse.urljoin(f"{endpoint}/", rendered_path.lstrip("/"))

    query_params = {}
    if "{flow_id}" not in path and flow_id:
        query_params["flow_id"] = flow_id
    if "{job_id}" not in path and csghub_job_id:
        query_params["job_id"] = csghub_job_id
    if query_params:
        url = f"{url}?{parse.urlencode(query_params)}"
    return url


def _get_http_timeout() -> int:
    try:
        return int(os.getenv("CSGHUB_HTTP_TIMEOUT", "30"))
    except ValueError:
        return 30


def _build_csghub_headers(
    user_token: str | None = None,
) -> dict[str, str]:
    """CSGHub API headers: Authorization = Bearer <user_token> (access token); User-Token for git ops."""
    headers = {
        "Content-Type": "application/json",
    }
    if user_token and str(user_token).strip():
        token = str(user_token).strip()
        headers["Authorization"] = token if token.lower().startswith("bearer ") else f"Bearer {token}"
        headers["User-Token"] = token
    return headers


def _ensure_bearer_authorization(authorization: str | None) -> str | None:
    if not authorization or not str(authorization).strip():
        return None
    auth = str(authorization).strip()
    if not auth.lower().startswith("bearer "):
        auth = f"Bearer {auth}"
    return auth


def _build_api_bearer_headers(user_token: str | None) -> dict[str, str]:
    """Bearer access token for CSGHub/DataFlow HTTP (e.g. trace sync, platform query)."""
    headers = {"Content-Type": "application/json"}
    auth = _ensure_bearer_authorization(user_token)
    if auth:
        headers["Authorization"] = auth
    return headers


def _load_json_response(resp) -> dict[str, Any]:
    response_text = resp.read().decode("utf-8")
    if not response_text:
        return {}
    return json.loads(response_text)


def _parse_extra_config(extra_config: Any) -> dict[str, Any]:
    if extra_config is None:
        return {}
    if isinstance(extra_config, dict):
        return extra_config
    if isinstance(extra_config, str):
        try:
            parsed = json.loads(extra_config)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def collect_repo_ids(
    *repo_id_candidates: str | None,
    extra_config: Any = None,
) -> list[str]:
    """Collect repo_id for task creation (dedupe, preserve order)."""
    repo_ids: list[str] = []
    seen: set[str] = set()

    def _add(value: str | None) -> None:
        if value is None:
            return
        normalized = str(value).strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        repo_ids.append(normalized)

    for candidate in repo_id_candidates:
        _add(candidate)

    extra = _parse_extra_config(extra_config)
    for key in (
        "repo_id",
        "re_id",
        "csg_hub_repo_id",
        "to_csg_hub_repo_id",
        "from_csg_hub_repo_id",
        "export_repo_id",
        "csg_hub_dataset_id",
    ):
        _add(extra.get(key))

    return repo_ids


# Env vars injected into Pod when submitting Argo task to CSGHub (no .env in image; use template.env)
_POD_RUNTIME_ENV_KEYS = (
    "CSGHUB_ENDPOINT",
    "RAY_ENABLE",
    "RAY_ADDRESS",
    "RAY_LOG_DIR",
    "ENABLE_OPENTELEMETRY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "OPENAI_API_VERSION",
    "AZURE_MODEL",
)


def get_dataflow_trace_sync_url() -> str:
    """
    Full URL for Pod trace sync: CSGHUB_ENDPOINT + TRACE_SYNC_API_PATH.
    Written to template.env.DATAFLOW_TRACE_SYNC_URL when creating Argo task.
    """
    explicit = os.getenv("DATAFLOW_TRACE_SYNC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").strip().rstrip("/")
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured for trace sync URL")
    return f"{endpoint}{TRACE_SYNC_API_PATH}"


def get_dataflow_workflow_sync_url() -> str:
    """
    Full URL for Pod workflow step/terminal sync: CSGHUB_ENDPOINT + WORKFLOW_SYNC_API_PATH.
    Written to template.env.DATAFLOW_WORKFLOW_SYNC_URL when creating Argo task.
    """
    explicit = os.getenv("DATAFLOW_WORKFLOW_SYNC_URL", "").strip().rstrip("/")
    if explicit:
        return explicit
    endpoint = os.getenv("CSGHUB_ENDPOINT", "").strip().rstrip("/")
    if not endpoint:
        raise ValueError("CSGHUB_ENDPOINT is not configured for workflow sync URL")
    return f"{endpoint}{WORKFLOW_SYNC_API_PATH}"


def get_pod_data_dir() -> str:
    """
    Pod work directory configured on DataFlow API.
    Written to template.env.DATA_DIR and passed as payload.data_dir to CSGHub;
    CSGHub must set workflow-data volume mountPath to the same path.
    """
    return (
        os.getenv("CSGHUB_DATAFLOW_DATA_DIR", "").strip()
        or os.getenv("DATA_DIR", "").strip()
        or "/dataflow_data"
    ).rstrip("/")


def _build_pod_runtime_env() -> dict[str, str]:
    """
    Build Argo Pod env from DataFlow API service environment (includes DATA_DIR).
    """
    env: dict[str, str] = {}

    endpoint = os.getenv("CSGHUB_ENDPOINT", "").strip().rstrip("/")
    if endpoint:
        env["CSGHUB_ENDPOINT"] = endpoint

    env["DATA_DIR"] = get_pod_data_dir()

    ray_enable = os.getenv("RAY_ENABLE") or os.getenv("CSGHUB_DATAFLOW_RAY_ENABLE", "False")
    env["RAY_ENABLE"] = str(ray_enable).strip() or "False"

    # Format conversion PDF (MinerU); defaults match .env / formatify_helpers
    env["MINERU_API_URL"] = (
        os.getenv("MINERU_API_URL", "").strip() or "http://111.4.242.20:30000"
    )
    env["MINERU_BACKEND"] = (
        os.getenv("MINERU_BACKEND", "").strip() or "http-client"
    )

    for key in _POD_RUNTIME_ENV_KEYS:
        if key in ("CSGHUB_ENDPOINT", "RAY_ENABLE"):
            continue
        value = os.getenv(key)
        if value is not None and str(value).strip() != "":
            env[key] = str(value).strip()

    try:
        env["DATAFLOW_TRACE_SYNC_URL"] = get_dataflow_trace_sync_url()
    except ValueError as exc:
        logger.warning("Pod env missing DATAFLOW_TRACE_SYNC_URL: {}", exc)

    try:
        env["DATAFLOW_WORKFLOW_SYNC_URL"] = get_dataflow_workflow_sync_url()
    except ValueError as exc:
        logger.warning("Pod env missing DATAFLOW_WORKFLOW_SYNC_URL: {}", exc)

    callback_token = os.getenv("CSGHUB_DATAFLOW_CALLBACK_TOKEN", "").strip()
    if callback_token:
        env["DATAFLOW_INTERNAL_TOKEN"] = callback_token

    return env


def _default_template_env() -> dict[str, str]:
    return _build_pod_runtime_env()


def _merge_template_env(extra: Any) -> dict[str, str]:
    merged = _default_template_env()
    if isinstance(extra, list):
        for item in extra:
            if isinstance(item, dict) and item.get("name"):
                merged[str(item["name"])] = str(item.get("value", ""))
    elif isinstance(extra, dict):
        for name, value in extra.items():
            merged[str(name)] = str(value)
    return merged


def _build_template_definition(template_name: str) -> dict[str, Any]:
    template: dict[str, Any] = {
        "name": template_name,
        "parameters": ["task_type", "task_params"],
        "command": ["python"],
        "args": [
            "run_dataflow_task.py",
            "--task-type",
            "{{inputs.parameters.task_type}}",
            "--task-params",
            "{{inputs.parameters.task_params}}",
        ],
        "env": _default_template_env(),
    }
    # CSGHub prepends registry prefix (e.g. 192.168.2.98:8140/); pass in-repo path only
    image = os.getenv(
        "CSGHUB_DATAFLOW_TEMPLATE_IMAGE",
        "opencsg_public/dataflow:argo-latest",
    )
    if image:
        template["image"] = image
    env_json = os.getenv("CSGHUB_DATAFLOW_TEMPLATE_ENV_JSON", "").strip()
    if env_json:
        try:
            template["env"] = _merge_template_env(json.loads(env_json))
        except json.JSONDecodeError:
            logger.warning("CSGHUB_DATAFLOW_TEMPLATE_ENV_JSON is not valid JSON, skip env")
    if not template["env"].get("CSGHUB_ENDPOINT"):
        logger.warning(
            "Pod template env missing CSGHUB_ENDPOINT; ingester will fall back to https://hub.opencsg.com. "
            "Set CSGHUB_ENDPOINT on the DataFlow API service (e.g. http://192.168.2.120:8120)."
        )
    else:
        logger.debug(
            "Pod template env | CSGHUB_ENDPOINT={} | DATA_DIR={}",
            template["env"].get("CSGHUB_ENDPOINT"),
            template["env"].get("DATA_DIR"),
        )
    return template


def build_job_flow_id(job_source: str, biz_id: int) -> str:
    prefix_mapping = {
        "datasource": "AA",
        "formatify": "AB",
        "pipeline": "AC",
        "tool": "AD",
    }
    prefix = prefix_mapping.get(job_source, "DF")
    return f"{prefix}{biz_id}"


def build_job_flow_id_restart(job_source: str, biz_id: int) -> str:
    """Generate flow_id for restart to avoid CSGHub job_id collision."""
    import time

    base = build_job_flow_id(job_source, biz_id)
    return f"{base}R{int(time.time())}"


# Temporary debug: remove after frontend storage config integration
_DEBUG_STORAGE_SIZE = "4Gi"


def _optional_env(key: str) -> str | None:
    value = os.getenv(key, "").strip()
    return value or None


def build_csghub_payload(
    *,
    job_id: str,
    job_name: str,
    dag_tasks: list[dict[str, Any]],
    entrypoint: str | None = None,
    job_desc: str | None = None,
    resource_id: int | None = None,
    resource_name: str | None = None,
    repo_ids: list[str] | None = None,
    storage_size: str | None = None,
) -> dict[str, Any]:
    template_name = build_container_template_name(job_id)
    template = _build_template_definition(template_name)
    resolved_dag_tasks = [
        {**task, "template": template_name}
        for task in dag_tasks
    ]
    payload: dict[str, Any] = {
        "job_id": job_id,
        "job_name": job_name,
        "job_desc": job_desc or job_name,
        "entrypoint": entrypoint or get_csghub_entrypoint(),
        "data_dir": get_pod_data_dir(),
        "template": template,
        "dag_tasks": resolved_dag_tasks,
    }

    resolved_storage_size = resolve_storage_size(
        storage_size or _optional_env("CSGHUB_STORAGE_SIZE") or _DEBUG_STORAGE_SIZE
    )
    payload["storage_size"] = normalize_storage_size(resolved_storage_size)

    storage_access_mode = _optional_env("CSGHUB_STORAGE_ACCESS_MODE")
    if storage_access_mode:
        payload["storage_access_mode"] = storage_access_mode

    storage_class_name = _optional_env("CSGHUB_STORAGE_CLASS_NAME")
    if storage_class_name:
        payload["storage_class_name"] = storage_class_name

    if resource_id is not None:
        payload["resource_id"] = resource_id

    if resource_name and str(resource_name).strip():
        payload["resource_name"] = str(resource_name).strip()

    if repo_ids:
        payload["repo_ids"] = repo_ids

    return payload


def _headers_for_log(headers: dict[str, str]) -> dict[str, str]:
    """For logging: redact Authorization / User-Token values."""
    out = dict(headers)
    for key in ("Authorization", "User-Token"):
        if key in out and out[key]:
            v = out[key]
            out[key] = f"{v[:8]}...<len={len(v)}>" if len(v) > 12 else "***"
    return out


def _payload_str_for_log(payload: dict[str, Any], max_len: int = 48000) -> str:
    s = json.dumps(payload, ensure_ascii=False)
    if len(s) > max_len:
        return s[:max_len] + f"... [truncated, total {len(s)} chars]"
    return s


def submit_job_to_csghub(
    payload: dict[str, Any],
    namespace: str,
    user_token: str | None = None,
) -> dict[str, Any]:
    url = get_csghub_job_create_url(namespace)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = _build_csghub_headers(user_token=user_token)

    logger.info(
        "CSGHub create job request | url={url} | namespace={ns} | headers={hdr} | payload_json={payload}",
        url=url,
        ns=namespace,
        hdr=_headers_for_log(headers),
        payload=_payload_str_for_log(payload),
    )

    req = request.Request(url, data=body, headers=headers, method="POST")
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            return _load_json_response(resp)
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        logger.error(
            "Failed to submit job to CSGHub | status={code} | url={url} | response_body={body} | request_payload_json={payload}",
            code=exc.code,
            url=url,
            body=response_text or "(empty)",
            payload=_payload_str_for_log(payload),
        )
        raise RuntimeError(f"CSGHub request failed: {exc.code} {response_text}") from exc
    except error.URLError as exc:
        logger.error(
            "Failed to submit job to CSGHub | url={url} | reason={reason} | request_payload_json={payload}",
            url=url,
            reason=exc.reason,
            payload=_payload_str_for_log(payload),
        )
        raise RuntimeError(f"CSGHub request failed: {exc.reason}") from exc


_CSGHUB_OK_MSGS = frozenset({"OK", "SUCCESS", "CREATED", "SUCCEEDED"})
_CSGHUB_FAILED_STATUS_KEYS = frozenset({"FAILED", "FAIL", "ERROR"})
_CSGHUB_SUCCESS_STATUS_KEYS = frozenset({
    "SUCCESS",
    "SUCCEEDED",
    "COMPLETED",
    "FINISHED",
    "DONE",
    "CREATED",
    "SUBMITTED",
    "PENDING",
    "QUEUED",
    "WAITING",
    "RUNNING",
    "PROCESSING",
    "EXECUTING",
    "IN_PROGRESS",
})


def _status_key(status: str | None) -> str:
    return str(status or "").strip().replace("-", "_").replace(" ", "_").upper()


_FLOW_ID_PATTERN = re.compile(r"^(AA|AB|AC|AD|DF)\d+$", re.IGNORECASE)


def _looks_like_flow_id(value: str | None) -> bool:
    return bool(_FLOW_ID_PATTERN.match(str(value or "").strip()))


def _extract_argo_task_id_from_payload(payload: Any) -> str | None:
    if payload is None:
        return None
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return None
    if not isinstance(payload, dict):
        return None
    nested = payload.get("data")
    body: dict[str, Any] = {**payload, **nested} if isinstance(nested, dict) else payload
    for key in ("argo_task_id", "argoTaskId"):
        value = body.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return None


def resolve_csghub_remote_job_id(
    csghub_job_id: str | None,
    *,
    flow_id: str | None = None,
    csghub_response_payload: Any = None,
) -> str | None:
    """
    Job id to use for CSGHub remote ops (DELETE/status query).
    Create response job_id is often flow_id (e.g. AC82); use argo_task_id (e.g. dffmwvwwgvpq80).
    """
    stored = str(csghub_job_id or "").strip()
    fid = str(flow_id or "").strip()
    if stored and not (fid and stored == fid) and not _looks_like_flow_id(stored):
        logger.info(
            "CSGHub resolve remote job id | use stored csghub_job_id={jid}",
            jid=stored,
        )
        return stored
    recovered = _extract_argo_task_id_from_payload(csghub_response_payload)
    if recovered:
        logger.info(
            "CSGHub resolve remote job id | use argo_task_id from payload={jid} | "
            "stored={stored} | flow_id={fid}",
            jid=recovered,
            stored=stored or "(empty)",
            fid=fid or "(empty)",
        )
        return recovered
    logger.info(
        "CSGHub resolve remote job id | fallback stored={stored} | flow_id={fid}",
        stored=stored or "(empty)",
        fid=fid or "(empty)",
    )
    return stored or None


def _extract_csghub_job_id(body: dict[str, Any]) -> Any:
    for key in ("argo_task_id", "argoTaskId"):
        value = body.get(key)
        if value is not None and str(value).strip() != "":
            return value
    for key in ("csghub_job_id", "workflow_id", "uuid"):
        value = body.get(key)
        if value is not None and str(value).strip() != "":
            return value
    for key in ("job_id", "jobId"):
        value = body.get(key)
        if value is not None and str(value).strip() != "":
            normalized = str(value).strip()
            if not _looks_like_flow_id(normalized):
                return normalized
    value = body.get("id")
    if value is not None and str(value).strip() != "":
        normalized = str(value).strip()
        if not normalized.isdigit() and not _looks_like_flow_id(normalized):
            return normalized
    return None


def parse_csghub_job_create_response(response: Any) -> dict[str, Any]:
    """
    Parse CSGHub create-task response; supports {msg,data:{argo_task_id,job_id,status}} and flat shape.
    csghub_job_id prefers argo_task_id (for DELETE); job_id is often flow_id (e.g. AC82).
    Returns job_id, status; error is non-empty string on failure.
    """
    if not isinstance(response, dict):
        return {"job_id": None, "status": None, "error": "invalid CSGHub response"}

    nested = response.get("data")
    body: dict[str, Any] = dict(response)
    if isinstance(nested, dict):
        body = {**response, **nested}

    job_id = _extract_csghub_job_id(body)
    status = body.get("status")
    msg = response.get("msg") or response.get("message") or body.get("msg") or ""
    error = body.get("error") or body.get("err") or response.get("error")

    msg_key = str(msg).strip().upper()
    status_key = _status_key(status)

    if status_key in _CSGHUB_FAILED_STATUS_KEYS:
        error = error or f"CSGHub status: {status}"
    elif msg and msg_key not in _CSGHUB_OK_MSGS:
        # msg=Created etc. mean success; not an error if job_id or success status present
        if not job_id and status_key not in _CSGHUB_SUCCESS_STATUS_KEYS:
            error = error or str(msg)

    if not job_id and not error:
        error = "CSGHub response missing job_id"

    return {
        "job_id": str(job_id) if job_id is not None else None,
        "status": status,
        "error": str(error) if error else None,
    }


def ensure_csghub_job_create_success(response: Any) -> dict[str, Any]:
    """Raise RuntimeError when create-task response validation fails."""
    parsed = parse_csghub_job_create_response(response)
    if parsed.get("error"):
        raise RuntimeError(parsed["error"])
    return parsed


def _parse_csghub_logs_response_body(body: str, content_type: str | None) -> str:
    if not body:
        logger.warning(
            "CSGHub logs response body is empty | content_type={ct}",
            ct=content_type or "(none)",
        )
        return ""
    if content_type and "json" in content_type.lower():
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.warning(
                "CSGHub logs response JSON parse failed, return raw body | "
                "content_type={ct} | body_preview={preview}",
                ct=content_type,
                preview=body[:500],
            )
            return body
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("data", "logs", "log", "content", "message", "text", "result"):
                value = data.get(key)
                if isinstance(value, str):
                    return value
                if isinstance(value, list):
                    return "\n".join(
                        line if isinstance(line, str) else json.dumps(line, ensure_ascii=False)
                        for line in value
                    )
            logger.warning(
                "CSGHub logs JSON dict has no known log field | keys={keys} | "
                "body_preview={preview}",
                keys=list(data.keys()),
                preview=body[:500],
            )
            return json.dumps(data, ensure_ascii=False, indent=2)
        if isinstance(data, list):
            return "\n".join(
                item if isinstance(item, str) else json.dumps(item, ensure_ascii=False)
                for item in data
            )
        logger.warning(
            "CSGHub logs JSON unexpected type | type={typ} | body_preview={preview}",
            typ=type(data).__name__,
            preview=body[:500],
        )
    return body


def fetch_csghub_job_logs(
    *,
    namespace: str,
    csghub_job_id: str,
    user_token: str | None = None,
    stream: bool = False,
    dag_task_id: str | None = None,
) -> str:
    """
    Fetch task logs from CSGHub. Empty dag_task_id = main task log; otherwise subtask log.
    """
    url = get_csghub_job_logs_url(
        namespace,
        csghub_job_id,
        stream=stream,
        dag_task_id=dag_task_id,
    )
    headers = _build_csghub_headers(user_token=user_token)
    req = request.Request(url, headers=headers, method="GET")
    has_user_token = bool(str(user_token or "").strip())
    logger.info(
        "CSGHub fetch job logs request | url={url} | namespace={ns} | job_id={jid} | "
        "dag_task_id={dag} | stream={stream} | has_user_token={ut}",
        url=url,
        ns=namespace,
        jid=csghub_job_id,
        dag=dag_task_id or "(main)",
        stream=stream,
        ut=has_user_token,
    )
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            content_type = resp.headers.get("Content-Type")
            status = getattr(resp, "status", None) or resp.getcode()
            parsed = _parse_csghub_logs_response_body(raw, content_type)
            logger.info(
                "CSGHub fetch job logs response | status={status} | content_type={ct} | "
                "raw_len={raw_len} | parsed_len={parsed_len} | raw_preview={preview}",
                status=status,
                ct=content_type or "(none)",
                raw_len=len(raw),
                parsed_len=len(parsed or ""),
                preview=(raw[:300] if raw else "(empty)"),
            )
            if raw and not parsed:
                logger.warning(
                    "CSGHub logs parsed empty but raw body non-empty | url={url} | "
                    "raw_preview={preview}",
                    url=url,
                    preview=raw[:500],
                )
            return parsed
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        logger.error(
            "Failed to fetch job logs from CSGHub | status={code} | url={url} | body={body}",
            code=exc.code,
            url=url,
            body=response_text or "(empty)",
        )
        raise RuntimeError(f"CSGHub logs query failed: {exc.code} {response_text}") from exc
    except error.URLError as exc:
        logger.error(
            "Failed to fetch job logs from CSGHub | url={url} | reason={reason}",
            url=url,
            reason=exc.reason,
        )
        raise RuntimeError(f"CSGHub logs query failed: {exc.reason}") from exc


def parse_platform_dag_tasks(dag_tasks_raw: Any) -> list[dict[str, Any]]:
    """
    Parse dag_tasks from CSGHub platform GET job (JSON string or dict).
    Keys are Argo DAG task_id (e.g. ac9401); values are name/status/start_time/end_time.
    """
    if dag_tasks_raw is None:
        return []
    if isinstance(dag_tasks_raw, str):
        text = dag_tasks_raw.strip()
        if not text:
            return []
        try:
            dag_tasks_raw = json.loads(text)
        except json.JSONDecodeError:
            return []
    if not isinstance(dag_tasks_raw, dict):
        return []

    items: list[dict[str, Any]] = []
    for task_id, info in dag_tasks_raw.items():
        if not isinstance(info, dict):
            continue
        items.append({
            "task_id": str(task_id),
            "task_name": str(info.get("name") or task_id),
            "status": info.get("status") or info.get("state") or info.get("phase"),
            "start_time": info.get("start_time") or info.get("started_at"),
            "end_time": info.get("end_time") or info.get("finished_at"),
            "message": info.get("message") or info.get("error_message"),
        })
    return items


def parse_platform_job_query_response(response: Any) -> dict[str, Any]:
    """
    Parse platform GET job response: { msg, data: { status, dag_tasks, argo_task_id, ... } }.
    """
    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError as exc:
            raise ValueError("platform job response is not valid JSON") from exc
    if not isinstance(response, dict):
        raise ValueError("invalid platform job response")

    nested = response.get("data")
    body: dict[str, Any] = {**response, **nested} if isinstance(nested, dict) else dict(response)

    status = body.get("status") or body.get("job_status") or body.get("state")
    if not status:
        raise ValueError("platform job response missing status")

    subtask_items = parse_platform_dag_tasks(body.get("dag_tasks"))
    return {
        "status": str(status),
        "message": body.get("message"),
        "argo_task_id": body.get("argo_task_id"),
        "csghub_job_id": body.get("argo_task_id") or body.get("job_id"),
        "job_name": body.get("job_name"),
        "subtask_items": subtask_items,
        "raw": body,
    }


def query_platform_job_from_csghub(
    *,
    namespace: str,
    csghub_job_id: str,
    user_token: str | None = None,
) -> dict[str, Any]:
    """GET /api/v1/platform/dataflow/{namespace}/jobs/{job_id}; return raw JSON."""
    auth = _ensure_bearer_authorization(user_token)
    if not auth:
        raise ValueError("Authorization (Bearer token) is required for platform job query")

    url = get_csghub_platform_job_url(namespace, csghub_job_id)
    headers = _build_api_bearer_headers(auth)
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            return _load_json_response(resp)
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        logger.error(
            "Failed to query platform job from CSGHub | status={code} | url={url} | body={body}",
            code=exc.code,
            url=url,
            body=response_text,
        )
        raise RuntimeError(f"CSGHub platform job query failed: {exc.code} {response_text}") from exc
    except error.URLError as exc:
        logger.error(
            "Failed to query platform job from CSGHub | url={url} | reason={reason}",
            url=url,
            reason=exc.reason,
        )
        raise RuntimeError(f"CSGHub platform job query failed: {exc.reason}") from exc


def fetch_platform_job_status(
    *,
    namespace: str,
    csghub_job_id: str | None = None,
    flow_id: str | None = None,
    user_token: str | None = None,
    csghub_response_payload: Any = None,
) -> dict[str, Any]:
    """
    GET platform job details; parse main status and dag_tasks subtask list.
    Returns parse_platform_job_query_response fields plus raw_response.
    """
    remote_job_id = resolve_csghub_remote_job_id(
        csghub_job_id,
        flow_id=flow_id,
        csghub_response_payload=csghub_response_payload,
    )
    if not namespace or not str(namespace).strip():
        raise ValueError("namespace 不能为空")
    if not remote_job_id:
        raise ValueError("无法解析 CSGHub 远端 job_id（argo_task_id）")

    auth = _ensure_bearer_authorization(user_token)
    if not auth:
        raise ValueError("查询任务状态需要 Authorization: Bearer")

    raw = query_platform_job_from_csghub(
        namespace=str(namespace).strip(),
        csghub_job_id=remote_job_id,
        user_token=auth,
    )
    parsed = parse_platform_job_query_response(raw)
    return {**parsed, "raw_response": raw}


def delete_job_from_csghub(
    *,
    namespace: str,
    csghub_job_id: str,
    user_token: str | None = None,
) -> dict[str, Any]:
    """
    Call CSGHub DELETE /api/v1/platform/dataflow/{namespace}/jobs/{job_id} to cancel remote task.
    Request must include Authorization: Bearer <token>.
    """
    auth = _ensure_bearer_authorization(user_token)
    if not auth:
        raise ValueError("Authorization (Bearer token) is required for CSGHub job delete")

    url = get_csghub_job_delete_url(namespace, csghub_job_id)
    headers = _build_api_bearer_headers(auth)

    logger.info(
        "CSGHub delete job request | url={url} | namespace={ns} | job_id={jid} | headers={hdr}",
        url=url,
        ns=namespace,
        jid=csghub_job_id,
        hdr=_headers_for_log(headers),
    )

    req = request.Request(url, headers=headers, method="DELETE")
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            if resp.status in (204, 205):
                return {}
            return _load_json_response(resp)
    except error.HTTPError as exc:
        if exc.code == 404:
            logger.warning(
                "CSGHub job already deleted or not found | url={url} | status=404",
                url=url,
            )
            return {"status": "not_found"}
        response_text = exc.read().decode("utf-8", errors="ignore")
        logger.error(
            "Failed to delete job from CSGHub | status={code} | url={url} | response_body={body}",
            code=exc.code,
            url=url,
            body=response_text or "(empty)",
        )
        raise RuntimeError(f"CSGHub delete job failed: {exc.code} {response_text}") from exc
    except error.URLError as exc:
        logger.error(
            "Failed to delete job from CSGHub | url={url} | reason={reason}",
            url=url,
            reason=exc.reason,
        )
        raise RuntimeError(f"CSGHub delete job failed: {exc.reason}") from exc


def try_cancel_csghub_job(
    *,
    namespace_uuid: str | None,
    csghub_job_id: str | None,
    user_token: str | None,
    flow_id: str | None = None,
    csghub_response_payload: Any = None,
) -> tuple[bool, str | None]:
    """
    Best-effort CSGHub delete job API call. Returns (remote_ok, warning).
    When remote_ok=False, warning is failure reason; when skipped, remote_ok=True and warning may be informational.
    """
    ns = str(namespace_uuid or "").strip()
    jid = resolve_csghub_remote_job_id(
        csghub_job_id,
        flow_id=flow_id,
        csghub_response_payload=csghub_response_payload,
    ) or ""
    if not ns or not jid:
        logger.warning(
            "Skip CSGHub job delete: missing namespace or csghub_job_id | flow_id={}",
            flow_id,
        )
        return True, None
    if not _ensure_bearer_authorization(user_token):
        logger.warning(
            "Skip CSGHub job delete: missing Authorization | flow_id={} | csghub_job_id={}",
            flow_id,
            jid,
        )
        return True, None
    try:
        delete_job_from_csghub(
            namespace=ns,
            csghub_job_id=jid,
            user_token=user_token,
        )
        logger.info(
            "CSGHub job deleted | flow_id={} | namespace={} | csghub_job_id={}",
            flow_id,
            ns,
            jid,
        )
        return True, None
    except Exception as exc:
        logger.error(
            "CSGHub job delete failed | flow_id={} | namespace={} | csghub_job_id={} | error={}",
            flow_id,
            ns,
            jid,
            exc,
        )
        return False, str(exc)


def query_job_subtasks_status_from_csghub(
    *,
    flow_id: str | None = None,
    csghub_job_id: str | None = None,
    user_token: str | None = None,
) -> dict[str, Any]:
    if not flow_id and not csghub_job_id:
        raise ValueError("flow_id and csghub_job_id cannot both be empty")

    url = get_csghub_job_subtask_status_url(flow_id=flow_id, csghub_job_id=csghub_job_id)
    headers = _build_csghub_headers(user_token=user_token)
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=_get_http_timeout()) as resp:
            return _load_json_response(resp)
    except error.HTTPError as exc:
        response_text = exc.read().decode("utf-8", errors="ignore")
        logger.error(f"Failed to query job subtasks status from CSGHub, status={exc.code}, body={response_text}")
        raise RuntimeError(f"CSGHub subtask status query failed: {exc.code} {response_text}") from exc
    except error.URLError as exc:
        logger.error(f"Failed to query job subtasks status from CSGHub, reason={exc.reason}")
        raise RuntimeError(f"CSGHub subtask status query failed: {exc.reason}") from exc
