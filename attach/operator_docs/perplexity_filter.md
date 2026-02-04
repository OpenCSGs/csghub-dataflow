困惑度过滤（`perplexity_filter`）

**使用场景**
- 质量控制: 过滤不流畅或不自然的文本
- 语言模型训练: 选择高质量训练数据
- 数据清洗: 去除机器生成或低质量文本

**示例**
- 输入文本: `"The quick brown fox jumps over the lazy dog."`
- 配置: `lang='en', max_ppl=1500`
- 输出: 计算困惑度，如果<=1500，保留样本