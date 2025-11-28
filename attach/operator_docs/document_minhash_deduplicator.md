文档去重（MinHashLSH）（`document_minhash_deduplicator`）
- 输入：大规模文本语料库。
- 输出：近似相同文档被合并/去重后的数据集。
- 核心：通过 MinHash + LSH 近似检测高 Jaccard 相似度的文档并去重，原始中间结构以字节存储，最终数据集不保留这些结构。