token 数量范围过滤（`token_num_filter`）
- 输入：使用某 tokenizer（如 BPE）可分词的文本集合。
- 输出：只保留 token 数在给定范围内的样本。
- 核心：通过指定的 HuggingFace tokenizer 统计 token 数，避免数据过短或超过模型上下文限制。