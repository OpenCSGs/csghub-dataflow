打分数据筛选（`text_high_score_filter`）
- 输入：已经在某个字段（默认 `text_score`）上打过 0–5 分的样本。
- 输出：只保留得分位于 `[min_score, max_score)` 区间的样本（阈值可配置）。
- 核心：从指定 `score_field` 读取分值，在配置的分数段内标记 `Fields.stats.high_score` 并据此过滤，可与第 27 条的 embedding 打分算子配合使用。