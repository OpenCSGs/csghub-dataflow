from data_server.datasource.DatasourceModels import DataSourceTypeEnum
from data_server.datasource.schemas import DataSourceCreate
from data_server.datasource.services.datasource import get_datasource_connector



# 数据库配置（请根据实际环境修改）
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 27017,
    "database": "test_mongodb_db"
}

def test_get_mongodb_tables_and_columns():
    # MongoDB测试配置
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
        # 调用get_tables_and_columns方法
        collections_and_columns = connector.get_tables_and_columns()
        print(f"collections_and_columns: {collections_and_columns}")
        
        # 验证返回数据结构
        assert isinstance(collections_and_columns, list), "返回结果应该是列表"
        
        # 对每个集合进行验证（如果有集合）
        for collection_info in collections_and_columns:
            assert "table_name" in collection_info, "集合信息应包含table_name"
            assert "columns" in collection_info, "集合信息应包含columns字段"
            assert isinstance(collection_info["columns"], list), "columns应该是列表"
            
            # 验证字段信息（如果有字段）
            for column_info in collection_info["columns"]:
                assert "column_name" in column_info, "字段信息应包含column_name"
    else:
        print("MongoDB连接失败")


if __name__ == '__main__':

    test_get_mongodb_tables_and_columns()