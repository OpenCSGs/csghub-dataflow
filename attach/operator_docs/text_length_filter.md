文本长度范围过滤（`text_length_filter`）

**使用场景**
- 长度控制: 过滤过短或过长的文本
- 质量控制: 去除空文本或异常长文本
- 数据标准化: 确保文本长度在合理范围内

**示例**
- 输入文本: `"Today is Sund Sund Sund Sund Sund Sunda and it's a happy day!"`
- 配置: `min_len=10, max_len=1000`
- 输出: 如果文本长度在10-1000字符之间，保留样本