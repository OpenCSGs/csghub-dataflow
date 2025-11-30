子字符串清理（`remove_words_with_incorrect_substrings_mapper`）
- 输入："abcERROR123 正常词 test_BAD_word"
- 输出："正常词"
- 核心：删除包含指定不合法子串（如 ERROR、BAD）的单词，可用于过滤带敏感/错误片段的 token。