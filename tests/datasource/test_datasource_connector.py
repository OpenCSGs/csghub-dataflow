from data_server.datasource.DatasourceModels import DataSourceTypeEnum
from data_server.datasource.schemas import DataSourceCreate
from data_server.datasource.services.datasource import get_datasource_connector




DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 27017,
    "database": "test_mongodb_db"
}

def test_get_mongodb_tables_and_columns():

    dataSourceCreate = DataSourceCreate(
        name="test",
        des="test mongo des",
        source_type=DataSourceTypeEnum.MONGODB.value,
        source_status=True,
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        database=DB_CONFIG["database"],
        username="data_flow_test",
        password="123456",
    )
    
    connector = get_datasource_connector(dataSourceCreate)
    if connector.test_connection():

        collections_and_columns = connector.get_tables_and_columns()
        print(f"collections_and_columns: {collections_and_columns}")
        

        assert isinstance(collections_and_columns, list), "返回结果应该是列表"
        

        for collection_info in collections_and_columns:
            assert "table_name" in collection_info, "集合信息应包含table_name"
            assert "columns" in collection_info, "集合信息应包含columns字段"
            assert isinstance(collection_info["columns"], list), "columns应该是列表"
            

            for column_info in collection_info["columns"]:
                assert "column_name" in column_info, "字段信息应包含column_name"
    else:
        print("MongoDB连接失败")


if __name__ == '__main__':

    test_get_mongodb_tables_and_columns()