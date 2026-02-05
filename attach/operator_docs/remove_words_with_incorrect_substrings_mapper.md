错误子串词移除（`remove_words_with_incorrect_substrings_mapper`）

**使用场景**
- URL清理: 删除包含URL片段的词
- 数据清洗: 去除包含特定模式的词
- 噪声去除: 删除包含错误子串的词

**示例**
- 输入文本: `"请用百度www.baidu.com进行搜索"`
- 配置: `lang='zh', tokenization=False, substrings=['http', 'www', '.com', 'href', '//']`
- 输出文本: `"请用百度进行搜索"`