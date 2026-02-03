打分数据筛选（`text_high_score_filter`）

**使用场景**
- 质量筛选: 只保留高质量样本
- 阈值过滤: 根据评分筛选数据
- 数据精选: 为训练选择最佳样本

**示例**
- 输入数据: `{"text": "...", "quality_score": 0.85}`
- 配置: `score_field='quality_score', min_score=0.7`
- 分数0.85>=0.7，样本被保留

- 输入：已经在某个字段（默认 `text_score`）上打过 0–5 分的样本。
- 输出：只保留得分位于 `[min_score, max_score)` 区间的样本（阈值可配置）。
- 核心：从指定 `score_field` 读取分值，在配置的分数段内标记 `Fields.stats.high_score` 并据此过滤，可与第 27 条的 embedding 打分算子配合使用。