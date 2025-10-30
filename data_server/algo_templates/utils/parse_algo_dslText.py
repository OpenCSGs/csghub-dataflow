import yaml
from collections import deque, defaultdict
from loguru import logger


def convert_raw_to_processed(raw_yaml: str) -> str:


    data = yaml.safe_load(raw_yaml)


    nodes = data.get('process', {})
    edges = data.get('edges', [])


    id_to_node = {node['id']: node for node in nodes.values()}



    adj = defaultdict(list)
    in_degree = defaultdict(int)


    for node_id in id_to_node.keys():
        in_degree[node_id] = 0

    for edge in edges:
        source = edge['source']
        target = edge['target']

        if source not in id_to_node:
            logger.error(f"edges中引用的source节点 '{source}' 不存在于process中！")
            raise ValueError(f"edges中引用的source节点 '{source}' 不存在于process中！")
        if target not in id_to_node:
            logger.error(f"edges中引用的target节点 '{target}' 不存在于process中！")
            raise ValueError(f"edges中引用的target节点 '{target}' 不存在于process中！")

        adj[source].append(target)
        in_degree[target] += 1


    queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])
    process_order = []

    while queue:
        current_node = queue.popleft()
        process_order.append(current_node)


        for next_node in adj[current_node]:
            in_degree[next_node] -= 1
            if in_degree[next_node] == 0:
                queue.append(next_node)


    if len(process_order) != len(id_to_node):
        raise ValueError("数据流中存在环，无法确定处理顺序！")


    process_list = []
    for node_id in process_order:
        node = id_to_node[node_id]
        operator_name = node['operator_name']
        configs = node.get('configs', [])


        config_dict = {}
        for config in configs:
            param_name = config['config_name']
            param_value = config['final_value']
            

            # handle_numeric_ids_of_string_type
            if param_value and isinstance(param_value, str) and param_value.isdigit():
                from data_server.operator.mapper.operator_mapper import get_operator_config_select_option_by_id
                from data_server.database.session import get_sync_session
                try:
                    db = get_sync_session()
                    option_record = get_operator_config_select_option_by_id(db, int(param_value))
                    if option_record and hasattr(option_record, 'name'):
                        param_value = option_record.name
                    db.close()
                except Exception as e:
                    print(f"查询operator_config_select_options失败: {e}")
                    pass
            # handle_string_array_format_like_"['1','2']"_or_"[''1'', ''2'']"
            elif param_value and isinstance(param_value, str) and param_value.startswith('[') and param_value.endswith(']'):
                try:
                    import ast
                    # try_to_parse_the_string_array
                    # First, handle the double single quote escape format [" 1 ", "2"] -> [" 1 ", "2"]
                    normalized_value = param_value.replace("''", "'")
                    parsed_list = ast.literal_eval(normalized_value)
                    if isinstance(parsed_list, list):
                        from data_server.operator.mapper.operator_mapper import get_operator_config_select_option_by_id
                        from data_server.database.session import get_sync_session
                        converted_list = []
                        for item in parsed_list:
                            if isinstance(item, str) and item.isdigit():
                                try:
                                    db = get_sync_session()
                                    option_record = get_operator_config_select_option_by_id(db, int(item))
                                    if option_record and hasattr(option_record, 'name'):
                                        converted_list.append(option_record.name)
                                    else:
                                        converted_list.append(item)
                                    db.close()
                                except Exception as e:
                                    print(f"查询operator_config_select_options失败: {e}")
                                    converted_list.append(item)
                            else:
                                converted_list.append(item)
                        param_value = converted_list
                except (ValueError, SyntaxError) as e:
                    print(f"解析字符串数组失败: {e}")
                    pass
            # handle_the_numeric_id_of_list_type
            elif param_value and isinstance(param_value, list):
                from data_server.operator.mapper.operator_mapper import get_operator_config_select_option_by_id
                from data_server.database.session import get_sync_session
                converted_list = []
                for item in param_value:
                    if isinstance(item, str) and item.isdigit():
                        try:
                            db = get_sync_session()
                            option_record = get_operator_config_select_option_by_id(db, int(item))
                            if option_record and hasattr(option_record, 'name'):
                                converted_list.append(option_record.name)
                            else:
                                converted_list.append(item)
                            db.close()
                        except Exception as e:
                            print(f"查询operator_config_select_options失败: {e}")
                            converted_list.append(item)
                    else:
                        converted_list.append(item)
                param_value = converted_list


            if param_value is None:
                config_dict[param_name] = None
            elif isinstance(param_value, str) and param_value.lower() == 'true':
                config_dict[param_name] = True
            elif isinstance(param_value, str) and param_value.lower() == 'false':
                config_dict[param_name] = False
            elif isinstance(param_value, list):
                list_str = str(param_value)
                config_dict[param_name] = list_str
            else:
                config_dict[param_name] = param_value


        process_list.append({operator_name: config_dict})



    result = data.copy()
    result.pop('process', None)
    result.pop('edges', None)
    result['process'] = process_list


    yaml_str = yaml.dump(result, sort_keys=False, allow_unicode=True, default_flow_style=False, indent=2, width=float("inf"))

    # Convert the list in string format back to YAML list format
    import re
    # Match strings in the form of "['item1', 'item2']" and convert them to YAML list format
    def convert_string_list_to_yaml(match):
        param_name = match.group(1)
        list_content = match.group(2)
        # restore_double_single_quotes_to_single_quotes
        list_content = list_content.replace("''", "'")
        return f"{param_name}: {list_content}"
    
    # regular_expressions_match_lists_in_string_format
    # 匹配单引号包裹的字符串数组：'[...]'
    pattern1 = r"(\s+\w+):\s*'(\[.*?\])'"
    yaml_str = re.sub(pattern1, convert_string_list_to_yaml, yaml_str)
    
    # 匹配双引号包裹的字符串数组："[...]"
    pattern2 = r'(\s+\w+):\s*"(\[.*?\])"'
    yaml_str = re.sub(pattern2, convert_string_list_to_yaml, yaml_str)

    yaml_str = yaml_str.replace(": {}", ":")
    

    lines = yaml_str.split('\n')
    formatted_lines = []
    in_process_section = False
    
    for line in lines:
        if line.strip() == 'process:':
            in_process_section = True
            formatted_lines.append(line)
        elif in_process_section and line.strip().startswith('- ') and ':' in line:

            if not line.startswith('  '):
                line = '  ' + line
            formatted_lines.append(line)
        elif in_process_section and line.strip() and not line.strip().startswith('- '):

            if line.startswith('      '):

                formatted_lines.append(line)
            elif line.startswith('    '):

                formatted_lines.append('      ' + line[4:])
            elif line.startswith('  '):

                formatted_lines.append('      ' + line[2:])
            else:

                formatted_lines.append('      ' + line)
        else:

            formatted_lines.append(line)

            if in_process_section and line.strip() and not line.startswith('  ') and not line.startswith('    '):
                in_process_section = False
    
    yaml_str = '\n'.join(formatted_lines)

    return yaml_str

if __name__ == '__main__':
    yaml_str = """
name: 数据生成
description: 该模版用于数据增强，旨在扩展用户的提示数据，以帮助模型更好地理解任务。
type: data_refine
process:
  extract_qa_mapper:
    id: node_1755500078644_157
    operator_id: '11'
    operator_type: Mapper
    operator_name: extract_qa_mapper
    display_name: 问答对提取
    icon: >-
      data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF4AAABeCAYAAACq0qNuAAAACXBIWXMAAAsTAAALEwEAmpwYAAADeWlUWHRYTUw6Y29tLmFkb2JlLnhtcAAAAAAAPD94cGFja2V0IGJlZ2luPSLvu78iIGlkPSJXNU0wTXBDZWhpSHpyZVN6TlRjemtjOWQiPz4gPHg6eG1wbWV0YSB4bWxuczp4PSJhZG9iZTpuczptZXRhLyIgeDp4bXB0az0iQWRvYmUgWE1QIENvcmUgOS4xLWMwMDEgNzkuMTQ2Mjg5OTc3NywgMjAyMy8wNi8yNS0yMzo1NzoxNCAgICAgICAgIj4gPHJkZjpSREYgeG1sbnM6cmRmPSJodHRwOi8vd3d3LnczLm9yZy8xOTk5LzAyLzIyLXJkZi1zeW50YXgtbnMjIj4gPHJkZjpEZXNjcmlwdGlvbiByZGY6YWJvdXQ9IiIgeG1sbnM6eG1wTU09Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC9tbS8iIHhtbG5zOnN0UmVmPSJodHRwOi8vbnMuYWRvYmUuY29tL3hhcC8xLjAvc1R5cGUvUmVzb3VyY2VSZWYjIiB4bWxuczp4bXA9Imh0dHA6Ly9ucy5hZG9iZS5jb20veGFwLzEuMC8iIHhtcE1NOk9yaWdpbmFsRG9jdW1lbnRJRD0ieG1wLmRpZDo2ZDYyZmIwNC03ODY4LTQxZjktYmVkMy1iYzE0YWM5MDgxYTciIHhtcE1NOkRvY3VtZW50SUQ9InhtcC5kaWQ6OUQwNjhCRURBNTc1MkY0NTlBNjNEQzNEQTBBNkVBQTUiIHhtcE1NOkluc3RhbmNlSUQ9InhtcC5paWQ6NDI2M0Q2N0NEQ0Y2QzQ0MUE2MjlGMTdDMURBMjkyNTAiIHhtcDpDcmVhdG9yVG9vbD0iQWRvYmUgUGhvdG9zaG9wIDI1LjEgKE1hY2ludG9zaCkiPiA8eG1wTU06RGVyaXZlZEZyb20gc3RSZWY6aW5zdGFuY2VJRD0ieG1wLmlpZDpjODlkNzU2MC00NjcxLTQ1OTYtYTY5ZS0zMDNiMmEzYTMxZmUiIHN0UmVmOmRvY3VtZW50SUQ9InhtcC5kaWQ6NmQ2MmZiMDQtNzg2OC00MWY5LWJlZDMtYmMxNGFjOTA4MWE3Ii8+IDwvcmRmOkRlc2Ny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
    position:
      x: 356.333251953125
      'y': 278.83332347869873
    configs:
      - id: 16
        operator_id: 11
        config_name: hf_model
        config_type: select
        select_options:
          - value: '18'
            label: alibaba-pai/pai-qwen1_5-7b-doc2qa
        default_value: '18'
        is_required: false
        is_spinner: false
        final_value: '[''41'', ''42'', ''43'', ''44'', ''45'']'
        display_name: 模型名称
edges: []

"""
    print(convert_raw_to_processed(yaml_str))