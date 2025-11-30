from data_server.datasource.DatasourceModels import DataSourceTypeEnum, DataSource,DataSourceTaskStatusEnum
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session



def add_datasource():


    extra_config = {
      "mysql": {
        "source": {
            "test_table_1": ["id","name", "age","created_at"],
            "test_table_3": ["id","name", "age","created_at"]
        },
        "type": "",
        "sql": ""
      },
      "max_line_json": 10000,
      "csg_hub_dataset_name": "test_mysql",
      "csg_hub_dataset_id": 98,
      "csg_hub_dataset_default_branch": "main"
    }
    datasource = DataSource(
        source_type=DataSourceTypeEnum.MYSQL.value,
        name='测试数据库采集任务5.6',
        description='测试数据库采集任务',
        username='root',
        password='nC9@xZ4f!G7jM^2p',
        host='home.sxcfx.cn',
        port=18125,
        database='mysql',
        task_status=DataSourceTaskStatusEnum.WAITING.value,
        owner_id=1,
        extra_config=extra_config
    )
    db_session: Session = get_sync_session()
    db_session.add(datasource)
    db_session.commit()


if __name__ == '__main__':

    add_datasource()