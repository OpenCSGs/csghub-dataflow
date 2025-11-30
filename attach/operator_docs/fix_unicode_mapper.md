Unicode 错误修正（`fix_unicode_mapper`）
- 输入："This text has bad characters: cafÃ© and broken quotes â€œ."
- 输出："This text has bad characters: café and broken quotes \"."
- 核心：通过 `ftfy` 等库修正常见的 Unicode 编码错误，修复乱码与错误字符。