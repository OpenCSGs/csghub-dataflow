空白规范化（`whitespace_normalization_mapper`）
- 输入："Hello\u2003World!\n这\t是  测试。"
- 输出："Hello World!\n这 是 测试。"
- 核心：将各种 Unicode 空白字符（制表符、不换行空格等）统一为普通空格 U+0020。