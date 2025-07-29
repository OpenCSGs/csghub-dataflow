import loguru
from pyhive import hive
from TCLIService.ttypes import TOperationState
from data_server.datasource.schemas import DataSourceCreate


class HiveConnector:
    def __init__(self, datasource: DataSourceCreate):
        self.datasource = datasource


    def get_connection(self):
        return hive.Connection(
            host=self.datasource.host,
            port=self.datasource.port,
            username=self.datasource.username,
            password=self.datasource.password if self.datasource.auth_type == 'LDAP' else None,
            database=self.datasource.database,
            auth=self.datasource.auth_type
        )

    def test_connection(self):
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES")
            result = cursor.fetchone()
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def execute_query(self, query):
        conn = self.get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(query)
            if query.lower().startswith("select"):
                return cursor.fetchall()
            else:
                return {"status": "Query executed"}
        finally:
            cursor.close()
            conn.close()

    def get_tables(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SHOW TABLES")
            return [row[0] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()

    def get_tables_and_columns(self):
        """
        查询所有表和字段信息。

        Returns:
            list: 包含表和字段信息的列表，每个元素是一个字典，包含表名和字段列表。
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute('SHOW TABLES')
                results = cursor.fetchall()
                tables_list = []
                for row in results:
                    loguru.logger.info(row)
                    table_name = row[0]
                    cursor.execute(f'DESCRIBE {table_name}')
                    table_columns_results = cursor.fetchall()
                    column_list = []
                    for column in table_columns_results:
                        column_list.append(column[0])
                    table_info = {
                        'table_name': table_name,
                        'columns': column_list
                    }
                    tables_list.append(table_info)
                return tables_list
        finally:
            conn.close()

    def get_table_columns(self, table_name: str):
        """
        查询指定表的所有字段信息。

        Args:
            table_name (str): 表名

        Returns:
            list: 包含字段名的列表
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 查询指定表的所有字段信息
                query = f'DESCRIBE {table_name}'
                cursor.execute(query, (self.datasource.database, table_name))
                results = cursor.fetchall()
                # 提取字段名并返回
                return [row[0] for row in results]
        finally:
            conn.close()

    def get_table_total_count_hive(self, table_name):
        """
        获取指定表的总行数。

        Args:
            table_name (str): 表名

        Returns:
            int: 表的总行数
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                query = f"""
                SELECT COUNT(*) AS total_count
                FROM {table_name}
                """
                cursor.execute(query)
                result = cursor.fetchone()
                return result['total_count']
        finally:
            conn.close()

    def query_table_hive(self, table_name: str, columns: list, offset: int, limit: int) -> list:
        """
        查询表中的数据，支持列过滤和分页。

        Args:
            table_name (str): 表名
            columns (list): 要查询的列名列表
            offset (int): 查询的起始偏移量
            limit (int): 查询的限制行数

        Returns:
            list: 查询结果列表，每个元素是一个元组，包含指定的列名和值
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 构建查询列名的字符串
                column_names = ', '.join(columns)
                # 构建查询语句
                query = f"""
                SELECT {column_names}
                FROM {table_name}
                LIMIT {limit} OFFSET {offset}
                """

                # 执行查询
                cursor.execute(query)

                # 获取查询结果
                rows = cursor.fetchall()

                return rows
        except Exception as e:
            raise e
        finally:
            # 确保数据库连接被关闭
            conn.close()

    def execute_custom_query_hive(self, query: str) -> list:
        """
        执行一个自定义的HiveQL查询，并返回查询结果。

        Args:
            query (str): 要执行的HiveQL查询字符串

        Returns:
            list: 查询结果列表，每个元素是一个元组，包含列名和值
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 执行查询
                cursor.execute(query)

                # 获取查询结果
                rows = cursor.fetchall()

                return rows
        except Exception as e:
            # 处理异常，例如HiveQL错误或连接问题
            raise e
        finally:
            # 确保数据库连接被关闭
            conn.close()
