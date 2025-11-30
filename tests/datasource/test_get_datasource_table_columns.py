import pytest
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from data_server.datasource.schemas import DataSourceCreate

from data_server.datasource.services.connectors.mongodb import MongoDBConnector


TEST_URI = "mongodb://localhost:27017/"
TEST_DATABASE = "test"


def test_mongo_connection():

    try:
        client = MongoClient(TEST_URI)
        client.server_info()
        print("成功连接到本地 MongoDB 数据库")
        return True
    except ConnectionFailure:
        print("无法连接到本地 MongoDB 数据库")
        return False
    finally:
        client.close()


@pytest.fixture(scope="module")
def test_datasource():

    datasource = DataSourceCreate(
        name="test_datasource",
        des="Test MongoDB datasource",
        source_type=1,
        source_status=True,
        host=TEST_URI,
        database=TEST_DATABASE
    )
    return datasource


@pytest.fixture(scope="module")
def connector(test_datasource):

    return MongoDBConnector(test_datasource)


@pytest.fixture(scope="module")
def setup_test_data(connector):
    if not test_mongo_connection():
        pytest.skip("无法连接到本地 MongoDB 数据库，跳过测试")
    client = MongoClient(TEST_URI)
    db = client[TEST_DATABASE]
    collection = db["test_collection"]

    inserted_data = [
        {"name": "Alice", "age": 25},
        {"name": "Bob", "age": 30}
    ]
    result = collection.insert_many(inserted_data)

    inserted_docs = []
    for i, doc in enumerate(inserted_data):
        doc_with_id = doc.copy()
        doc_with_id["_id"] = result.inserted_ids[i]
        inserted_docs.append(doc_with_id)
    yield inserted_docs

    collection.drop()
    client.close()


def test_insert_data(setup_test_data):

    client = MongoClient(TEST_URI)
    db = client[TEST_DATABASE]
    collection = db["test_collection"]

    inserted_docs = list(collection.find())
    client.close()

    print("插入的数据:")
    for doc in inserted_docs:
        print(doc)
    assert inserted_docs == setup_test_data