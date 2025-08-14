

import os
import glob
import re
from loguru import logger
from sqlalchemy import text
from .session import get_sync_session


def _execute_sql_file(sql_file):
    logger.info(f"Executing initialization script: {os.path.basename(sql_file)}")
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        insert_statements = extract_insert_statements(sql_content)
        successful_count = 0
        skipped_count = 0
        
        for statement in insert_statements:
            if statement.strip():
                with get_sync_session() as session:
                    try:
                        with session.begin():
                            processed_statement = preprocess_sql_statement(statement)
                            session.execute(text(processed_statement))
                        successful_count += 1
                    except Exception as e:
                        if ("duplicate key" in str(e).lower() or 
                            "already exists" in str(e).lower() or
                            "unique constraint" in str(e).lower() or
                            "重复键" in str(e) or
                            "唯一约束" in str(e) or
                            "已经存在" in str(e)):
                            logger.debug(f"Skipping duplicate data in {os.path.basename(sql_file)}: {str(e)[:100]}...")
                            skipped_count += 1
                            continue
                        elif "syntax error" in str(e).lower() or "unterminated" in str(e).lower():
                            logger.warning(f"Skipping malformed SQL statement in {os.path.basename(sql_file)}: {str(e)[:100]}...")
                            logger.debug(f"Problematic statement: {statement[:300]}...")
                            skipped_count += 1
                            continue
                        else:
                            logger.error(f"Error executing statement in {os.path.basename(sql_file)}: {e}")
                            logger.error(f"Failed statement: {statement[:200]}...")
                            continue
        
        logger.info(f"Processed {os.path.basename(sql_file)}: {successful_count} successful, {skipped_count} skipped")
    except Exception as e:
        logger.error(f"Error processing file {sql_file}: {e}")

def initialize_table(table_name: str):
    """
    Initializes a single table by finding and executing its corresponding .sql file.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        init_data_dir = os.path.join(current_dir, "Initialization_data")
        
        if not os.path.exists(init_data_dir):
            logger.warning(f"Initialization data directory not found: {init_data_dir}")
            return

        # Find the sql file corresponding to the table name
        # Look for exact match: table_name.sql
        target_filename = f"{table_name}.sql"
        sql_file = os.path.join(init_data_dir, target_filename)
        
        if not os.path.exists(sql_file):
            sql_file = None

        if sql_file:
            _execute_sql_file(sql_file)
        else:
            logger.warning(f"No SQL initialization file found for table: {table_name}")

    except Exception as e:
        logger.error(f"Failed to initialize table {table_name}: {e}")
        raise

def execute_initialization_scripts():
    """
    Execute all SQL scripts for database initialization.
    """
    try:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        init_data_dir = os.path.join(current_dir, "Initialization_data")
        
        if not os.path.exists(init_data_dir):
            logger.warning(f"Initialization data directory not found: {init_data_dir}")
            return
        
        sql_files = glob.glob(os.path.join(init_data_dir, "*.sql"))
        
        if not sql_files:
            logger.info("No SQL initialization files found")
            return
        
        logger.info(f"Found {len(sql_files)} SQL initialization files for full initialization.")
        
        for sql_file in sorted(sql_files):
            _execute_sql_file(sql_file)
                
        logger.info("Database full initialization scan completed successfully")
                
    except Exception as e:
        logger.error(f"Failed to execute initialization scripts: {e}")
        raise


def preprocess_sql_statement(statement):

    try:


        

        if not statement.upper().strip().startswith('INSERT INTO'):
            return statement
        

        # INSERT INTO "table" VALUES (val1, val2, 'complex_string', val4, ...);
        

        values_match = re.search(r'VALUES\s*\((.*)\);?\s*$', statement, re.IGNORECASE | re.DOTALL)
        if not values_match:
            return statement
        
        values_part = values_match.group(1)
        


        fixed_values = fix_quoted_strings(values_part).replace('\\n', '\n')
        

        table_part = statement[:values_match.start()]
        fixed_statement = f"{table_part}VALUES ({fixed_values});"
        
        return fixed_statement
        
    except Exception as e:
        logger.warning(f"Error preprocessing SQL statement: {e}")
        return statement


def fix_quoted_strings(values_part):

    try:


        
        result = []
        i = 0
        current_token = ""
        in_string = False
        string_content = ""
        paren_depth = 0
        
        while i < len(values_part):
            char = values_part[i]
            
            if char == '(' and not in_string:
                paren_depth += 1
                current_token += char
            elif char == ')' and not in_string:
                paren_depth -= 1
                current_token += char
            elif char == "'" and not in_string:

                in_string = True
                string_content = ""
            elif char == "'" and in_string:

                if i + 1 < len(values_part) and values_part[i + 1] == "'":

                    string_content += "''"
                    i += 1
                else:

                    in_string = False

                    if ("''" in string_content or 
                        "href=" in string_content or 
                        len(string_content) > 100 or
                        any(c in string_content for c in ['<', '>', '"', '\\'])):

                        dollar_tag = f"$tag{len(result)}$"
                        current_token += f"{dollar_tag}{string_content}{dollar_tag}"
                    else:

                        current_token += f"'{string_content}'"
                    string_content = ""
            elif in_string:
                string_content += char
            elif char == ',' and paren_depth == 0 and not in_string:
                result.append(current_token.strip())
                current_token = ""
            else:
                current_token += char
            
            i += 1
        

        if current_token.strip():
            result.append(current_token.strip())
        
        return ', '.join(result)
        
    except Exception as e:
        logger.warning(f"Error fixing quoted strings: {e}")
        return values_part


def extract_insert_statements(sql_content):


    sql_content = re.sub(r'--.*?\n', '\n', sql_content)
    sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    

    insert_statements = []
    lines = sql_content.split('\n')
    current_statement = ""
    in_insert = False
    paren_count = 0
    quote_count = 0
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            

        if line.upper().startswith('INSERT INTO'):
            in_insert = True
            current_statement = line

            paren_count = line.count('(') - line.count(')')
            quote_count = line.count("'") % 2
            

            if line.endswith(';') and paren_count == 0 and quote_count == 0:
                insert_statements.append(current_statement)
                current_statement = ""
                in_insert = False
        elif in_insert:

            current_statement += " " + line
            paren_count += line.count('(') - line.count(')')
            quote_count = (quote_count + line.count("'")) % 2
            

            if line.endswith(';') and paren_count == 0 and quote_count == 0:
                insert_statements.append(current_statement)
                current_statement = ""
                in_insert = False
    

    if current_statement and in_insert:
        insert_statements.append(current_statement)
    
    return insert_statements
