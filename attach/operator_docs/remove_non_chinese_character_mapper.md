移除非中文字符（`remove_non_chinese_character_mapper`）
- 输入："This is English，混合123和符号@#。"
- 输出："混合和符号。"（保留中文，可配置保留部分数字或标点）
- 核心：按 Unicode 范围保留中文字符，删除非中文字符，用于构造纯中文语料。