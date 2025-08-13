from data_server.datasource.services.connectors.mysql import MySQLConnector
from data_server.datasource.services.connectors.mongodb import MongoDBConnector
from data_server.datasource.services.connectors.hive import HiveConnector
from data_server.datasource.DatasourceModels import DataSourceTypeEnum
from data_server.datasource.schemas import DataSourceCreate

def get_datasource_connector(datasource: DataSourceCreate):
    if datasource.source_type == DataSourceTypeEnum.MYSQL.value:  # MySQL
        return MySQLConnector(datasource)
    elif datasource.source_type == DataSourceTypeEnum.MONGODB.value:  # MongoDB
        return MongoDBConnector(datasource)
    elif datasource.source_type == DataSourceTypeEnum.HIVE.value:  # Hive
        return HiveConnector(datasource)
    else:
        raise ValueError(f"Unsupported data source type: {datasource.source_type}")