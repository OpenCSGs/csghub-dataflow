import os
import re
import sqlparse
from loguru import logger
from data_celery.utils import get_project_root
from sqlalchemy import text
from data_server.database.session import get_sync_session

# Initialization data version - Update this version when modifying SQL files in Initialization_data directory
INIT_DATA_VERSION = "1.0.0"

def get_current_db_version() -> str:
    """
    Get the current initialization data version stored in database.
    Returns the latest version (ordered by id DESC) or 'None' if no version is found.
    """
    ensure_deletion_status_table()
    with get_sync_session() as session:
        try:
            result = session.execute(
                text("SELECT version FROM deletion_status ORDER BY id DESC LIMIT 1")
            )
            version = result.scalar_one_or_none()
            return version if version else "None"
        except Exception as e:
            logger.warning(f"Error getting current database version: {e}")
            return "Error"

def ensure_deletion_status_table():
    """
    Create deletion_status table if it doesn't exist.
    Simplified table structure with only necessary fields:
    - id: Primary key
    - version: Initialization data version
    - description: Optional description
    - created_at: Timestamp when this version was initialized (for version history tracking)
    
    Also handles migration from old table structure (removes operation_name and executed_at).
    """
    with get_sync_session() as session:
        try:
            # Create table if not exists (new simplified structure with created_at)
            logger.info("Ensuring deletion_status table exists...")
            session.execute(text("""
                CREATE TABLE IF NOT EXISTS deletion_status (
                    id SERIAL PRIMARY KEY,
                    version VARCHAR(50),
                    description TEXT,
                    created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
                )
            """))
            session.commit()
            logger.info("deletion_status table ensured")
            
            # Add version column if it doesn't exist (for backward compatibility)
            try:
                logger.info("Ensuring version column exists...")
                session.execute(text("""
                    ALTER TABLE deletion_status 
                    ADD COLUMN IF NOT EXISTS version VARCHAR(50)
                """))
                session.commit()
                logger.info("version column ensured")
            except Exception as e:
                logger.debug(f"Could not add version column: {e}")
                session.rollback()
            
            # Add created_at column if it doesn't exist (for backward compatibility)
            try:
                logger.info("Ensuring created_at column exists...")
                session.execute(text("""
                    ALTER TABLE deletion_status 
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT (now() AT TIME ZONE 'Asia/Shanghai')
                """))
                session.commit()
                logger.info("created_at column ensured")
            except Exception as e:
                logger.debug(f"Could not add created_at column: {e}")
                session.rollback()
            
            # Migration: Remove old columns if they exist (for backward compatibility)
            # This ensures smooth upgrade from old version
            logger.info("Checking for old columns to remove...")
            
            # Check and drop operation_name column
            try:
                session.execute(text("""
                    ALTER TABLE deletion_status 
                    DROP COLUMN IF EXISTS operation_name
                """))
                session.commit()
                logger.info("Old column 'operation_name' removed (if existed)")
            except Exception as e:
                logger.debug(f"Could not drop operation_name: {e}")
                session.rollback()
            
            # Check and drop executed_at column
            try:
                session.execute(text("""
                    ALTER TABLE deletion_status 
                    DROP COLUMN IF EXISTS executed_at
                """))
                session.commit()
                logger.info("Old column 'executed_at' removed (if existed)")
            except Exception as e:
                logger.debug(f"Could not drop executed_at: {e}")
                session.rollback()
            
            # Clean up old records with NULL version (from previous schema)
            # This removes legacy records that don't have version information
            try:
                result = session.execute(text("DELETE FROM deletion_status WHERE version IS NULL"))
                deleted_count = result.rowcount
                session.commit()
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old record(s) with NULL version")
            except Exception as e:
                logger.debug(f"Could not clean up old records: {e}")
                session.rollback()
            
            logger.info("Table structure migration completed")
            
        except Exception as e:
            logger.error(f"Error creating/updating deletion_status table: {e}")
            session.rollback()

def has_deletion_been_executed() -> bool:
    """
    Check if the one-time deletion has already been executed by checking database version.
    Returns False if:
    - No record exists in deletion_status table
    - Version field is NULL (old data without version)
    - Version doesn't match current INIT_DATA_VERSION
    This ensures re-initialization when SQL files are updated.
    
    Execution order guarantee:
    1. First call ensure_deletion_status_table() to ensure correct table structure
    2. Then query the version field value
    This way even old users (with old fields in table) can migrate correctly
    """
    # Step 1: Ensure deletion_status table structure is correct
    # For old users, automatically removes operation_name and executed_at fields, and adds created_at
    ensure_deletion_status_table()
    
    # Step 2: Query version number (get the latest version from deletion_status table)
    with get_sync_session() as session:
        try:
            result = session.execute(
                text("SELECT version FROM deletion_status ORDER BY id DESC LIMIT 1")
            )
            db_version = result.scalar_one_or_none()
            
            # scalar_one_or_none() returns None in these cases:
            # 1. No records in the table
            # 2. Has record but version field is NULL (old users after upgrade)
            if db_version is None:
                logger.info(f"No version record found or version is NULL in database. Current code version: {INIT_DATA_VERSION}. Will execute re-initialization.")
                return False
            elif db_version != INIT_DATA_VERSION:
                logger.info(f"Version mismatch detected! Database version: {db_version}, Code version: {INIT_DATA_VERSION}. Will execute re-initialization.")
                return False
            else:
                logger.info(f"Version matched: {db_version}. Initialization already executed for this version.")
                return True
        except Exception as e:
            # Any exception returns False, triggering initialization (safety strategy)
            logger.warning(f"Error checking deletion status: {e}")
            logger.warning("Will trigger re-initialization as a safety measure.")
            return False

def mark_deletion_as_executed():
    """
    Mark the one-time deletion as executed in database with current version.
    Appends a new record to keep version history (does not delete old records).
    Each initialization creates a new record with timestamp.
    """
    with get_sync_session() as session:
        try:
            # Insert new record with current version (append, not replace)
            # created_at will be automatically set to CURRENT_TIMESTAMP
            session.execute(
                text("""
                    INSERT INTO deletion_status (version, description) 
                    VALUES (:version, :desc)
                """),
                {
                    "version": INIT_DATA_VERSION,
                    "desc": f"Initialization data version {INIT_DATA_VERSION} from Initialization_data SQL files"
                }
            )
            session.commit()
            logger.info(f"Marked deletion as executed with version {INIT_DATA_VERSION} in deletion_status table (appended to history)")
        except Exception as e:
            logger.error(f"Error marking deletion as executed: {e}")
            session.rollback()

def has_table_alteration_been_executed() -> bool:
    """
    Check if the one-time table alteration has already been executed.
    Since we use ALTER TABLE ... ADD COLUMN IF NOT EXISTS, we can check column existence directly.
    Returns True if columns already exist (no need to execute again).
    """
    with get_sync_session() as session:
        try:
            # Check if operator_description column exists in operator_info table
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'operator_info' 
                AND column_name = 'operator_description'
            """))
            operator_col_exists = result.scalar_one_or_none() is not None
            
            # Check if config_description column exists in operator_config table
            result = session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'operator_config' 
                AND column_name = 'config_description'
            """))
            config_col_exists = result.scalar_one_or_none() is not None
            
            both_exist = operator_col_exists and config_col_exists
            
            if both_exist:
                logger.info("Table alteration columns already exist, skipping...")
            else:
                logger.info("Table alteration columns do not exist, will execute...")
            
            return both_exist
        except Exception as e:
            logger.warning(f"Error checking table alteration status: {e}")
            return False

def mark_table_alteration_as_executed():
    """
    Mark the one-time table alteration as executed.
    Since we check column existence directly, this function is now a no-op.
    Kept for compatibility.
    """
    logger.info("Table alteration completed (no status record needed)")
    pass

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

def update_sequence_for_table(table_name: str):
    """
    Update sequence based on table data to avoid primary key conflicts.
    
    Logic:
    - If max(id) >= 1000 (has user data): set sequence to max(id) + 1
    - If max(id) < 1000 (only SQL data): set sequence to 1000
    - If table is empty: set sequence to 1000
    """
    sequence_name = f"{table_name}_id_seq"
    
    with get_sync_session() as session:
        try:
            # Query current max id in table
            result = session.execute(
                text(f"SELECT MAX(id) FROM {table_name}")
            )
            max_id = result.scalar()
            
            # Determine next sequence value
            if max_id is None:
                # Empty table: start from 1000
                next_id = 1000
                logger.info(f"Table '{table_name}' is empty, setting sequence to 1000")
            elif max_id >= 1000:
                # Has user data (id >= 1000): start from max + 1
                next_id = max_id + 1
                logger.info(f"Table '{table_name}' has user data (max_id={max_id}), setting sequence to {next_id}")
            else:
                # Only SQL data (max_id < 1000): start from 1000
                next_id = 1000
                logger.info(f"Table '{table_name}' only has SQL data (max_id={max_id}), setting sequence to 1000")
            
            # Update sequence
            session.execute(
                text(f"ALTER SEQUENCE {sequence_name} RESTART WITH :next_id"),
                {"next_id": next_id}
            )
            session.commit()
            
            logger.info(f"Successfully updated sequence '{sequence_name}' to start from {next_id}")
        
        except Exception as e:
            logger.warning(f"Error updating sequence for '{table_name}': {e}")
            session.rollback()

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

    # After inserting data, update sequence to avoid primary key conflicts
    # Dynamically sets sequence based on actual data in table
    update_sequence_for_table(table_name)
