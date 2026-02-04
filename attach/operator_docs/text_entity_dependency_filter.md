文本实体依赖过滤（`text_entity_dependency_filter`）

**使用场景**
- 复杂度过滤: 保留句法结构复杂的文本
- 质量控制: 确保文本包含实体关系
- 任务特定: 为需要实体关系的任务筛选数据

**示例**
- 输入文本: `"Apple Inc. was founded by Steve Jobs in California."`
- 配置: `lang='en', min_dependency_num=1`
- 输出: 包含实体"Apple Inc."、"Steve Jobs"、"California"及其依存关系，样本被保留