语言识别评分过滤（`language_id_score_filter`）

**使用场景**
- 语言过滤: 只保留特定语言的文本
- 质量控制: 过滤语言混杂的文本
- 数据清洗: 去除语言识别不确定的样本

**示例**
- 输入文本: `"This is an English sentence."`
- 配置: `lang='en', min_score=0.8`
- 输出: 识别为英语且分数>0.8，样本被保留