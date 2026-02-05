文本动作过滤（`text_action_filter`）

**使用场景**
- 内容筛选: 保留包含动作的文本
- 质量控制: 确保文本具有动态性
- 任务特定: 为需要动作描述的任务筛选数据

**示例**
- 输入文本: `"The cat runs quickly and jumps high."`
- 配置: `lang='en', min_action_num=1`
- 输出: 包含动词"runs"和"jumps"，样本被保留