from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from data_server.datasource.schemas import DataSourceCreate

class MongoDBConnector:
    def __init__(self, datasource:DataSourceCreate):
        self.datasource = datasource
        # default_timeout_setting_milliseconds
        self.timeout_ms = 5000  # 5s

    def test_connection(self):
        client = None
        try:
            host = self.datasource.host
            uri = host
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=self.timeout_ms,
                connectTimeoutMS=self.timeout_ms,
                socketTimeoutMS=self.timeout_ms
            )
            client.server_info()
            return {"success": True, "message": "Connection successful"}
        except ServerSelectionTimeoutError as e:
            return {"error": False, "message": f"连接超时: {str(e)}"}
        except ConnectionFailure as e:
            return {"error": False, "message": f"连接失败: {str(e)}"}
        except Exception as e:
            return {"error": False, "message": f"未知错误: {str(e)}"}
        finally:
            if client:
                client.close()

    def _get_client(self):
        host = self.datasource.host
        uri = host
        return MongoClient(
            uri,
            serverSelectionTimeoutMS=self.timeout_ms,
            connectTimeoutMS=self.timeout_ms,
            socketTimeoutMS=self.timeout_ms
        )

    def execute_query(self, query):
        client = self._get_client()
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
        client = self._get_client()
        try:
            db = client[self.datasource.database]
            return db.list_collection_names()
        finally:
            client.close()

    def get_tables_and_columns(self):
        client = self._get_client()
        try:
            db = client[self.datasource.database]
            collections = db.list_collection_names()
            result = []
            for collection_name in collections:
                collection = db[collection_name]
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
        Get the number of documents in the specified collection.
        :param collection_name: Name of the collection
        :return: Number of documents
        """
        client = self._get_client()
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
        Query data in the collection with pagination support.

        Args:
            collection_name (str): Name of the collection
            offset (int): Starting offset for the query
            limit (int): Maximum number of documents to return

        Returns:
            list: List of query results, where each element is a dictionary containing all fields and values of the documents in the collection
        """
        client = self._get_client()
        try:
            db = client[self.datasource.database]
            collection = db[collection_name]

            results = list(collection.find().skip(offset).limit(limit))

            return results
        except ServerSelectionTimeoutError as e:
            raise ConnectionError(f"MongoDB连接超时: {str(e)}")
        except ConnectionFailure as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
        except Exception as e:
            raise e
        finally:
            client.close()
