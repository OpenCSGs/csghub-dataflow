# csghub-dataflow
OpenCSG dataflow is a one-stop data processing platform designed to leverage large model technology and advanced algorithms to optimize the entire data processing lifecycle, enhancing efficiency and precision, while addressing enterprise challenges in data management such as inefficiency, adaptability gaps, and security and compliance issues.

**DataFlow** is an open-source platform engineered to streamline end-to-end data processing within the AI/ML lifecycle. By unifying data workflows and model optimization, it transforms fragmented pipelines into a cohesive, automated system—ideal for enterprises tackling data complexity at scale.  

**🔑 Key Features**
1. **Full Lifecycle Management**  
   - Unified handling of data ingestion, transformation, modeling, and evaluation.  
2. **Seamless CSGHub Integration**  
   - Directly ingest datasets from CSGHub and push refined data back for model retraining, creating a continuous feedback loop .  
3. **Modular & Extensible Design**  
   - Plug-and-play operators for custom pipelines (e.g., NLP, image, audio processing).  
4. **Distributed Computing**  
   - Scale workloads across clusters via Kubernetes integration .  
5. **Multi-Agent Task Orchestration**  
   - Dynamically allocate complex tasks (e.g., data validation, anomaly detection) to collaborative agents.  
6. **MinerU Engine**  
   - Convert PDFs to structured Markdown/JSON for LLM-friendly datasets .  
7. **Growing Operator Library**  
   - Expandable support for multimodal data (text, image, video) and domain-specific transformations.  

## 🔗 Acknowledgements  

This project is built upon **[Data Juicer](https://github.com/modelscope/data-juicer)**. We sincerely thank the Data Juicer team for their impactful work in data engineering.  

### 📜 License  
This project inherits the [Apache License 2.0](LICENSE) from Data Juicer.  

# 🚀 Quick Start

## Building Docker Images

DataFlow uses two images with different roles:

| Image | Dockerfile | Purpose |
|-------|------------|---------|
| API Server | `Dockerfile` | Runs `data_server` API; submits jobs to CSGHub/Argo |
| Argo Execution | `Dockerfile-argo` | Runs inside Argo Workflow pods; executes datasource / formatify / pipeline / tool tasks via `run_dataflow_task.py` |

### API Server Image

```bash
docker build -t dataflow . -f Dockerfile

docker buildx build --provenance false --platform linux/amd64 -t dataflow . -f Dockerfile

docker buildx build --provenance false --platform linux/arm64 -t dataflow . -f Dockerfile
```

### Argo Execution Image

The Argo image bundles full operator dependencies (`docker/dataflow_requirements.txt`) and runtime code (`data_server`, `data_engine`, `run_dataflow_task.py`). CSGHub creates Argo Workflow pods from this image.

**Build locally (no push):**

```bash
docker build -f Dockerfile-argo \
  --build-arg BUILD_CN=true \
  --build-arg PRELOAD_ASSETS=true \
  -t opencsg_public/dataflow:argo-latest .
```

**Build and push (recommended):**

```bash
# ./scripts/build-push-argo.sh [registry] [tag]
./scripts/build-push-argo.sh 192.168.2.98:8140 argo-latest
./scripts/build-push-argo.sh opencsg-registry.cn-beijing.cr.aliyuncs.com argo-20260529
```

**Multi-platform build:**

```bash
docker buildx build --provenance false --platform linux/amd64 \
  -f Dockerfile-argo \
  --build-arg BUILD_CN=true \
  --build-arg PRELOAD_ASSETS=true \
  -t opencsg_public/dataflow:argo-latest .
```

Build args:

- `BUILD_CN=true` — use Aliyun apt/pip mirrors (recommended in China)
- `PRELOAD_ASSETS=true` — preload Data Juicer assets/models into the image (recommended for production)

**Configure the API server to use the image:**

Set `CSGHUB_DATAFLOW_TEMPLATE_IMAGE` on the DataFlow API service (also in `.env` / `docker run`). CSGHub prepends the registry prefix automatically — pass only the repository path, for example:

```bash
CSGHUB_DATAFLOW_TEMPLATE_IMAGE=opencsg_public/dataflow:argo-latest
```

When a job is submitted, each Argo pod runs:

```bash
python run_dataflow_task.py --task-type <datasource|formatify|pipeline|tool> --task-params '<json>'
```

Ensure `DATA_DIR` on the API server matches the `workflow-data` volume `mountPath` configured in CSGHub (default `/data/dataflow_data`).

## Prerequisites

Launch postgres container

```bash
docker run -d --name dataflow-pg \
   -p 5433:5432 \
   -v /tmp/data_flow/pgdata:/var/lib/postgresql/data \
   -e POSTGRES_DB=data_flow \
   -e POSTGRES_USER=postgres \
   -e POSTGRES_PASSWORD=postgres \
   opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsghq/csghub/postgres:15.10
```

## Installation data-flow

```bash

docker run -d --name dataflow-api -p 8000:8000 \
   -v /tmp/data_flow/apidata:/data/dataflow_data \
   -c "uvicorn data_server.main:app --host 0.0.0.0 --port 8000" \
   -e DATA_DIR=/data/dataflow_data \
   -e CSGHUB_ENDPOINT=https://hub.opencsg.com \
   -e MAX_WORKERS=99 \
   -e RAY_ADDRESS=auto \
   -e RAY_ENABLE=False \
   -e RAY_LOG_DIR=/data/ray_output \
   -e API_SERVER=0.0.0.0 \
   -e API_PORT=8000 \
   -e ENABLE_OPENTELEMETRY=False \
   -e DATABASE_DB=data_flow \
   -e DATABASE_USERNAME=postgres \
   -e DATABASE_PASSWORD=postgres \
   -e DATABASE_HOSTNAME=127.0.0.1 \
   -e DATABASE_PORT=5433 \
   -e STUDIO_JUMP_URL=https://data-label.opencsg.com \
   -e CSGHUB_DATAFLOW_TEMPLATE_IMAGE=opencsg_public/dataflow:argo-latest \
   dataflow

```

## Scheduling

DataFlow submits job execution to CSGHub/Argo. The API server builds a DAG and references the Argo execution image via `CSGHUB_DATAFLOW_TEMPLATE_IMAGE`. The old standalone `data-flow-celery` worker deployment is retired and should not be started anymore.

See [Argo Execution Image](#argo-execution-image) above for build and configuration details.

## Run data-flow server in development mode locally

### Create a Virtual Environment

```bash
uv venv --python 3.10

source .venv/bin/activate

# or

conda create -n  dataflow python=3.10
```

```bash

# Install dependencies
#pip install '.[dist]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
#pip install '.[tools]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
#pip install '.[sci]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
#pip install -r docker/requirements.txt

uv pip install -r docker/dataflow_requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# Run the server locally
uvicorn data_server.main:app --reload
```

Notes: 
- `kenlm`, `simhash-pybind`, `opencc==1.1.8`, `imagededup` in file `environments/science_requires.txt` are only support X86 platform. Remove them if you are using ARM platform. 
- DataFlow no longer relies on standalone Celery workers for task scheduling. Use the DataFlow API together with the CSGHub/Argo execution chain.
- If you want to use the data annotation service, please install and enable the **[Label Studio](https://github.com/OpenCSGs/label-studio)** service. Additionally, you need to set the `STUDIO_JUMP_URL` variable of the `data-flow` service to the address of the `Label Studio` service.

## 🛣️ Roadmap
Upcoming:  
- Enhanced real-time data streaming  
- AutoML integration for automated model tuning  
- Cross-cloud synchronization
- Support more data sources

## 🤝 Contributing
We welcome contributions! 

## 📞 Contact
For support or queries:  
- Email: [community@opencsg.com](mailto:community@opencsg.com)  
- GitHub: [OpenCSG/DataFlow](https://github.com/OpenCSGs)  
