# -*- coding: utf-8 -*-
import json
from kubernetes import client, config, watch
import os
from typing import Callable
import threading
import time
from typing import Dict, Optional
from kubernetes.client.rest import ApiException

from loguru import logger

dataflow_image = os.getenv("WORKFLOW_DATAFLOW_IMAGE", "dataworkflow:latest")
imagePullPolicy = os.getenv("WORKFLOW_IMAGE_PULL_POLICY", "IfNotPresent")

DATAFLOW_LABEL = "app.kubernetes.io/managed-by"
DATAFLOW_LABEL_VALUE = "workflow-dataflow"


def get_workflow_strategy_config() -> Dict:
    """
    Get Workflow TTL and Pod GC strategy configuration
    Returns:
        Dict: Configuration dictionary containing ttlStrategy and podGCStrategy
    """
    return {
        "ttlStrategy": {
            "secondsAfterCompletion": int(os.getenv("WORKFLOW_TTL_AFTER_COMPLETION", "3600")),
            "secondsAfterSuccess": int(os.getenv("WORKFLOW_TTL_AFTER_SUCCESS", "30")),
            "secondsAfterFailure": int(os.getenv("WORKFLOW_TTL_AFTER_FAILURE", "3600"))
        },
        "podGCStrategy": {
            "podGCStrategy": os.getenv("WORKFLOW_POD_GC_STRATEGY", "OnWorkflowCompletion")
        }
    }

def get_resource_config() -> Optional[Dict]:
    """
    Generate Kubernetes resource limit configuration from environment variables
    Format example:
        resources={
            "requests": {"cpu": "500m", "memory": "1Gi"},
            "limits": {"cpu": "1000m", "memory": "2Gi"}
        }
    """
    config = {}
    
    # CPU configuration
    if cpu_request := os.environ.get("WORKFLOW_CPU_REQUEST"):
        config.setdefault("requests", {})["cpu"] = cpu_request
    if cpu_limit := os.environ.get("WORKFLOW_CPU_LIMIT"):
        config.setdefault("limits", {})["cpu"] = cpu_limit
        
    # Memory configuration
    if mem_request := os.environ.get("WORKFLOW_MEMORY_REQUEST"):
        config.setdefault("requests", {})["memory"] = mem_request
    if mem_limit := os.environ.get("WORKFLOW_MEMORY_LIMIT"):
        config.setdefault("limits", {})["memory"] = mem_limit
    
    return config or None

def get_env_vars():
    env_vars = [
        {"name": "CSGHUB_ENDPOINT", "value": os.getenv("CSGHUB_ENDPOINT")},
        {"name": "RAY_ENABLE", "value": os.getenv("RAY_ENABLE", "False")},
        {"name": "RAY_ADDRESS", "value": os.getenv("RAY_ADDRESS", "auto")},
        {"name": "RAY_LOG_DIR", "value": os.getenv("RAY_LOG_DIR")},
        {"name": "AZURE_OPENAI_ENDPOINT", "value": os.getenv("AZURE_OPENAI_ENDPOINT")},
        {"name": "AZURE_OPENAI_API_KEY", "value": os.getenv("AZURE_OPENAI_API_KEY")},
        {"name": "OPENAI_API_VERSION", "value": os.getenv("OPENAI_API_VERSION")},
        {"name": "ENABLE_OPENTELEMETRY", "value": os.getenv("ENABLE_OPENTELEMETRY", "False")},
    ]
    return env_vars

def create_argo_workflow(namespace: str, job_id, job_conf, user_id, user_name, user_token, job_type, uuid_str):
    """
    Create Argo Workflow
    
    Args:
        namespace (str): Kubernetes namespace
        job_conf: Job configuration
        user_id (str): User ID
        user_name (str): Username
        user_token (str): User token
        ray_enable (bool): Whether to enable Ray
        job_type (str): Job type, possible values are "pipeline" or "tool"
    """
    config.load_kube_config()

    api_client = client.ApiClient()
    custom_object_api = client.CustomObjectsApi(api_client)

    cmd_args = [
        "/dataflow/JobWorkflowExecutor.py",
        job_type, 
        "--config", job_conf,
        "--user-id", str(user_id),
        "--user-name", user_name,
        "--user-token", user_token,
    ]
    
    env_vars = get_env_vars()

    labels = {
        DATAFLOW_LABEL: DATAFLOW_LABEL_VALUE,
        "workflow-type": job_type,
        "dataflow-job-id": str(job_id),
    }


    workflow_manifest = {
        "apiVersion": "argoproj.io/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "generateName": f"dataflow-{job_type}-",
            "labels": labels,
        },
        "spec": {
            **get_workflow_strategy_config(), 
            "serviceAccountName": os.getenv("WORKFLOW_SERVICE_ACCOUNT", "dataflow-sa"),
            "entrypoint": "main",
            "volumes": [
                {
                    "name": "data-volume",
                    "persistentVolumeClaim": {
                        "claimName": os.getenv("WORKFLOW_DATA_VOLUME_CLAIM_NAME", "dataflow-pvc")
                    }
                }
            ],
            "templates": [
                {
                    "name": "main",
                    "container": {
                        "image": dataflow_image,
                        "imagePullPolicy": imagePullPolicy,
                        "command": ["python3"],
                        "args": cmd_args,
                        "env": env_vars,
                        "resources": get_resource_config(),
                        "volumeMounts": [
                            {
                                "name": "data-volume",
                                "mountPath": os.getenv("DATA_DIR", "/tmp/dataflow/")
                            }
                        ],
                        "securityContext": {
                            "runAsUser": int(os.getenv("WORKFLOW_RUN_AS_USER", "1000")),
                            "runAsGroup": int(os.getenv("WORKFLOW_RUN_AS_GROUP", "1000"))
                        }
                    },
                }
            ]
        }
    }

    group = "argoproj.io"
    version = "v1alpha1"
    plural = "workflows"

    try:
        response = custom_object_api.create_namespaced_custom_object(
            group=group,
            version=version,
            namespace=namespace,
            plural=plural,
            body=workflow_manifest
        )
        logger.info(f"Workflow created successfully! Name: {response['metadata']['name']}")
        return response
    except client.exceptions.ApiException as e:
        print(f"Error creating workflow: {e}")
        return None

def watch_dataflow_resources(namespace: str, callback: Callable[[str, str, dict, str], None], stop_event: threading.Event):
    """
    Watch all resources managed by dataflow
    
    Args:
        namespace: Namespace
        callback: Callback function that receives parameters (resource_type, event_type, resource)
                 resource_type: "workflow" or "pod"
                 event_type: "ADDED", "MODIFIED", "DELETED"
                 resource: Resource object
        stop_event: Event used to stop watching
    """
    logger.info("Watching dataflow resources")
    config.load_kube_config()
    custom_object_api = client.CustomObjectsApi()
    w = watch.Watch()

    def watch_workflows():
        while not stop_event.is_set():
            try:
                stream = w.stream(
                    custom_object_api.list_namespaced_custom_object,
                    group="argoproj.io",
                    version="v1alpha1",
                    namespace=namespace,
                    plural="workflows",
                    label_selector=f"{DATAFLOW_LABEL}={DATAFLOW_LABEL_VALUE}"
                )
                
                for event in stream:
                    if stop_event.is_set():
                        break
                    
                    job_id = event['object'].get('metadata', {}).get('labels', {}).get('dataflow-job-id')
                    callback("workflow", event['type'], event['object'], job_id)
            except Exception as e:
                print(f"Workflow watch error: {e}")
                if not stop_event.is_set():
                    time.sleep(5)

    workflow_thread = threading.Thread(target=watch_workflows)
    workflow_thread.daemon = True
    
    workflow_thread.start()
    
    return workflow_thread

if __name__ == "__main__":
    def resource_callback(resource_type: str, event_type: str, resource: dict, job_id: str):
        if resource_type == "workflow":
            name = resource['metadata']['name']
            status = resource.get('status', {}).get('phase', 'Unknown')
            print(f"Workflow {name} {event_type}: {status} {job_id}")
            
            if status == "Running":
                pass
            if status == "Succeeded":
                print(f"Workflow {name} Succeeded")
            elif status == "Failed":
                print(f"Workflow {name} Failed")
  
         
                
    stop_event = threading.Event()

    workflow_thread = watch_dataflow_resources(
        namespace="data-flow",
        callback=resource_callback,
        stop_event=stop_event
    )

    try:
        json_str = {
            "job_name": "rbba",
            "job_type": "pipeline",
        }
        json_str = json.dumps(json_str)
        create_argo_workflow(namespace="data-flow", job_id="rbba", job_conf=json_str, user_id='1', user_name="rb.qin", user_token="c4a674ce5e794d56befa35f5d1964b7b", job_type="pipeline", uuid_str="djsajdjsajdjasjdjaj")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
        workflow_thread.join()
    