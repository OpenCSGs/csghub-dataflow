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
```

### 启动celery
eventlet 可以提高并发性能

直接启动，启动多个celery进程不推荐，会存在重复的worker name
```cmd
celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet --concurrency=5
```

### celery任务配置
data_celery 项目包下配置任务
具体参考test01 任务，test01是python包名
每创建一个任务需要以包的方式创建，该包下有tasks.py文件，在里面定义任务
```python
from data_celery.main import celery_app
from loguru import logger
import time

@celery_app.task(name="test_01")
def test_01(name):
    logger.info(f"test_01:{name} 开启执行")
    time.sleep(10)
    logger.info(f"test_01:{name} 执行结束")
    return True

@celery_app.task(name="test_02")
def test_02(name):
    logger.info(f"test_02:{name} 开启执行")
    time.sleep(10)
    logger.info(f"test_02:{name} 执行结束")
    return True
```
### celery任务调用

```python
from data_celery.main import celery_app
from data_celery.test01.tasks import test_01, test_02
import time

if __name__ == '__main__':
    print("main")
    # 保存任务结果对象
    result1 = test_01.apply_async(args=("123123",))
    result2 = test_02.delay("c2")

    print(f"任务1 ID: {result1.id}")
    print(f"任务2 ID: {result2.id}")

    print("main end")

    # 可选：检查任务状态（不推荐立即检查，仅用于调试）
    time.sleep(1)
    print(f"任务1状态: {result1.status}")
    print(f"任务2状态: {result2.status}")
```


### 配置内网穿透redis连接
默认使用本地环境，如果其他地方开发，需要配置内网穿透，新建.nat 文件，内容不限制
启动时会判断.nat文件是否存在，如果存在则使用内网穿透的redis连接

### celery docker部署
/docker-compose下增加redis镜像前置
配置启动命令

```yaml
services:
  postgres_db:
    restart: unless-stopped
    image: opencsg-registry.cn-beijing.cr.aliyuncs.com/opencsg_public/postgres
    volumes:
      - postgres_db:/var/lib/postgresql/data
    command: -p ${DATABASE_PORT}
    environment:
      - POSTGRES_DB=${DATABASE_DB}
      - POSTGRES_USER=${DATABASE_USERNAME}
      - POSTGRES_PASSWORD=${DATABASE_PASSWORD}
    env_file:
      - .env
    expose: 
      - ${DATABASE_PORT}
    ports:
      - "5433:${DATABASE_PORT}"
  celery_redis:
    restart: unless-stopped
    image: redis:latest  # 使用最新的官方 Redis 镜像
    volumes:
      - celery_redis_data:/data  # 挂载数据卷以持久化 Redis 数据
    ports:
      - "6379:6379"  # 将主机的 6379 端口映射到容器的 6379 端口
  api_server:
    build: .
    env_file:
      - .env
    volumes:
      # - .:/dataflow
      - ${DATA_DIR}:${DATA_DIR}
    ports:
      - "8000:8000"
    depends_on:
      - postgres_db
    # command: ["uvicorn", "data_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
  celery_worker1:
    build: .
    command: >
      sh -c "
        celery -A data_celery.main:celery_app worker --loglevel=info --pool=eventlet -n NODENAME1
      "
    depends_on:
      - celery_redis
volumes:
  postgres_db:
  celery_redis_data:
```

#### 单台部署 api_server 启动celery

使用docker-compose 启动 直接启动，celery image 使用build image的镜像即可

redis 使用docker-compose 启动，使用自己配置好redis 镜像，在.env 中配置redis_url

celery 服务启动时会读取env中的redis_url

#### 多台部署
celery image 使用build image的镜像即可
使用docker-compose 启动 api_server 可以去掉 celery_worker1 节点，

celery_worker1 单独启动时 去掉其他的节点，单独启动 celery_worker 服务

每个celery_worker 服务启动前 配置 -n 参数，例如 -n worker_hostname_des,多台部署，节点名称必须是唯一的，否则会启动重名的节点服务

单台启动多个celery 服务时可以配置多个节点 celery_worker1 、celery_worker2 、celery_worker3

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