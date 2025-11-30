风格数据合成（`make_cosmopedia_mapper`）
- 输入：包含 `title` 和正文 `text` 的网页摘录样本。
- 输出：`sample['data']` 中写入一篇 WikiHow/教程风格的合成文章。
- 核心：使用远程 OpenAI 兼容 API（默认 Qwen 系列），将网页摘录作为 topic，按模板生成长篇、多步骤、可操作性强的教学文本。