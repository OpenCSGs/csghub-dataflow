# 排序频率选择器 (frequency_specified_field_selector)

## 算子功能

这是一个基于字段值出现频率的数据选择工具,它统计每个字段值出现了多少次,然后选择最热门(或最冷门)的几个值对应的所有数据。

## 处理逻辑

### 第一步:参数验证

检查基本条件:
- 数据集是否为空
- field_key是否指定
- 字段是否存在

### 第二步:统计字段值频率

遍历所有样本:
- 提取指定字段的值
- 统计每个值出现的次数
- 记录每个值对应的样本索引

### 第三步:计算选择数量

根据参数决定选择多少个字段值:
- 只设置topk → 选择topk个值
- 只设置top_ratio → 选择比例对应的值
- 都设置 → 取较小值
- 都不设置 → 返回全部

### 第四步:排序和选择

按频率排序字段值:
- reverse=True → 降序(高频在前)
- reverse=False → 升序(低频在前)
- 选择前N个字段值
- 收集这些值的所有样本索引

### 第五步:返回结果

根据索引选择样本:
- 使用收集的索引
- 从原数据集中选择
- 返回选择后的数据集

### 示例

**配置:**
```yaml
字段名称: category
前n%比率: 0
前k个: 2
反向排序: true
```

**输入数据:**
```json
[
  {"text": "sample1", "category": "A"},
  {"text": "sample2", "category": "A"},
  {"text": "sample3", "category": "A"},
  {"text": "sample4", "category": "B"},
  {"text": "sample5", "category": "B"},
  {"text": "sample6", "category": "C"},
  {"text": "sample7", "category": "D"}
]
```


**输出数据:**
```json
[
  {"text": "sample1", "category": "A"},
  {"text": "sample2", "category": "A"},
  {"text": "sample3", "category": "A"},
  {"text": "sample4", "category": "B"},
  {"text": "sample5", "category": "B"}
]
```
