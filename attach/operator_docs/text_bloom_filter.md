数据 Bloom 过滤去重（`text_bloom_filter`）与生成数据聚合（`gather_generated_data_filter`）

**使用场景**
- 快速去重: 使用布隆过滤器快速检测重复
- 大规模去重: 处理海量数据的去重任务
- 增量去重: 与历史数据进行去重

**示例**
- 输入文本: `"This is a new document."`
- 配置: `bloom_filter_file='filter.bloom', hash_func='md5'`
- 如果文本哈希不在过滤器中，样本被保留

- 输入：可能包含重复内容的大规模文本流，或由生成算子输出的 `instruction/response` 对话数据。
- 输出：
  - 经 `text_bloom_filter` 过滤后，仅保留首见文本；
  - 经 `gather_generated_data_filter` 清洗后，得到带有 `conversation` 字段的一问一答对话，并去掉 prompt 为空或重复的样本。
- 核心：
  - `text_bloom_filter`：对 `text` 做哈希写入可扩展 BloomFilter，用哈希是否已存在判断是否是重复样本，再决定是否保留。
  - `gather_generated_data_filter`：
    - 从 `instruction`/`response` 中去掉 `||`、`<|im_end|>` 噪声标记并裁剪空白。
    - 构造标准 `conversation=[{"role":"user"...},{"role":"assistant"...}]` 结构。
    - 用一个集合跟踪 `first_prompt` 是否已出现，过滤掉 conversation 为空或 prompt 重复的样本。

