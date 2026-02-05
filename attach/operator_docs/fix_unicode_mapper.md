Unicode修复（`fix_unicode_mapper`）

**使用场景**
- 编码修复: 修复因编码错误导致的乱码
- 数据清洗: 统一文本的Unicode表示
- 文本标准化: 确保文本使用标准的Unicode编码

**示例**
- 输入文本: `"The Mona Lisa doesnÃƒÂ¢Ã¢â€šÂ¬Ã¢â€žÂ¢t have eyebrows."`
- 配置: `normalization='NFC'`
- 输出文本: `"The Mona Lisa doesn't have eyebrows."`