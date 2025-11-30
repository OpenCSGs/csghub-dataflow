数据样本向量编码搜索（`encode_and_get_nearest_mapper`）
- 输入：包含 `first_prompt` 字段的样本集合（通常由前序算子整理得到）。
- 输出：为每条样本增加 `embedding`、`nn_indices`、`nn_scores` 字段，记录其向量表示及最近邻信息。
- 核心：
  - 通过 OpenAI 兼容的 embedding 接口（默认 `text-embedding-v4`）对 `first_prompt` 列表编码为向量。
  - 使用 `datasets` + `faiss` 构建索引，以内积（余弦）相似度检索每条样本的 Top‑K 最近邻。
  - 结果用于后续基于图连通性的去重算子 `dedup_and_save_deduplicator`。