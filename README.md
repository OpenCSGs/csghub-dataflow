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

## Building data-flow from Source

```
docker build -t data_flow . -f Dockerfile
```

## Building data-flow-celery from Source

```
docker build -t data_flow . -f Dockerfile-celery
```

## Prerequisites

Launch postgres container

```bash
docker run -d --name dataflow-pg \
   -p 5433:5432 \
   -v /home/pgdata:/var/lib/postgresql/data \
   -e POSTGRES_DB=data_flow \
   -e POSTGRES_USER=postgres \
   -e POSTGRES_PASSWORD=postgres \
   opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsg_public/csghub/postgres:15.10
```

Launch mongoDB container

```bash
docker run -d --name dataflow-mongo \
   -p 27017:27017 \
   -v /home/mongodata:/data/db \
   -e MONGO_INITDB_ROOT_USERNAME=root \
   -e MONGO_INITDB_ROOT_PASSWORD=example \
   opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsghq/mongo:8.0.12
```

Launch redis container

```bash
docker run -d --name dataflow-redis \
   -p 6379:6379 \
   -v /home/redisdata:/data \
   opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsghq/redis:7.2.5
```

## Installation data-flow

```bash

docker run -d --name dataflow-api -p 8000:8000 \
   -v /home/apidata:/data/dataflow_data \
   -e DATA_DIR=/data/dataflow_data \
   -e CSGHUB_ENDPOINT=https://hub.opencsg.com \
   -e MAX_WORKERS=99 \
   -e RAY_ADDRESS=auto \
   -e RAY_ENABLE=False \
   -e RAY_LOG_DIR=/home/output \
   -e API_SERVER=0.0.0.0 \
   -e API_PORT=8000 \
   -e ENABLE_OPENTELEMETRY=False \
   -e POSTGRES_DB=data_flow \
   -e POSTGRES_USER=postgres \
   -e POSTGRES_PASSWORD=postgres \
   -e DATABASE_HOSTNAME=127.0.0.1 \
   -e DATABASE_PORT=5433 \
   -e STUDIO_JUMP_URL=https://data-label.opencsg.com \
   -e REDIS_HOST_URL=redis://127.0.0.1:6379 \
   -e MONG_HOST_URL=mongodb://root:example@127.0.0.1:27017 \
   data_flow

```

## Installation data-flow-celery

```bash

docker run -d --name celery-work -p 8001:8001 \
   -v /home/celery-data:/data/dataflow_celery \
   -e DATA_DIR=/data/dataflow_celery \
   -e CSGHUB_ENDPOINT=https://hub.opencsg.com \
   -e MAX_WORKERS=99 \
   -e RAY_ADDRESS=auto \
   -e RAY_ENABLE=False \
   -e RAY_LOG_DIR=/home/output \
   -e API_SERVER=0.0.0.0 \
   -e API_PORT=8001 \
   -e ENABLE_OPENTELEMETRY=False \
   -e POSTGRES_DB=data_flow \
   -e POSTGRES_USER=postgres \
   -e POSTGRES_PASSWORD=postgres \
   -e DATABASE_HOSTNAME=127.0.0.1 \
   -e DATABASE_PORT=5433 \
   -e REDIS_HOST_URL=redis://127.0.0.1:6379 \
   -e MONG_HOST_URL=mongodb://root:example@127.0.0.1:27017 \
   data_flow_celery

```

## Run data-flow server in development mode locally

```bash
# Create virtual python 3.10 environment
conda create -n  dataflow python=3.10

# Install dependencies
pip install '.[dist]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install '.[tools]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install '.[sci]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install -r docker/requirements.txt

# Run the server locally
uvicorn data_server.main:app --reload
```

## Run data-flow-celery server in development mode locally

```bash
# Create virtual python 3.10 environment
conda create -n  dataflow python=3.10

# Install dependencies
pip install '.[dist]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install '.[tools]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install '.[sci]' -i https://pypi.tuna.tsinghua.edu.cn/simple/
pip install -r docker/requirements.txt

# Run the celery server locally
celery -A data_celery.main:celery_app worker --loglevel=info --pool=gevent
```

Notes: 
- `kenlm`, `simhash-pybind`, `opencc==1.1.8`, `imagededup` in file `environments/science_requires.txt` are only support X86 platform. Remove them if you are using ARM platform. 
- The configuration information of `REDIS_HOST_URL` and `MONG_HOST_URL` in `data-flow` and `data-flow-celery` must be consistent.
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
