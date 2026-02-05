布隆过滤器（`text_bloom_filter`）

**使用场景**
- 快速去重: 使用布隆过滤器快速检测重复
- 大规模去重: 处理海量数据的去重任务
- 增量去重: 与历史数据进行去重

**示例**
- 输入文本: `"This is a new document."`
- 配置: `bloom_filter_file='filter.bloom', hash_func='md5'`
- 输出: 如果文本哈希不在过滤器中，样本被保留
