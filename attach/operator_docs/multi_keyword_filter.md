多关键词过滤（`multi_keyword_filter`）

**使用场景**
- 关键词筛选: 根据关键词过滤数据
- 主题过滤: 保留特定主题的文本
- 内容检测: 检测是否包含特定内容

**示例**
- 输入文本: `"Machine learning and deep learning are important."`
- 配置: `keywords=['machine learning', 'AI'], match_mode='any'`
- 包含"machine learning"，样本被保留

- 输入：包含文本内容的样本集合。
- 输出：删除匹配到任何指定关键词的样本。
- 核心：根据预设的关键词列表，当样本中包含任意一个关键词时，将该样本过滤掉，用于删除包含特定关键词的不需要的数据记录。
