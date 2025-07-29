from data_server.datasource.DatasourceModels import DataSourceTypeEnum, DataSource,DataSourceTaskStatusEnum
from data_server.database.session import get_sync_session
from sqlalchemy.orm import Session



def add_datasource():

    '''
    MYSQL5.6:
    host: home.sxcfx.cn  端口 18125   root  密码：nC9@xZ4f!G7jM^2p
    MYSQL8:
    host: home.sxcfx.cn  端口 18126   root  密码：zQ5*yH2m!B8pD^3x
    '''
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
    # 需要的时候执行添加数据采集源信息
    add_datasource()