MinHash去重（`document_minhash_deduplicator`）

**使用场景**
- 近似去重: 删除高度相似的文档
- 大规模去重: 使用LSH加速查找
- 内容去重: 基于n-gram相似度去重

**示例**
- 输入: 包含相似文档的数据集
- 配置: `num_perm=256, jaccard_threshold=0.7, ngram_size=5`
- 输出: 去除相似文档后的数据集