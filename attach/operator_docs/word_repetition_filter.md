词级重复率范围过滤（`word_repetition_filter`）
- 输入：可能含有大量重复词的文本样本。
- 输出：只保留 word-level n-gram 重复率在正常范围的样本。
- 核心：统计 word n-gram 重复度，过滤重复度严重的刷屏式文本。