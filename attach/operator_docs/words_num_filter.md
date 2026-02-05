词数过滤（`words_num_filter`）

**使用场景**
- 长度控制: 过滤词数过少或过多的文本
- 质量控制: 确保文本包含足够的信息
- 数据标准化: 统一文本长度范围

**示例**
- 输入文本: `"This is a short sentence with ten words in total here."`
- 配置: `lang='en', min_num=5, max_num=20`
- 输出: 词数为10，在范围内，样本被保留