## data-flow 启动

### 环境准备
```cmd
pip install .[dist] -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install .[tools] -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install .[scil] -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install -r docker/requirements.txt
```
### 启动api-server
```cmd
uvicorn data_server.main:app --reload
uvicorn data_server.main:app --host 0.0.0.0 --port 8001
```

### 调度说明
当前任务调度已切换为 DataFlow 调用 CSGHub，由 CSGHub 转换为 Argo Workflow 执行。

DataFlow API 负责创建 DAG 并提交任务；Argo Pod 内实际执行数据采集、格式转换、数据处理、工具任务。Pod 使用 **Argo 执行镜像**（`Dockerfile-argo` 构建），入口命令为：

```bash
python run_dataflow_task.py --task-type <datasource|formatify|pipeline|tool> --task-params '<json>'
```

旧的本地 Celery worker 启动方式已废弃，不需要再单独启动 `celery -A data_celery.main:celery_app worker ...`。

### Argo 执行镜像

DataFlow 使用两类镜像，职责不同：

| 镜像 | Dockerfile | 用途 |
|------|------------|------|
| API 服务 | `Dockerfile` | 运行 `data_server` API，向 CSGHub/Argo 提交任务 |
| Argo 执行 | `Dockerfile-argo` | 在 Argo Workflow Pod 内执行具体任务 |

Argo 镜像包含全量算子依赖（`docker/dataflow_requirements.txt`）及运行代码（`data_server`、`data_engine`、`run_dataflow_task.py`）。

**本地构建（不推送）：**

```bash
docker build -f Dockerfile-argo \
  --build-arg BUILD_CN=true \
  --build-arg PRELOAD_ASSETS=true \
  -t opencsg_public/dataflow:argo-latest .
```

**构建并推送（推荐）：**

```bash
# ./scripts/build-push-argo.sh [registry] [tag]
./scripts/build-push-argo.sh 192.168.2.98:8140 argo-latest
./scripts/build-push-argo.sh opencsg-registry.cn-beijing.cr.aliyuncs.com argo-20260529
```

**多平台构建：**

```bash
docker buildx build --provenance false --platform linux/amd64 \
  -f Dockerfile-argo \
  --build-arg BUILD_CN=true \
  --build-arg PRELOAD_ASSETS=true \
  -t opencsg_public/dataflow:argo-latest .
```

常用构建参数：

- `BUILD_CN=true` — 使用国内 apt/pip 镜像源（国内环境推荐）
- `PRELOAD_ASSETS=true` — 预下载 Data Juicer 资源/模型到镜像内（生产环境推荐）

**在 API 服务中配置镜像：**

在 DataFlow API 的环境变量中设置 `CSGHUB_DATAFLOW_TEMPLATE_IMAGE`（`.env` 或 `docker run` 均可）。CSGHub 会自动拼接仓库前缀，此处只需填写仓库内路径，例如：

```bash
CSGHUB_DATAFLOW_TEMPLATE_IMAGE=opencsg_public/dataflow:argo-latest
```

同时确保 API 服务的 `DATA_DIR` 与 CSGHub 创建 Workflow 时 `workflow-data` 卷的 `mountPath` 一致（默认 `/data/dataflow_data`）。

### 部署说明
当前部署只需要启动 DataFlow API 服务，以及其依赖的数据库、存储和网关相关配置。

Argo 执行镜像需提前构建并推送到 CSGHub 可访问的镜像仓库，并在 API 服务中通过 `CSGHUB_DATAFLOW_TEMPLATE_IMAGE` 指定。

原 `celery_worker`、`Dockerfile-celery`、独立 Celery compose/脚本 已下线，不再作为部署方案的一部分。

### DataSource extra_config 示例
```json
{
  "mysql": {
    "source": {
        "table1": ["col1", "col2"],
        "table2": ["col3", "col4"]
    },
    "type": "sql",
    "sql": "select * from table1 where col1 = 'value'"
  },
  "hive": {
    "source":{
        "table1": ["col1", "col2"],
        "table2": ["col3", "col4"]
    },
    "type": "sql",
    "sql": "select * from table1 where col1 = 'value'"
  },
  "mongo": ["table1", "table2"],
  "max_line_json": 10000,
  "csg_hub_dataset_name": "",
  "csg_hub_dataset_id": 0,
  "csg_hub_dataset_default_branch": "main"
}
```
每一个数据源 根据不同的key 来存储采集配置
每个数据源 配置内的 "type": "sql" 表示使用sql语句查询,其他值或者不填写表示使用source 配置

"max_line_json" 配置采集json数据时，单文件最大行数,默认50000

"csg_hub_dataset_name" 数据流向仓库分支名称

"csg_hub_dataset_id" 数据流向仓库 repo_id

"csg_hub_dataset_default_branch" 数据流向仓库默认分支