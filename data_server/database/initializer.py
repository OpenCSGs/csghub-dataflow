"""
数据库初始化模块
负责执行SQL初始化脚本，处理数据插入和SQL语法修复
"""

import os
import glob
import re
from loguru import logger
from sqlalchemy import text
from .session import get_sync_session


def execute_initialization_scripts():
    """
    Execute the SQL script for database initialization
    From data_server/database/Initialization_data directory reads all. SQL file
    And execute the INSERT statement within it to initialize the data
    """
    try:
        # Obtain the path of the initialization script directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        init_data_dir = os.path.join(current_dir, "Initialization_data")
        
        if not os.path.exists(init_data_dir):
            logger.warning(f"Initialization data directory not found: {init_data_dir}")
            return
        
        # get All Sql Files
        sql_files = glob.glob(os.path.join(init_data_dir, "*.sql"))
        
        if not sql_files:
            logger.info("No SQL initialization files found")
            return
        
        logger.info(f"Found {len(sql_files)} SQL initialization files")
        
        for sql_file in sorted(sql_files):  # sort_by_file_name_to_ensure_the_execution_order
            logger.info(f"Executing initialization script: {os.path.basename(sql_file)}")
            
            try:
                with open(sql_file, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
                
                # Extract the INSERT statement (ignore table creation and other statements)
                insert_statements = extract_insert_statements(sql_content)
                
                successful_count = 0
                skipped_count = 0
                
                for statement in insert_statements:
                    if statement.strip():
                        # Execute each INSERT statement in its own transaction
                        with get_sync_session() as session:
                            try:
                                with session.begin():
                                    # 预处理SQL语句以处理引号问题
                                    processed_statement = preprocess_sql_statement(statement)
                                    session.execute(text(processed_statement))
                                successful_count += 1
                            except Exception as e:
                                # If it is a repeated key error, skip (the data already exists)
                                if ("duplicate key" in str(e).lower() or 
                                    "already exists" in str(e).lower() or
                                    "unique constraint" in str(e).lower() or
                                    "重复键" in str(e) or  # adapt-to-chinese-error-messages
                                    "唯一约束" in str(e) or # adapt-to-chinese-error-messages
                                    "已经存在" in str(e)): # adapt-to-chinese-error-messages
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
                                    # Continue with next statement instead of raising
                                    continue
                
                logger.info(f"Processed {os.path.basename(sql_file)}: {successful_count} successful, {skipped_count} skipped")
                
            except Exception as e:
                logger.error(f"Error processing file {sql_file}: {e}")
                # Continue with next file instead of raising
                continue
                
        logger.info("Database initialization completed successfully")
                
    except Exception as e:
        logger.error(f"Failed to execute initialization scripts: {e}")
        raise


def preprocess_sql_statement(statement):
    """
    预处理SQL语句，修复引号转义问题
    """
    try:
        # 使用PostgreSQL的美元引用来处理复杂字符串
        # 这可以避免引号转义问题
        
        # 检查是否是INSERT语句
        if not statement.upper().strip().startswith('INSERT INTO'):
            return statement
        
        # 分析INSERT语句结构
        # INSERT INTO "table" VALUES (val1, val2, 'complex_string', val4, ...);
        
        # 使用正则表达式找到VALUES部分
        values_match = re.search(r'VALUES\s*\((.*)\);?\s*$', statement, re.IGNORECASE | re.DOTALL)
        if not values_match:
            return statement
        
        values_part = values_match.group(1)
        
        # 替换有问题的字符串值
        # 找到所有用单引号包围的字符串
        fixed_values = fix_quoted_strings(values_part)
        
        # 重构SQL语句
        table_part = statement[:values_match.start()]
        fixed_statement = f"{table_part}VALUES ({fixed_values});"
        
        return fixed_statement
        
    except Exception as e:
        logger.warning(f"Error preprocessing SQL statement: {e}")
        return statement


def fix_quoted_strings(values_part):
    """
    修复VALUES部分中的引号字符串
    """
    try:
        # 这是一个复杂的解析任务，我们使用一个简化的方法
        # 将有问题的字符串转换为美元引用格式
        
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
                # 开始字符串
                in_string = True
                string_content = ""
            elif char == "'" and in_string:
                # 检查是否是转义的引号
                if i + 1 < len(values_part) and values_part[i + 1] == "'":
                    # 这是转义的引号，添加到字符串内容
                    string_content += "''"
                    i += 1  # 跳过下一个引号
                else:
                    # 字符串结束
                    in_string = False
                    # 使用美元引用来包装复杂字符串
                    if ("''" in string_content or 
                        "href=" in string_content or 
                        len(string_content) > 100 or
                        any(c in string_content for c in ['<', '>', '"', '\\'])):
                        # 使用美元引用
                        dollar_tag = f"$tag{len(result)}$"
                        current_token += f"{dollar_tag}{string_content}{dollar_tag}"
                    else:
                        # 普通字符串，保持原样
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
        
        # 添加最后一个token
        if current_token.strip():
            result.append(current_token.strip())
        
        return ', '.join(result)
        
    except Exception as e:
        logger.warning(f"Error fixing quoted strings: {e}")
        return values_part


def extract_insert_statements(sql_content):
    """
    从SQL内容中提取INSERT语句
    """
    # 移除注释
    sql_content = re.sub(r'--.*?\n', '\n', sql_content)
    sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
    
    # 更精确的INSERT语句提取
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
            
        # 检测INSERT语句开始
        if line.upper().startswith('INSERT INTO'):
            in_insert = True
            current_statement = line
            # 计算括号和引号
            paren_count = line.count('(') - line.count(')')
            quote_count = line.count("'") % 2
            
            # 如果这一行就结束了（以分号结尾且括号平衡）
            if line.endswith(';') and paren_count == 0 and quote_count == 0:
                insert_statements.append(current_statement)
                current_statement = ""
                in_insert = False
        elif in_insert:
            # 继续构建INSERT语句
            current_statement += " " + line
            paren_count += line.count('(') - line.count(')')
            quote_count = (quote_count + line.count("'")) % 2
            
            # 检查是否语句结束
            if line.endswith(';') and paren_count == 0 and quote_count == 0:
                insert_statements.append(current_statement)
                current_statement = ""
                in_insert = False
    
    # 如果还有未完成的语句，也添加进去
    if current_statement and in_insert:
        insert_statements.append(current_statement)
    
    return insert_statements
