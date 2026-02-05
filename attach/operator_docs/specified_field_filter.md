指定字段过滤（`specified_field_filter`）

**使用场景**
- 数据筛选: 根据特定字段值筛选数据
- 分类过滤: 只保留特定类别的数据
- 条件过滤: 根据业务规则过滤数据

**示例**
- 输入数据: `{"text": "...", "category": "news", "source": "website"}`
- 配置: `field_key='category', target_value=['news', 'blog']`
- 输出: category为'news'，在目标值列表中，样本被保留