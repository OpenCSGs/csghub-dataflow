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

## Building from Source

```
docker build -t data_flow . -f Dockerfile
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
   opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsg_public/postgres
```

## Installation

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
   data_flow

```

## Run server in development mode locally

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

Notes: `kenlm`, `simhash-pybind`, `opencc==1.1.8`, `imagededup` in file `environments/science_requires.txt` are only support X86 platform. Remove them if you are using ARM platform. 

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
