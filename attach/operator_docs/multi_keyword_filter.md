多关键词过滤（`multi_keyword_filter`）

**使用场景**
- 关键词筛选: 根据关键词过滤数据
- 主题过滤: 保留特定主题的文本
- 内容检测: 检测是否包含特定内容

**示例**
- 输入文本: `"Machine learning and deep learning are important."`
- 配置: `keywords=['machine learning', 'AI'], match_mode='any'`
- 输出: 包含"machine learning"，样本被保留
