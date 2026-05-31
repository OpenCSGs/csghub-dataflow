import os

from data_server.datasource.schemas import DataSourceBase


class FileConnector:
    def __init__(self, datasource: DataSourceBase):
        self.datasource = datasource

    def _get_source_path(self) -> str:
        extra_config = self.datasource.extra_config or {}
        if isinstance(extra_config, str):
            extra_config = {}

        candidates = [
            extra_config.get("file_path"),
            extra_config.get("path"),
            self.datasource.host,
            self.datasource.database,
        ]
        for value in candidates:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return ""

    def test_connection(self):
        source_path = self._get_source_path()
        if not source_path:
            return {"success": False, "message": "FILE 数据源路径不能为空"}
        if not os.path.exists(source_path):
            return {"success": False, "message": f"FILE 数据源路径不存在: {source_path}"}
        return {"success": True, "message": "Connection successful"}

    def get_tables(self):
        source_path = self._get_source_path()
        if os.path.isfile(source_path):
            return [os.path.basename(source_path)]

        entries = []
        for name in sorted(os.listdir(source_path)):
            entries.append(name)
        return entries

    def get_tables_and_columns(self):
        source_path = self._get_source_path()
        if os.path.isfile(source_path):
            return [{
                "table_name": os.path.basename(source_path),
                "columns": [],
            }]

        result = []
        for name in sorted(os.listdir(source_path)):
            entry_path = os.path.join(source_path, name)
            result.append({
                "table_name": name,
                "columns": [],
                "entry_type": "directory" if os.path.isdir(entry_path) else "file",
            })
        return result

    def get_table_columns(self, table_name: str):
        return []
