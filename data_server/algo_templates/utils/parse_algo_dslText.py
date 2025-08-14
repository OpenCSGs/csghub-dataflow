import yaml
from collections import deque, defaultdict


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


            if param_value is None:
                config_dict[param_name] = None
            elif isinstance(param_value, str) and param_value.lower() == 'true':
                config_dict[param_name] = True
            elif isinstance(param_value, str) and param_value.lower() == 'false':
                config_dict[param_name] = False
            else:
                config_dict[param_name] = param_value


        process_list.append({operator_name: config_dict})



    result = data.copy()
    result.pop('process', None)
    result.pop('edges', None)
    result['process'] = process_list


    yaml_str = yaml.dump(result, sort_keys=False, allow_unicode=True, default_flow_style=False, indent=2, width=float("inf"))


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
name: test
description: 模板描述
type: data_refine
process:
  chinese_convert_mapper:
    id: node_1753511328856_55
    operator_id: '4339774200'
    operator_type: Mapper
    operator_name: chinese_convert_mapper
    icon: null
    position:
      x: 265.5
      'y': 223
    configs:
      - id: 4339774201
        operator_id: 4339774200
        config_name: mode
        config_type: select
        select_options:
          - value: '4318984200'
            label: s2t
          - value: '4319114200'
            label: t2s
          - value: '4319204200'
            label: s2tw
          - value: '4319274200'
            label: tw2s
          - value: '4319324200'
            label: s2hk
          - value: '4319374200'
            label: hk2s
          - value: '4319424200'
            label: s2twp
          - value: '4319484200'
            label: tw2sp
          - value: '4319534200'
            label: t2tw
          - value: '4319584200'
            label: tw2t
          - value: '4319624200'
            label: hk2t
          - value: '4319674200'
            label: t2hk
          - value: '4319714200'
            label: t2jp
          - value: '4319754200'
            label: jp2t
        default_value: t2s
        is_required: true
        is_spinner: false
        final_value: '4319274200'
  clean_email_mapper:
    id: node_1753511329900_846
    operator_id: '4340834200'
    operator_type: Mapper
    operator_name: clean_email_mapper
    icon: null
    position:
      x: 467.5
      'y': 220
    configs: []
  flagged_words_filter:
    id: node_1753515450257_892
    operator_id: '4350309400'
    operator_type: Filter
    operator_name: flagged_words_filter
    icon: null
    position:
      x: 588.11328125
      'y': 387.5
    configs:
      - id: 4350309401
        operator_id: 4350309400
        config_name: lang
        config_type: select
        select_options:
          - value: '4320064200'
            label: en
          - value: '4320124200'
            label: zh
        default_value: zh
        is_required: true
        is_spinner: false
        final_value: '4320124200'
      - id: 4350309402
        operator_id: 4350309400
        config_name: tokenization
        config_type: checkbox
        default_value: 'true'
        is_required: true
        is_spinner: false
        final_value: false
      - id: 4350309403
        operator_id: 4350309400
        config_name: max_ratio
        config_type: slider
        default_value: '0.01'
        min_value: '0'
        max_value: '1'
        slider_step: '0.01'
        is_required: true
        is_spinner: false
        final_value: 0.5
      - id: 4350309404
        operator_id: 4350309400
        config_name: use_words_aug
        config_type: checkbox
        default_value: 'true'
        is_required: true
        is_spinner: false
        final_value: true
edges:
  - source: node_1753511328856_55
    target: node_1753511329900_846
  - source: node_1753511329900_846
    target: node_1753515450257_892

"""
    print(convert_raw_to_processed(yaml_str))