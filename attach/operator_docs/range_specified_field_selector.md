范围字段选择（`range_specified_field_selector`）

**使用场景**
- 异常值过滤: 去除极端值
- 数据筛选: 选择特定范围的样本
- 质量控制: 基于百分位数筛选数据

**示例**
- 输入数据: 包含score字段的数据集
- 配置: `field_key='score', lower_percentile=25, upper_percentile=75`
- 输出: 只保留分数在25%-75%分位数之间的样本