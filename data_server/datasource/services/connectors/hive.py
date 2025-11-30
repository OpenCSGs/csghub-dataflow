from pyhive import hive
from TCLIService.ttypes import TOperationState
from data_server.datasource.schemas import DataSourceCreate


class HiveConnector:
    def __init__(self, datasource: DataSourceCreate):
        self.datasource = datasource


    def get_connection(self, timeout=30):
        """
        Get Hive connection with timeout setting
        Args:
            timeout (int): Connection timeout in seconds, default 30 (not used by pyhive, kept for compatibility)
        Returns:
            hive.Connection: Hive connection object
        """
        # Handle auth_type: pyhive uses 'NOSASL' for no authentication, 'LDAP' for LDAP authentication
        auth_type = self.datasource.auth_type
        if auth_type:
            auth_type_upper = auth_type.upper()
            if auth_type_upper in ['NONE', 'NOSASL']:
                auth_type = 'NOSASL'
            elif auth_type_upper == 'LDAP':
                auth_type = 'LDAP'
            else:
                auth_type = 'NOSASL'
        else:
            auth_type = 'NOSASL'
        
        # Password only needed for LDAP authentication
        password = None
        if auth_type == 'LDAP':
            password = self.datasource.password
        
        conn = hive.Connection(
            host=self.datasource.host,
            port=self.datasource.port,
            username=self.datasource.username,
            password=password,
            database=self.datasource.database,
            auth=auth_type
        )
        return conn

    def test_connection(self):
        conn = None
        cursor = None
        try:
            conn = self.get_connection(timeout=30)
            cursor = conn.cursor()
            # Use simple SELECT 1 query to avoid potential issues with SHOW TABLES
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            # Verify result
            if result and len(result) > 0:
                return {"success": True, "message": "Connection successful"}
            else:
                return {"success": False, "message": "Connection test returned empty result"}
        except Exception as e:
            return {"success": False, "message": str(e)}
        finally:
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if conn:
                try:
                    conn.close()
                except:
                    pass

    def execute_query(self, query):
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            if query.lower().strip().startswith("select"):
                results = cursor.fetchall()
                return results
            else:
                return {"status": "Query executed"}
        finally:
            cursor.close()
            conn.close()

    def get_tables(self):
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            cursor.execute("SHOW TABLES")
            results = cursor.fetchall()
            return [row[0] for row in results]
        finally:
            cursor.close()
            conn.close()

    def get_tables_and_columns(self):
        """
        Query information about all tables and fields.
        Returns:
        list: A list containing table and field information, where each element is a dictionary including the table name and a list of fields.
        """
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            cursor.execute('SHOW TABLES')
            results = cursor.fetchall()
            tables_list = []
            for row in results:
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
            cursor.close()
            conn.close()

    def get_table_columns(self, table_name: str):
        """
        Query all field information of the specified table.
        Args:
        table_name (str): Name of the table
        Returns:
        list: A list containing field names
        """
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            query = f'DESCRIBE {table_name}'
            cursor.execute(query)
            results = cursor.fetchall()
            return [row[0] for row in results]
        finally:
            cursor.close()
            conn.close()

    def get_table_total_count_hive(self, table_name):
        """
        Get the total number of rows in the specified table.
        Args:
            table_name (str): Name of the table
        Returns:
            int: Total number of rows in the table
        """
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            query = f"""
            SELECT COUNT(*) AS total_count
            FROM {table_name}
            """
            cursor.execute(query)
            result = cursor.fetchone()
            if result:
                return result[0]
            else:
                return 0
        finally:
            cursor.close()
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
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            column_names = ', '.join(columns)
            query = f"""
            SELECT {column_names}
            FROM {table_name}
            LIMIT {limit} OFFSET {offset}
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        finally:
            cursor.close()
            conn.close()

    def execute_custom_query_hive(self, query: str) -> list:
        """
        Execute a custom HiveQL query and return the query results.
        Args:
            query (str): The HiveQL query string to be executed
        Returns:
            list: List of query results, where each element is a tuple containing column names and values
        """
        conn = self.get_connection(timeout=60)
        cursor = conn.cursor()
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
        finally:
            cursor.close()
            conn.close()
