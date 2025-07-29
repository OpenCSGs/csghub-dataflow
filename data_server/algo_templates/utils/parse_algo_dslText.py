import yaml
from collections import deque, defaultdict


def convert_raw_to_processed(raw_yaml: str) -> str:
    """
    将原始YAML数据处理为目标格式的YAML字符串
    :param raw_yaml: 原始YAML格式的字符串
    :return: 处理后的YAML格式字符串
    """
    # -------------------- 步骤1：解析原始数据 --------------------
    data = yaml.safe_load(raw_yaml)  # 将YAML字符串转为Python字典

    # -------------------- 步骤2：提取节点和连接关系 --------------------
    nodes = data.get('process', {})  # 所有处理节点（字典，键是node_0/node_1等）
    edges = data.get('edges', [])  # 节点连接关系（数据流动方向）

    # 建立「节点ID」到「节点详情」的映射（方便快速查找）
    id_to_node = {node['id']: node for node in nodes.values()}

    # -------------------- 步骤3：确定节点执行顺序（拓扑排序） --------------------
    # 构建邻接表（记录每个节点的下游节点）和入度表（记录每个节点的入度）
    adj = defaultdict(list)  # 邻接表：key=节点ID，value=下游节点ID列表
    in_degree = defaultdict(int)  # 入度表：key=节点ID，value=入度数（有多少上游节点指向它）

    # 首先初始化所有节点的入度为0
    for node_id in id_to_node.keys():
        in_degree[node_id] = 0

    for edge in edges:
        source = edge['source']  # 数据来源节点ID
        target = edge['target']  # 数据流向的节点ID

        # 记录连接关系
        adj[source].append(target)
        in_degree[target] += 1  # 目标节点入度+1

    # 拓扑排序（确定节点执行顺序）
    queue = deque([node_id for node_id in in_degree if in_degree[node_id] == 0])  # 初始入度为0的节点（起点）
    process_order = []  # 最终的节点执行顺序（存储节点ID）

    while queue:
        current_node = queue.popleft()
        process_order.append(current_node)

        # 遍历当前节点的所有下游节点，减少它们的入度
        for next_node in adj[current_node]:
            in_degree[next_node] -= 1
            if in_degree[next_node] == 0:  # 下游节点入度减为0时，加入队列
                queue.append(next_node)

    # 检查是否存在环（如果有环则无法处理所有节点）
    if len(process_order) != len(id_to_node):
        raise ValueError("数据流中存在环，无法确定处理顺序！")

    # -------------------- 步骤4：生成process字段 --------------------
    process_list = []
    for node_id in process_order:  # 按执行顺序处理每个节点
        node = id_to_node[node_id]
        operator_name = node['operator_name']  # 节点的处理名称（如chinese_convert_mapper）
        configs = node.get('configs', [])  # 该节点的配置参数列表

        # 将配置参数转换为字典（处理类型转换：字符串'true'→布尔值True）
        config_dict = {}
        for config in configs:
            param_name = config['config_name']  # 参数名（如mode）
            param_value = config['final_value']  # 参数值（如'4998547'）
            
            # 根据param_value查询operator_config_select_options记录，获取name属性
            if param_value and isinstance(param_value, str) and param_value.isdigit():
                from data_server.operator.mapper.operator_mapper import get_operator_config_select_option_by_id
                from data_server.database.session import get_sync_session
                try:
                    # 创建数据库会话
                    db = get_sync_session()
                    option_record = get_operator_config_select_option_by_id(db, int(param_value))
                    if option_record and hasattr(option_record, 'name'):
                        param_value = option_record.name
                    db.close()
                except Exception as e:
                    # 如果查询失败，保持原值
                    print(f"查询operator_config_select_options失败: {e}")
                    pass

            # 修复：final_value为None时直接赋值None，否则再lower
            if param_value is None:
                config_dict[param_name] = None
            elif isinstance(param_value, str) and param_value.lower() == 'true':
                config_dict[param_name] = True
            elif isinstance(param_value, str) and param_value.lower() == 'false':
                config_dict[param_name] = False
            else:
                config_dict[param_name] = param_value  # 其他情况保持原字符串

        # 将节点名称和参数添加到处理流程列表
        process_list.append({operator_name: config_dict})

    # -------------------- 步骤5：组装最终结果 --------------------
    # 复制原始数据的所有字段（排除nodes和edges）
    result = data.copy()
    result.pop('process', None)  # 移除原始nodes字段
    result.pop('edges', None)  # 移除原始edges字段
    result['process'] = process_list  # 添加处理流程字段

    # 将字典转为YAML字符串（保留字段顺序，允许中文，设置正确的缩进）
    yaml_str = yaml.dump(result, sort_keys=False, allow_unicode=True, default_flow_style=False, indent=2, width=float("inf"))

    # 将空字典 "{}" 替换为空字符串，保留冒号
    yaml_str = yaml_str.replace(": {}", ":")
    
    # 确保process字段的缩进正确
    lines = yaml_str.split('\n')
    formatted_lines = []
    in_process_section = False
    
    for line in lines:
        if line.strip() == 'process:':
            in_process_section = True
            formatted_lines.append(line)
        elif in_process_section and line.strip().startswith('- ') and ':' in line:
            # 这是process列表中的项目，确保正确的缩进
            if not line.startswith('  '):
                line = '  ' + line
            formatted_lines.append(line)
        elif in_process_section and line.strip() and not line.strip().startswith('- '):
            # 这是process列表项下的配置参数，需要额外缩进
            if line.startswith('      '):
                # 已经是6个空格缩进，保持不变
                formatted_lines.append(line)
            elif line.startswith('    '):
                # 只有4个空格缩进，替换为6个空格
                formatted_lines.append('      ' + line[4:])
            elif line.startswith('  '):
                # 只有2个空格缩进，替换为6个空格
                formatted_lines.append('      ' + line[2:])
            else:
                # 没有缩进，添加6个空格
                formatted_lines.append('      ' + line)
        else:
            # 其他行保持不变
            formatted_lines.append(line)
            # 如果遇到非process字段，退出process区域
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