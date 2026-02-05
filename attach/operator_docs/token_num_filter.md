Token数量过滤（`token_num_filter`）

**使用场景**
- 长度控制: 根据模型token限制过滤数据
- 质量控制: 确保文本长度适中
- 模型适配: 为特定模型准备合适长度的数据

**示例**
- 输入文本: `"This is a sample text for tokenization."`
- 配置: `hf_tokenizer='gpt2', min_num=5, max_num=100`
- 输出: 使用GPT-2 tokenizer分词，如果token数在5-100之间，保留样本