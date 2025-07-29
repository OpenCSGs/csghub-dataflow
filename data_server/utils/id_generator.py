from sqlalchemy import BigInteger, Column, event
from sqlalchemy.ext.declarative import declared_attr
from data_server.utils.snowflake_id import generate_id
import inspect

class IdMixin:
    """
    提供紧凑型10位ID自动生成功能的Mixin类
    用于替代SQLAlchemy默认的自增主键
    生成的ID为10位数字，范围：1000000000 - 9999999999
    """

    @declared_attr
    def id(cls):
        """
        定义id列为BigInteger类型，非自增，使用紧凑型10位ID算法生成
        """
        return Column(BigInteger, primary_key=True)

    @staticmethod
    def _before_insert_listener(mapper, connection, target):
        """
        在插入前生成10位ID作为主键
        """
        if target.id is None:
            target.id = generate_id()

def register_id_generator_listeners(Base):
    """
    为所有继承IdMixin的模型注册监听器
    适配混合使用@as_declarative装饰的Base
    """
    from data_server.operator.models.operator import OperatorInfo, OperatorConfig, OperatorConfigSelectOptions
    from data_server.operator.models.operator_permission import OperatorPermission
    from data_server.algo_templates.model import AlgoTemplate

    # 直接为特定的模型类注册监听器
    models = [OperatorInfo, OperatorConfig, OperatorConfigSelectOptions, OperatorPermission,AlgoTemplate]
    
    for model_class in models:
        if issubclass(model_class, IdMixin):
            event.listen(model_class, 'before_insert', IdMixin._before_insert_listener) 