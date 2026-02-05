SimHash去重（`document_simhash_deduplicator`）

**使用场景**
- 近似去重: 删除相似但不完全相同的文档
- 大规模去重: 高效处理海量数据
- 内容去重: 识别内容相似的文档

**示例**
- 输入: 包含相似文档的数据集
- 配置: `window_size=6, hamming_distance=4`
- 输出: 去除相似文档后的数据集