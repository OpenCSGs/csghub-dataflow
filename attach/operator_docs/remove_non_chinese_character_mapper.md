非中文字符移除（`remove_non_chinese_character_mapper`）

**使用场景**
- 中文文本清洗: 去除非中文字符
- 数据标准化: 只保留中文和必要字符
- 噪声去除: 删除emoji、特殊符号等

**示例**
- 输入文本: `"👊    所有的非汉字a44sh都12@46h会被*&……*qb^4525去掉"`
- 配置: `keep_alphabet=False, keep_number=False, keep_punc=False`
- 输出文本: `"所有的非汉字都会被去掉"`