长词移除（`remove_long_words_mapper`）

**使用场景**
- 数据清洗: 去除异常长的词(可能是乱码)
- 文本标准化: 过滤不合理的词
- 噪声去除: 删除URL、长串数字等

**示例**
- 输入文本: `"This paper a novel eqeqweqwewqeqwe121e1 method on LLM pretrain."`
- 配置: `min_len=1, max_len=10`
- 输出文本: `"This paper novel method LLM pretrain."`