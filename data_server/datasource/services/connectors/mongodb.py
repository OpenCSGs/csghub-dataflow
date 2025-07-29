from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from data_server.datasource.schemas import DataSourceCreate

class MongoDBConnector:
    def __init__(self, datasource:DataSourceCreate):
        self.datasource = datasource

    def test_connection(self):
        try:
            host = self.datasource.host
            # host 如果需要鉴权里面包含用户名和密码
            uri = host
            client = MongoClient(uri)
            client.server_info()
            return {"success": True, "message": "Connection successful"}
        except ConnectionFailure as e:
            return {"success": False, "message": str(e)}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def execute_query(self, query):
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        db = client[self.datasource.database]
        try:
            collection = db[query['collection']]
            operation = query['operation']

            if operation == "find":
                filter_ = query.get('filter', {})
                projection = query.get('projection', {})
                return list(collection.find(filter_, projection))
            elif operation == "aggregate":
                pipeline = query.get('pipeline', [])
                return list(collection.aggregate(pipeline))
            else:
                return {"error": f"Unsupported operation: {operation}"}
        finally:
            client.close()

    def get_tables(self):
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        try:
            db = client[self.datasource.database]
            return db.list_collection_names()
        finally:
            client.close()

    def get_tables_and_columns(self):
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        try:
            db = client[self.datasource.database]
            collections = db.list_collection_names()
            result = []
            for collection_name in collections:
                collection = db[collection_name]
                # 获取集合中的文档样例来推断字段
                sample_doc = collection.find_one()
                columns = []
                if sample_doc:
                    columns = list(sample_doc.keys())
                result.append({
                    'table_name': collection_name,
                    'columns': columns
                })
            return result
        finally:
            client.close()

    def get_collection_document_count(self, collection_name):
        """
        获取指定集合的文档数量。
        :param collection_name: 集合名称
        :return: 文档数量
        """
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        try:
            db = client[self.datasource.database]
            collection = db[collection_name]
            count = collection.count_documents({})
            return count
        except Exception as e:
            raise e
        finally:
            client.close()

    def query_collection(self, collection_name: str, offset: int, limit: int) -> list:
        """
        查询集合中的数据，支持分页。

        Args:
            collection_name (str): 集合名
            offset (int): 查询的起始偏移量
            limit (int): 查询的限制文档数

        Returns:
            list: 查询结果列表，每个元素是一个字典，包含集合中文档的所有字段和值
        """
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        try:
            # 选择数据库和集合
            db = client[self.datasource.database]
            collection = db[collection_name]
            # MongoDB的分页使用skip和limit
            results = list(collection.find().skip(offset).limit(limit))

            return results
        except ConnectionFailure as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
        except Exception as e:
            raise e
        finally:
            # 确保数据库连接被关闭
            client.close()
