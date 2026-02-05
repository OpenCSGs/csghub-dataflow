频率字段选择（`frequency_specified_field_selector`）

**使用场景**
- 数据采样: 选择最常见的类别
- 长尾过滤: 去除低频样本
- 数据平衡: 基于频率选择样本

**示例**
- 输入数据: 包含category字段的数据集
- 配置: `field_key='category', top_k=5`
- 输出: 只保留频率最高的5个类别的样本