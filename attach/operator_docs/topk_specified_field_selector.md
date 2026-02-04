TopK字段选择（`topk_specified_field_selector`）

**使用场景**
- 数据精选: 选择质量最高的样本
- 排行筛选: 选择得分最高的样本
- 数据缩减: 只保留最重要的样本

**示例**
- 输入数据: 包含quality_score字段的数据集
- 配置: `field_key='quality_score', top_k=1000, reverse=True`
- 输出: 质量分数最高的1000个样本