import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from data_server.datasource.schemas import DataSourceCreate
# 使用绝对导入
from data_server.datasource.services.connectors.mongodb import MongoDBConnector

# 假设 MongoDB 服务运行在本地默认端口，数据库名为 test_db
TEST_URI = "mongodb://localhost:27017/"
TEST_DATABASE = "test"


def test_mongo_connection():
    """尝试连接本地 MongoDB 数据库"""
    try:
        client = MongoClient(TEST_URI)
        client.server_info()  # 尝试获取服务器信息以验证连接
        print("成功连接到本地 MongoDB 数据库")
        return True
    except ConnectionFailure:
        print("无法连接到本地 MongoDB 数据库")
        return False
    finally:
        client.close()


@pytest.fixture(scope="module")
def test_datasource():
    # 创建 DataSourceCreate 实例，补充 source_type 字段
    datasource = DataSourceCreate(
        name="test_datasource",  # 补充数据源名称
        des="Test MongoDB datasource",  # 补充数据源描述
        source_type=1,  # 假设 MongoDB 对应的整数类型值为 1
        source_status=True,  # 补充数据源状态
        host=TEST_URI,
        database=TEST_DATABASE
    )
    return datasource


@pytest.fixture(scope="module")
def connector(test_datasource):
    # 创建 MongoDBConnector 实例
    return MongoDBConnector(test_datasource)


@pytest.fixture(scope="module")
def setup_test_data(connector):
    if not test_mongo_connection():
        pytest.skip("无法连接到本地 MongoDB 数据库，跳过测试")
    client = MongoClient(TEST_URI)
    db = client[TEST_DATABASE]
    collection = db["test_collection"]
    # 插入测试数据
    inserted_data = [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30}
    ]
    result = collection.insert_many(inserted_data)
    # 为插入的数据添加 _id 字段
    inserted_docs = []
    for i, doc in enumerate(inserted_data):
        doc_with_id = doc.copy()
        doc_with_id["_id"] = result.inserted_ids[i]
        inserted_docs.append(doc_with_id)
    yield inserted_docs
    # 清理测试数据
    collection.drop()
    client.close()


def test_insert_data(setup_test_data):
    """测试数据是否成功插入到 MongoDB 中"""
    client = MongoClient(TEST_URI)
    db = client[TEST_DATABASE]
    collection = db["test_collection"]
    # 查询集合中的所有文档，不过滤 _id 字段
    inserted_docs = list(collection.find())
    client.close()
    # 打印插入的数据
    print("插入的数据:")
    for doc in inserted_docs:
        print(doc)
    assert inserted_docs == setup_test_data