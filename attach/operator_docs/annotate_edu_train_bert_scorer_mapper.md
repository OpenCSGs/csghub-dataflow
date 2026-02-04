教学评估打分（`annotate_edu_train_bert_scorer_mapper`）

**使用场景**
- 教育内容评分: 评估文本的教育价值
- 内容筛选: 根据相关性过滤数据
- 质量评估: 为教育数据集打分

**示例**
- 输入文本: `"深度学习是机器学习的一个分支..."`
- 配置: `query_text='What is Deep Learning?'`
- 输出: 在样本中添加 `text_score` 字段，值为0-5之间的浮点数