高分文本过滤（`text_high_score_filter`）

**使用场景**
- 质量筛选: 只保留高质量样本
- 阈值过滤: 根据评分筛选数据
- 数据精选: 为训练选择最佳样本

**示例**
- 输入数据: `{"text": "...", "quality_score": 0.85}`
- 配置: `score_field='quality_score', min_score=0.7`
- 输出: 分数0.85>=0.7，样本被保留