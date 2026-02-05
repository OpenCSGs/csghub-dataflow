文本编码与最近邻查找（`encode_and_get_nearest_mapper`）

**使用场景**
- 相似度搜索: 查找相似的文本
- 数据去重: 识别重复或相似的样本
- 聚类分析: 为文本聚类提供基础

**示例**
- 输入数据集:
  ```json
  [
    {"first_prompt": "What is artificial intelligence?"},
    {"first_prompt": "How does machine learning work?"}
  ]
  ```
- 输出数据集: 增加 `embedding`、`nn_indices` 和 `nn_scores` 字段