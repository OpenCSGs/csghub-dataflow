文档去重（`document_deduplicator`）

**使用场景**
- 精确去重: 删除完全相同的文档
- 数据清洗: 去除重复数据
- 质量控制: 确保数据唯一性

**示例**
- 输入: 包含重复文档的数据集
- 配置: `hash_method='md5', lowercase=False, ignore_non_character=False`
- 输出: 去除重复后的数据集，只保留每组重复文档中的第一个