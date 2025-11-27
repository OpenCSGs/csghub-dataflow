# dedup_and_save_deduplicator 算子说明文档

## 算子概述

`dedup_and_save_deduplicator` 是一个基于图连通性的去重算子。它通过构建相似度图来识别重复样本，并保留每个连通分量中的代表性样本。该算子适用于已有预计算最近邻相似度信息的数据集。

## 算子功能

### 核心功能描述

1. **相似度图构建**：算子会遍历数据集中的每个样本，根据样本中的最近邻索引（`nn_indices`）和相似度分数（`nn_scores`）构建一个无向图。如果两个样本之间的相似度分数超过设定的阈值，则在它们之间添加一条边。

2. **连通分量识别**：使用图论算法识别所有连通分量。在同一个连通分量中的样本被认为是相似的（可能通过传递关系连接）。

3. **样本筛选**：对于每个连通分量，只保留索引最小的样本，删除其他重复样本。

4. **字段过滤**：将指定的字段（如 `embedding`、`nn_indices`、`nn_scores`、`text` 等）从样本主体移动到 `stats` 字段中，以减少存储空间。

### 适用场景

- 数据集已包含预计算的最近邻相似度信息
- 需要处理传递性相似关系（A与B相似，B与C相似，则A、B、C应归为一组）
- 需要对大规模数据集进行去重处理

## 输入参数

### 参数说明

| 参数名 | 类型 | 默认值 | 是否必填 | 说明 |
|--------|------|--------|----------|------|
| `similarity_threshold` | `float` | `0.5` | 否 | 相似度阈值。只有相似度分数大于等于此阈值的样本对才会被连接。取值范围：[0.0, 1.0] |
| `nn_indices_key` | `str` | `'nn_indices'` | 否 | 样本中存储最近邻索引的字段名。每个样本应包含一个列表，列表中的元素可以是列表或数组，表示该样本的最近邻样本索引 |
| `nn_scores_key` | `str` | `'nn_scores'` | 否 | 样本中存储最近邻相似度分数的字段名。每个样本应包含一个列表，列表中的元素可以是列表或数组，表示与最近邻样本的相似度分数，与 `nn_indices` 一一对应 |
| `fields_to_filter` | `list` | `['embedding', 'nn_indices', 'nn_scores', 'text', 'instruction', 'response']` | 否 | 需要移动到 `stats` 字段的字段列表。这些字段在处理后会被移动到样本的 `stats` 字段中，并从样本主体中删除 |

### 输入数据要求

每个样本需要包含以下字段：

1. **`nn_indices`**（或通过 `nn_indices_key` 指定的字段）：
   - 类型：列表（可以是嵌套列表）
   - 格式：`[[1, 2]]` 或 `[[1, 2], [3, 4]]`（多组最近邻）
   - 说明：如果是最外层是列表且第一个元素是列表，则取第一个元素；否则直接使用
   - 示例：`[[1, 2]]` 表示当前样本的最近邻是索引为 1 和 2 的样本

2. **`nn_scores`**（或通过 `nn_scores_key` 指定的字段）：
   - 类型：列表（可以是嵌套列表）
   - 格式：`[[0.97, 0.89]]` 或 `[[0.97, 0.89], [0.85, 0.82]]`
   - 说明：与 `nn_indices` 格式一致，长度必须匹配
   - 示例：`[[0.97, 0.89]]` 表示与索引 1 和 2 的样本的相似度分数分别为 0.97 和 0.89

### 输入示例

```python
dataset = [
    {
        'text': 'The cat sat on the mat',
        'nn_indices': [[1, 2]],  # 与索引1和2的样本相似
        'nn_scores': [[0.97, 0.89]]  # 相似度分数
    },
    {
        'text': 'A cat was sitting on a mat',
        'nn_indices': [[0, 2]],  # 与索引0和2的样本相似
        'nn_scores': [[0.97, 0.92]]
    },
    {
        'text': 'The cat sat on the mat',
        'nn_indices': [[0, 1]],
        'nn_scores': [[0.89, 0.92]]
    },
    {
        'text': 'Today is a sunny day',
        'nn_indices': [[]],  # 没有相似样本
        'nn_scores': [[]]
    }
]
```

## 输出说明

### 输出数据结构

算子返回两个值：

1. **去重后的数据集**（`Dataset`）：
   - 类型：`NestedDataset`
   - 说明：经过去重处理的数据集，每个连通分量只保留一个样本（索引最小的）

2. **重复样本对信息**（`dict`）：
   - 类型：`dict`
   - 说明：用于追踪的重复样本对信息，仅在 `show_num > 0` 时包含内容
   - 格式：`{'group_0': [sample1, sample2], ...}`

### 输出字段变化

- **保留的字段**：样本中不在 `fields_to_filter` 列表中的字段会保留在样本主体中
- **移动到 stats 的字段**：`fields_to_filter` 中指定的字段会被移动到 `stats` 字段中
  - 原字段：`sample['text']`
  - 处理后：`sample['stats']['text']`（如果 `text` 在 `fields_to_filter` 中）

### 输出示例

假设输入数据如上述示例，使用 `similarity_threshold=0.5`：

**去重逻辑**：
- 样本 0、1、2 形成连通分量（0↔1，0↔2，1↔2）
- 样本 3 独立存在
- 保留索引最小的样本：0 和 3

**输出数据集**：
```python
[
    {
        'text': 'The cat sat on the mat',  # 如果 text 不在 fields_to_filter 中
        # 或者
        'stats': {
            'text': 'The cat sat on the mat'  # 如果 text 在 fields_to_filter 中
        }
    },
    {
        'text': 'Today is a sunny day',  # 或 stats 格式
    }
]
```

## 使用示例

### 基本使用

```yaml
process:
  - dedup_and_save_deduplicator:
      similarity_threshold: 0.5
      nn_indices_key: 'nn_indices'
      nn_scores_key: 'nn_scores'
      fields_to_filter: ['embedding', 'nn_indices', 'nn_scores', 'text']
```

### Python 代码示例

```python
from data_engine.core.data import NestedDataset as Dataset
from data_engine.ops.deduplicator.dedup_and_save_deduplicator import DedupAndSaveDeduplicator

# 准备数据
ds_list = [
    {'text': 'A', 'nn_indices': [[1]], 'nn_scores': [[0.99]]},
    {'text': 'B', 'nn_indices': [[0, 2]], 'nn_scores': [[0.99, 0.98]]},
    {'text': 'C', 'nn_indices': [[1]], 'nn_scores': [[0.98]]},
    {'text': 'D', 'nn_indices': [[]], 'nn_scores': [[]]},
]

dataset = Dataset.from_list(ds_list)

# 创建算子实例
op = DedupAndSaveDeduplicator(
    similarity_threshold=0.95,
    nn_indices_key='nn_indices',
    nn_scores_key='nn_scores',
    fields_to_filter=['nn_indices', 'nn_scores']
)

# 执行去重
dataset = dataset.map(op.compute_hash)
result_dataset, dup_pairs = op.process(dataset)

# 结果：保留样本 A（索引0）和 D（索引3）
```

## 算法原理

### 图构建过程

1. 初始化一个无向图 `G`，将所有样本作为节点
2. 遍历每个样本：
   - 获取该样本的 `nn_indices` 和 `nn_scores`
   - 对于每个最近邻，如果相似度分数 `>= similarity_threshold` 且邻居索引在数据集范围内，则在当前样本和邻居样本之间添加一条边

### 连通分量识别

使用 NetworkX 库的 `connected_components` 函数识别所有连通分量。连通分量中的样本通过相似度边连接（可能通过传递关系）。

### 样本选择策略

对于每个连通分量，选择索引最小的样本作为代表样本，删除其他样本。

## 注意事项

1. **相似度信息要求**：数据集必须包含预计算的最近邻相似度信息。如果样本中没有 `nn_indices` 和 `nn_scores` 字段，算子会自动创建空列表，但不会进行去重。

2. **索引有效性**：`nn_indices` 中的索引必须在数据集的有效范围内（0 到 len(dataset)-1），超出范围的索引会被忽略。

3. **传递性去重**：算子支持传递性去重。例如，如果样本 A 与 B 相似，B 与 C 相似，即使 A 与 C 的直接相似度低于阈值，它们也会被归为同一组。

4. **字段过滤**：`fields_to_filter` 中指定的字段会被移动到 `stats` 字段。如果字段不存在，则不会报错，只是跳过。

5. **性能考虑**：
   - 图构建的时间复杂度为 O(n×k)，其中 n 是样本数，k 是平均最近邻数量
   - 连通分量识别的时间复杂度约为 O(n+m)，其中 m 是边的数量
   - 对于大规模数据集，建议先用 `encode_and_get_nearest_mapper` 等算子预计算相似度信息

## 相关算子

- **`encode_and_get_nearest_mapper`**：用于预计算样本的嵌入向量和最近邻相似度信息
- **`document_deduplicator`**：基于 MD5 哈希的文档级去重
- **`document_simhash_deduplicator`**：基于 SimHash 的去重
- **`document_minhash_deduplicator`**：基于 MinHashLSH 的去重

## 版本信息

- 算子名称：`dedup_and_save_deduplicator`
- 算子类型：Deduplicator
- 依赖库：networkx, numpy
