from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from data_server.datasource.schemas import DataSourceCreate

class MongoDBConnector:
    def __init__(self, datasource:DataSourceCreate):
        self.datasource = datasource

    def test_connection(self):
        try:
            host = self.datasource.host
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
        Query data in the collection with pagination support.

        Args:
            collection_name (str): Name of the collection
            offset (int): Starting offset for the query
            limit (int): Maximum number of documents to return

        Returns:
            list: List of query results, where each element is a dictionary containing all fields and values of the documents in the collection
        """
        host = self.datasource.host
        uri = host
        client = MongoClient(uri)
        try:
            db = client[self.datasource.database]
            collection = db[collection_name]

            results = list(collection.find().skip(offset).limit(limit))

            return results
        except ConnectionFailure as e:
            raise ConnectionError(f"Failed to connect to MongoDB: {str(e)}")
        except Exception as e:
            raise e
        finally:
            client.close()
