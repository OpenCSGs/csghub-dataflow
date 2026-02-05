生成数据收集过滤（`gather_generated_data_filter`）

**使用场景**
- 数据收集: 收集LLM生成的数据
- 数据筛选: 只保留生成的样本
- 管道处理: 在生成后筛选有效样本

**示例**
- 输入数据: `{"text": "...", "is_generated": true}`
- 配置: `generated_field='is_generated'`
- 输出: 标记为true，样本被保留
