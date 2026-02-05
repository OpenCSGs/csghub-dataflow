停用词过滤（`stopwords_filter`）

**使用场景**
- 质量控制: 过滤停用词过少的异常文本
- 自然度检测: 确保文本包含正常的停用词
- 数据清洗: 去除关键词堆砌的文本

**示例**
- 输入文本: `"The quick brown fox jumps over the lazy dog."`
- 配置: `lang='en', min_ratio=0.3`
- 输出: 停用词包括"the", "over"等，如果比例>=30%，保留样本