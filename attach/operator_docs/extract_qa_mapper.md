问答对提取（`extract_qa_mapper`）
- 输入：说明性文档文本，如："物联网是物物相连的互联网，核心是互联网..."。
- 输出：`[{"Human":"物联网的核心是什么？","Assistant":"互联网"}, ...]` 对应的 ChatML JSON 字符串。
- 核心：
  - 调用远程 API（支持 OpenAI 兼容格式，如 Qwen、DeepSeek、GPT 等）生成包含多轮 `Human: ...\nAssistant: ...` 的问答文本。
  - 用正则模式 `Human: (.*?)\nAssistant: (.*?)(?=\nHuman|$)` 抽取问答对。
  - 转成 ChatML 格式的 `messages` 列表，序列化后写回样本，实现从文档到多轮问答对的自动构造。