排序频率选择器（`frequency_specified_field_selector`）
- 输入：样本中包含某分类字段（如 `source`、`domain`）。
- 输出：按字段值出现频率排序后，选出前 k 个最常见值对应的样本。
- 核心：统计指定字段的频率，选择高频类别对应的样本子集。