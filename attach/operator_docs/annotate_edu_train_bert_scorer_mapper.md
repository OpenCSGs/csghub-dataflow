教学评估打分（`annotate_edu_train_bert_scorer_mapper`）
- 输入：一条待评估的文本（如教学/科普内容）。
- 输出：在样本中新增一个形如 `text_score` 的评分字段，取值范围约在 0~5 之间。
- 核心：
  - 使用 OpenAI 兼容的 embedding 接口（如 `text-embedding-v4`）分别对固定查询 `query_text` 和当前样本文本做向量编码。
  - 计算两者余弦相似度，并按区间映射到 0–5 分段（低/中/高相关分别线性缩放）。
  - 得分越高表示与 `query_text` 越相关，可作为后续筛选依据。