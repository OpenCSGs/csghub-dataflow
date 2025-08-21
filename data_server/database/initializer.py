import os
import sqlparse
from loguru import logger
from data_celery.utils import get_project_root
from sqlalchemy import text
from data_server.database.session import get_sync_session

def extract_insert_statements(sql_file_path: str) -> list[str]:
    """
    Extracts all INSERT INTO statements from a given SQL file using sqlparse.
    """
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            parsed = sqlparse.parse(content)
            insert_statements = [
                str(statement).strip() for statement in parsed if statement.get_type() == 'INSERT'
            ]
            return insert_statements
    except FileNotFoundError:
        logger.error(f"Initialization file not found: {sql_file_path}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while reading {sql_file_path}: {e}")
        return []

def extract_sequence_statements(sql_file_path: str) -> list[str]:
    """
    Extracts sequence-related statements (setval, ALTER SEQUENCE) from a SQL file.
    """
    try:
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            parsed = sqlparse.parse(content)
            sequence_statements = []
            for statement in parsed:
                stmt_str = str(statement).strip().lower()
                if 'setval' in stmt_str or 'alter sequence' in stmt_str:
                    sequence_statements.append(str(statement).strip())
            return sequence_statements
    except FileNotFoundError:
        logger.error(f"Initialization file not found: {sql_file_path}")
        return []
    except Exception as e:
        logger.error(f"An error occurred while reading {sql_file_path}: {e}")
        return []

def initialize_table(table_name: str):
    """
    Initializes a table by executing INSERT statements and then sequence resets from its .sql file.
    """
    project_root = get_project_root()
    sql_file_path = os.path.join(project_root, 'data_server', 'database', 'Initialization_data', f'{table_name}.sql')

    logger.info(f"Looking for initialization file: {sql_file_path}")

    insert_statements = extract_insert_statements(sql_file_path)

    if not insert_statements:
        logger.warning(f"No INSERT statements found for table '{table_name}' in {sql_file_path}. Skipping data insertion.")
    else:
        logger.info(f"Found {len(insert_statements)} INSERT statements for table '{table_name}'. Executing now.")
        with get_sync_session() as session:
            success_count = 0
            for statement in insert_statements:
                try:
                    session.execute(text(statement))
                    session.commit()
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to execute INSERT for '{table_name}'. Rolling back.")
                    logger.error(f"Statement: {statement}")
                    logger.error(f"Error: {e}")
                    session.rollback()

            if success_count == len(insert_statements):
                logger.info(f"Successfully executed all {success_count} INSERTs for table '{table_name}'.")
            else:
                logger.warning(f"Executed {success_count}/{len(insert_statements)} INSERTs for '{table_name}'.")

    # After inserting data, handle sequence updates
    sequence_statements = extract_sequence_statements(sql_file_path)
    if not sequence_statements:
        logger.info(f"No sequence statements found for table '{table_name}'.")
        return

    logger.info(f"Found {len(sequence_statements)} sequence statements for '{table_name}'. Executing now.")
    with get_sync_session() as session:
        for statement in sequence_statements:
            try:
                session.execute(text(statement))
                session.commit()
                logger.info(f"Successfully executed sequence statement for '{table_name}'.")
            except Exception as e:
                logger.error(f"Failed to execute sequence statement for '{table_name}'. Rolling back.")
                logger.error(f"Statement: {statement}")
                logger.error(f"Error: {e}")
                session.rollback()
