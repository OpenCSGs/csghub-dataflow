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
                query = """
                SELECT TABLE_NAME, COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME, ORDINAL_POSITION
                """
                cursor.execute(query, (self.datasource.database,))
                results = cursor.fetchall()

                tables_dict = {}
                for row in results:
                    table_name = row['TABLE_NAME']
                    column_name = row['COLUMN_NAME']
                    if table_name not in tables_dict:
                        tables_dict[table_name] = []
                    tables_dict[table_name].append({'column_name': column_name})

                return [{'table_name': table, 'columns': columns} for table, columns in tables_dict.items()]
        finally:
            conn.close()

    def get_table_columns(self, table_name: str):
        """
        Query all field information of the specified MySQL table.
        Args:
        table_name (str): Name of the table
        Returns:
        list: A list containing field information, where each element is a dictionary including the field name.
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
                query = """
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                """
                cursor.execute(query, (self.datasource.database, table_name))
                results = cursor.fetchall()

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
        Query data in the table with support for column filtering and pagination.
        Args:
        table_name (str): Name of the table
        columns (list): List of column names to query
        offset (int): Starting offset for the query
        limit (int): Maximum number of rows to return
        Returns:
        list: List of query results, where each element is a dictionary containing the specified column names and their values
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

                column_names = ', '.join(columns)

                query = f"""
                SELECT {column_names}
                FROM {table_name}
                LIMIT %s OFFSET %s
                """

                cursor.execute(query, (limit, offset))

                rows = cursor.fetchall()

                return rows
        except Exception as e:
            raise e
        finally:
            conn.close()

    def execute_custom_query(self, query: str) -> list:
        """
        Execute a custom SQL query and return the query results.
        Args:
        query (str): The SQL query string to be executed
        Returns:
        list: List of query results, where each element is a dictionary containing column names and their values
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

                cursor.execute(query)

                rows = cursor.fetchall()

                return rows
        except Exception as e:

            raise e
        finally:

            conn.close()