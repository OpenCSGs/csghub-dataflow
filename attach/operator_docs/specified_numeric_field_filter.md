指定数值字段过滤（`specified_numeric_field_filter`）

**使用场景**
- 数值范围过滤: 根据数值字段筛选数据
- 质量控制: 过滤评分过低的数据
- 阈值过滤: 根据业务阈值筛选数据

**示例**
- 输入数据: `{"text": "...", "rating": 4.5, "views": 1000}`
- 配置: `field_key='rating', min_value=4.0, max_value=5.0`
- 输出: rating为4.5，在范围内，样本被保留