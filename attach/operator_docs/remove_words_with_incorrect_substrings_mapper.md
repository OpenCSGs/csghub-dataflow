# 子字符串清理 (remove_words_with_incorrect_substrings_mapper) 

## 算子功能

这是一个错误子串词移除器,它会检查文本中的每个单词,如果发现单词里包含了你指定的"坏片段"(比如"www"、"http"、".com"等),就把整个单词删掉。

## 处理逻辑

算子的工作流程:

1. **分割文本** - 把文本分成一个个单词
2. **检查每个单词** - 看单词里是否包含指定的坏片段
3. **去除特殊符号** - 先去掉单词两边的标点符号,再检查
4. **判断保留或删除** - 如果包含任何一个坏片段,就删掉整个单词
5. **重新组合** - 把保留下来的单词重新组合成文本


### 示例

**配置:**
```yaml
语言: '英文'
分词: false
子字符串: 'http', 'www', 'ftp', '.com', '.org'
```

**输入数据:**
```json
{
  "text": "Check http://example.com and www.site.org or ftp://files.com today.",
  "text": "Visit \"www.example.com\" or (https://site.org) today.",
}
```

**输出数据:**
```json
{
  "text": "Check and or today.",
  "text": "Visit or today."
}
```