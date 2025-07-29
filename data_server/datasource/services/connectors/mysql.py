import pymysql
from pymysql.cursors import DictCursor
from data_server.datasource.schemas import DataSourceCreate

class MySQLConnector:
    def __init__(self, datasource:DataSourceCreate):
        self.datasource = datasource

    def test_connection(self):
        try:
            conn = pymysql.connect(
                host=self.datasource.host,
                port=self.datasource.port,
                user=self.datasource.username,
                password=self.datasource.password,
                database=self.datasource.database,
                cursorclass=DictCursor
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            return {"success": True, "message": "Connection successful"}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def execute_query(self, query):
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute(query)
                if query.lower().startswith("select"):
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return {"affected_rows": cursor.rowcount}
        finally:
            conn.close()

    def get_tables(self):
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                return [row[f"Tables_in_{self.datasource.database}"] for row in cursor.fetchall()]
        finally:
            conn.close()

    def get_tables_and_columns(self):
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                # 查询表和字段信息
                query = """
                SELECT TABLE_NAME, COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
                cursor.execute(query, (self.datasource.database,))
                results = cursor.fetchall()

                # 按表名分组整理字段信息
                tables_dict = {}
                for row in results:
                    table_name = row['TABLE_NAME']
                    column_name = row['COLUMN_NAME']
                    if table_name not in tables_dict:
                        tables_dict[table_name] = []
                    tables_dict[table_name].append({'column_name': column_name})

                # 转换为要求的列表格式
                return [{'table_name': table, 'columns': columns} for table, columns in tables_dict.items()]
        finally:
            conn.close()

    def get_table_columns(self, table_name: str):
        """
        查询指定MySQL表的所有字段信息。

        Args:
            table_name (str): 表名

        Returns:
            list: 包含字段信息的列表，每个元素是一个字典，包含字段名。
        """
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                # 查询指定表的所有字段信息
                query = """
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """
                cursor.execute(query, (self.datasource.database, table_name))
                results = cursor.fetchall()

                # 提取字段名并返回
                return [{'column_name': row['COLUMN_NAME']} for row in results]
        finally:
            conn.close()

    def get_table_total_count(self, table_name):
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                query = f'SELECT COUNT(*) AS total_count FROM {table_name}'
                cursor.execute(query)
                result = cursor.fetchone()
                return result['total_count']
        finally:
            conn.close()

    def query_table(self, table_name: str, columns: list, offset: int, limit: int) -> list:
        """
        查询表中的数据，支持列过滤和分页。

        Args:
            table_name (str): 表名
            columns (list): 要查询的列名列表
            offset (int): 查询的起始偏移量
            limit (int): 查询的限制行数

        Returns:
            list: 查询结果列表，每个元素是一个字典，包含指定的列名和值
        """
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                # 构建查询列名的字符串
                column_names = ', '.join(columns)
                # 构建查询语句
                query = f"""
                SELECT {column_names}
                FROM {table_name}
                LIMIT %s OFFSET %s
                """

                # 执行查询
                cursor.execute(query, (limit, offset))

                # 获取查询结果
                rows = cursor.fetchall()

                return rows
        except Exception as e:
            raise e
        finally:
            # 确保数据库连接被关闭
            conn.close()

    def execute_custom_query(self, query: str) -> list:
        """
        执行一个自定义的SQL查询，并返回查询结果。

        Args:
            query (str): 要执行的SQL查询字符串

        Returns:
            list: 查询结果列表，每个元素是一个字典，包含列名和值
        """
        conn = pymysql.connect(
            host=self.datasource.host,
            port=self.datasource.port,
            user=self.datasource.username,
            password=self.datasource.password,
            database=self.datasource.database,
            cursorclass=DictCursor
        )
        try:
            with conn.cursor() as cursor:
                # 执行查询
                cursor.execute(query)

                # 获取查询结果
                rows = cursor.fetchall()

                return rows
        except Exception as e:
            # 处理异常，例如SQL错误或连接问题
            raise e
        finally:
            # 确保数据库连接被关闭
            conn.close()