import os
import re
import sqlparse
from loguru import logger
from data_celery.utils import get_project_root
from sqlalchemy import text
from data_server.database.session import get_sync_session

def ensure_deletion_status_table():
    """
    Create deletion_status table if it doesn't exist.
    """
    with get_sync_session() as session:
        try:
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS deletion_status (
                    id SERIAL PRIMARY KEY,
                    operation_name VARCHAR(255) UNIQUE NOT NULL,
                    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    description TEXT
                )
            """))
            session.commit()
        except Exception as e:
            logger.error(f"Error creating deletion_status table: {e}")
            session.rollback()

def has_deletion_been_executed() -> bool:
    """
    Check if the one-time deletion has already been executed by checking database.
    """
    ensure_deletion_status_table()
    with get_sync_session() as session:
        try:
            result = session.execute(
                text("SELECT 1 FROM deletion_status WHERE operation_name = :name"),
                {"name": "init_data_deletion"}
            )
            executed = result.scalar_one_or_none() is not None
            if executed:
                logger.info("Deletion has already been executed (found record in deletion_status table)")
            else:
                logger.info("Deletion has not been executed yet (no record in deletion_status table)")
            return executed
        except Exception as e:
            logger.warning(f"Error checking deletion status: {e}")
            return False

def mark_deletion_as_executed():
    """
    Mark the one-time deletion as executed in database.
    """
    with get_sync_session() as session:
        try:
            session.execute(
                text("""
                    INSERT INTO deletion_status (operation_name, description) 
                    VALUES (:name, :desc) 
                    ON CONFLICT (operation_name) DO NOTHING
                """),
                {
                    "name": "init_data_deletion",
                    "desc": "Initial data deletion from Initialization_data SQL files"
                }
            )
            session.commit()
            logger.info("Marked deletion as executed in deletion_status table")
        except Exception as e:
            logger.error(f"Error marking deletion as executed: {e}")
            session.rollback()

def has_table_alteration_been_executed() -> bool:
    """
    Check if the one-time table alteration has already been executed by checking database.
    """
    ensure_deletion_status_table()
    with get_sync_session() as session:
        try:
            result = session.execute(
                text("SELECT 1 FROM deletion_status WHERE operation_name = :name"),
                {"name": "table_alteration_add_description"}
            )
            executed = result.scalar_one_or_none() is not None
            if executed:
                logger.info("Table alteration has already been executed (found record in deletion_status table)")
            else:
                logger.info("Table alteration has not been executed yet (no record in deletion_status table)")
            return executed
        except Exception as e:
            logger.warning(f"Error checking table alteration status: {e}")
            return False

def mark_table_alteration_as_executed():
    """
    Mark the one-time table alteration as executed in database.
    """
    with get_sync_session() as session:
        try:
            session.execute(
                text("""
                    INSERT INTO deletion_status (operation_name, description) 
                    VALUES (:name, :desc) 
                    ON CONFLICT (operation_name) DO NOTHING
                """),
                {
                    "name": "table_alteration_add_description",
                    "desc": "Added operator_description and config_description columns"
                }
            )
            session.commit()
            logger.info("Marked table alteration as executed in deletion_status table")
        except Exception as e:
            logger.error(f"Error marking table alteration as executed: {e}")
            session.rollback()

def alter_tables_add_description_columns():
    """
    Add description columns to operator_info and operator_config tables.
    This operation will only be executed once on first startup.
    Fields are added as the last column in each table, type is TEXT, nullable.
    Raises exception if any ALTER TABLE fails.
    """
    success_count = 0
    errors = []
    
    with get_sync_session() as session:
        try:
            logger.info("Adding operator_description column to operator_info table...")
            session.execute(text("""
                ALTER TABLE operator_info 
                ADD COLUMN IF NOT EXISTS operator_description TEXT COLLATE "pg_catalog"."default" NULL
            """))
            session.commit()
            logger.info("Successfully added operator_description column to operator_info")
            success_count += 1
        except Exception as e:
            logger.warning(f"Error adding operator_description column: {e}")
            session.rollback()
            errors.append(f"operator_info: {e}")
        
        try:
            logger.info("Adding config_description column to operator_config table...")
            session.execute(text("""
                ALTER TABLE operator_config 
                ADD COLUMN IF NOT EXISTS config_description TEXT COLLATE "pg_catalog"."default" NULL
            """))
            session.commit()
            logger.info("Successfully added config_description column to operator_config")
            success_count += 1
        except Exception as e:
            logger.warning(f"Error adding config_description column: {e}")
            session.rollback()
            errors.append(f"operator_config: {e}")
    
    if errors:
        error_msg = f"Failed to alter {len(errors)} table(s): {'; '.join(errors)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    logger.info(f"Successfully altered {success_count} tables")

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

def extract_ids_from_sql(sql_file_path: str) -> list[int]:
    """
    Extract all id primary key values from INSERT statements in SQL file.
    """
    ids = []
    try:
        insert_statements = extract_insert_statements(sql_file_path)
        for statement in insert_statements:
            match = re.search(r'VALUES\s*\((\d+)', statement, re.IGNORECASE)
            if match:
                ids.append(int(match.group(1)))
        logger.info(f"Extracted {len(ids)} IDs from {sql_file_path}")
        return ids
    except Exception as e:
        logger.error(f"Error extracting IDs: {e}")
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

def delete_by_ids(table_name: str, ids: list[int]):
    """
    Delete data from table by id list. Ignore if id doesn't exist.
    """
    if not ids:
        logger.info(f"No IDs to delete, skipping deletion step")
        return
    
    with get_sync_session() as session:
        deleted_count = 0
        not_found_count = 0
        error_count = 0
        
        for id_value in ids:
            try:
                result = session.execute(
                    text(f"DELETE FROM {table_name} WHERE id = :id"),
                    {"id": id_value}
                )
                session.commit()
                
                if result.rowcount > 0:
                    deleted_count += 1
                    logger.debug(f"Deleted id={id_value} from table '{table_name}'")
                else:
                    not_found_count += 1
                    logger.debug(f"ID {id_value} not found in table '{table_name}', skipping")
                    
            except Exception as e:
                error_count += 1
                logger.warning(f"Error deleting id={id_value} from table '{table_name}': {e}")
                session.rollback()
                continue
        
        logger.info(f"Table '{table_name}': Deleted {deleted_count}/{len(ids)} records (not found: {not_found_count}, errors: {error_count})")

def delete_table_data_by_ids(table_name: str):
    """
    Delete data from table based on ids found in the corresponding SQL file.
    This function will not interrupt execution even if deletion fails.
    """
    try:
        project_root = get_project_root()
        sql_file_path = os.path.join(project_root, 'data_server', 'database', 'Initialization_data', f'{table_name}.sql')
        
        ids_to_delete = extract_ids_from_sql(sql_file_path)
        
        if ids_to_delete:
            logger.info(f"Starting deletion for table '{table_name}' ({len(ids_to_delete)} IDs)")
            delete_by_ids(table_name, ids_to_delete)
        else:
            logger.info(f"No IDs found for deletion in '{table_name}', skipping deletion step")
    except Exception as e:
        logger.warning(f"Error during deletion process for table '{table_name}': {e}")
        logger.warning(f"Continuing with remaining operations...")

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
