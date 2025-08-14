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
        Query information about all tables and fields.
        Returns:
        list: A list containing table and field information, where each element is a dictionary including the table name and a list of fields.
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
        Query all field information of the specified table.
        Args:
        table_name (str): Name of the table
        Returns:
        list: A list containing field names
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                query = f'DESCRIBE {table_name}'
                cursor.execute(query)
                results = cursor.fetchall()
                return [row[0] for row in results]
        finally:
            conn.close()

    def get_table_total_count_hive(self, table_name):
        """
        Get the total number of rows in the specified table.
        Args:
        table_name (str): Name of the table
        Returns:
        int: Total number of rows in the table
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
                loguru.logger.info(f'count:{result[0]}')
                if result:
                    return result[0]
                else:
                    return 0
        finally:
            conn.close()

    def query_table_hive(self, table_name: str, columns: list, offset: int, limit: int) -> list:
        """
        Query data in the table with column filtering and pagination support.
        Args:
        table_name (str): Name of the table
        columns (list): List of column names to query
        offset (int): Starting offset for the query
        limit (int): Maximum number of rows to return
        Returns:
        list: List of query results, where each element is a tuple containing the specified column names and their values
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                column_names = ', '.join(columns)
                query = f"""
                SELECT {column_names}
                FROM {table_name}
                LIMIT {limit} OFFSET {offset}
                """
                cursor.execute(query)
                rows = cursor.fetchall()
                return rows
        except Exception as e:
            raise e
        finally:

            conn.close()

    def execute_custom_query_hive(self, query: str) -> list:
        """
        Execute a custom HiveQL query and return the query results.
        Args:
        query (str): The HiveQL query string to be executed
        Returns:
        list: List of query results, where each element is a tuple containing column names and values
        """
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:

                cursor.execute(query)

                rows = cursor.fetchall()

                return rows
        except Exception as e:
            raise e
        finally:
            conn.close()
