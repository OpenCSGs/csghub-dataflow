# 数据样本向量编码搜索 (encode_and_get_nearest_mapper)

## 算子功能

这是一个将文本转换为向量并查找相似文本的智能工具，它先调用AI模型将文本转换为数字向量（embedding），然后使用Faiss技术快速找到每个文本最相似的其他文本。


## 处理逻辑

### 第一步：提取文本

从数据集中提取 `first_prompt` 字段的文本。

### 第二步：调用API获取向量

批量调用OpenAI兼容的API，将所有文本转换为向量。

### 第三步：构建Faiss索引

使用Faiss库构建向量索引，支持快速搜索。

### 第四步：查找最近邻

为每个文本查找最相似的K个文本（默认K=5）。

### 第五步：添加结果字段

为数据集添加三个新字段：
- `embedding`：文本的向量表示
- `nn_indices`：最相似文本的索引列表
- `nn_scores`：对应的相似度分数列表

### 第六步：返回结果

返回增强后的数据集。


### 示例

**配置：**
```yaml
model_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
auth_token: "sk-xxxx"
model_name: text-embedding-v4
dimensions: 1024
```

**输入数据：**
```json
[
  {"first_prompt": "机器学习是什么？"},
  {"first_prompt": "深度学习的原理"},
  {"first_prompt": "人工智能的应用"},
  {"first_prompt": "如何做红烧肉？"}
]
```

**输出数据：**
```json
[
  {
    "first_prompt": "机器学习是什么？",
    "embedding": [0.23, -0.45, 0.67, ...],
    "nn_indices": [[1, 2, 3]],
    "nn_scores": [[0.88, 0.85, 0.10]]
  },
  {
    "first_prompt": "深度学习的原理",
    "embedding": [0.25, -0.43, 0.65, ...],
    "nn_indices": [[0, 2, 3]],
    "nn_scores": [[0.88, 0.82, 0.08]]
  },
  {
    "first_prompt": "人工智能的应用",
    "embedding": [0.22, -0.44, 0.66, ...],
    "nn_indices": [[0, 1, 3]],
    "nn_scores": [[0.85, 0.82, 0.12]]
  },
  {
    "first_prompt": "如何做红烧肉？",
    "embedding": [-0.56, 0.78, -0.34, ...],
    "nn_indices": [[2, 0, 1]],
    "nn_scores": [[0.12, 0.10, 0.08]]
  }
]
```
