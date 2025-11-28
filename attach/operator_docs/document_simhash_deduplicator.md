文档去重（SimHash）（`document_simhash_deduplicator`）
- 输入：文本语料库。
- 输出：根据 SimHash 相似度去重后的数据集。
- 核心：对文本计算 SimHash 向量，通过汉明距离阈值判断"近似重复"，删除冗余样本。