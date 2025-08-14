# 数据库连接方式文档

## 概述
本文档整理了项目中测试用的数据库连接方式，包括MySQL、MongoDB和PostgreSQL的连接参数、认证方式和实现细节。

## 1. MySQL连接方式

### 1.1 连接参数
- **主机(host)**: 从数据源配置获取
- **端口(port)**: 从数据源配置获取
- **用户名(username)**: 从数据源配置获取
- **密码(password)**: 从数据源配置获取
- **数据库名(database)**: 从数据源配置获取

### 1.2 认证方式
采用标准的用户名/密码认证方式。

### 1.3 连接实现
```python
conn = pymysql.connect(
    host=self.datasource.host,
    port=self.datasource.port,
    user=self.datasource.username,
    password=self.datasource.password,
    database=self.datasource.database,
    cursorclass=DictCursor
)
```

### 1.4 测试连接方法
```python
def test_connection(self):
    try:
        # 连接代码同上
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
        return {"success": True, "message": "Connection successful"}
    except Exception as e:
        return {"success": False, "message": str(e)}
```

## 2. MongoDB连接方式

### 2.1 连接参数
- **连接URI(host)**: 从数据源配置获取，包含认证信息
- **数据库名(database)**: 从数据源配置获取

### 2.2 认证方式
认证信息嵌入在连接URI中，格式通常为：`mongodb://username:password@host:port/`

### 2.3 连接实现
```python
host = self.datasource.host
uri = host
client = MongoClient(uri)
db = client[self.datasource.database]
```

### 2.4 测试连接方法
```python
def test_connection(self):
    try:
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        client.server_info()  # 检查连接
        return {"success": True, "message": "Connection successful"}
    except ConnectionFailure as e:
        return {"success": False, "message": str(e)}
```

## 3. PostgreSQL连接方式

### 3.1 连接参数
- **主机(host)**: 默认192.168.2.98，可通过环境变量DATABASE_HOSTNAME覆盖
- **端口(port)**: 默认5432，可通过环境变量DATABASE_PORT覆盖
- **用户名(username)**: 默认admin，可通过环境变量DATABASE_USERNAME覆盖
- **密码(password)**: 默认admin123456，可通过环境变量DATABASE_PASSWORD覆盖
- **数据库名(database)**: 默认data_flow，可通过环境变量DATABASE_DB覆盖

### 3.2 认证方式
采用标准的用户名/密码认证方式。

### 3.3 连接实现
```python
def sqlalchemy_database_uri() -> URL:
    database_hostname = "192.168.2.98"
    if os.path.exists(".nat"):
        database_hostname = "home.sxcfx.cn"
    return URL.create(
        drivername="postgresql",
        username=os.getenv('DATABASE_USERNAME', "admin"),
        password=os.getenv('DATABASE_PASSWORD', "admin123456"),
        host=os.getenv('DATABASE_HOSTNAME', database_hostname),
        port=os.getenv('DATABASE_PORT', 5432),
        database=os.getenv('DATABASE_DB', "data_flow")
    )
```

## 4. 环境变量配置
测试环境的数据库连接参数可以通过以下环境变量进行配置：
- DATABASE_HOSTNAME: 数据库主机名
- DATABASE_PORT: 数据库端口
- DATABASE_USERNAME: 数据库用户名
- DATABASE_PASSWORD: 数据库密码
- DATABASE_DB: 数据库名称

## 5. 连接管理
- 使用SQLAlchemy的sessionmaker管理PostgreSQL连接
- MySQL和MongoDB连接在每次操作后会显式关闭