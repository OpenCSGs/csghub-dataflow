字符重复过滤（`character_repetition_filter`）

**使用场景**
- 质量控制: 过滤包含大量重复字符的低质量文本
- 垃圾内容检测: 识别机器生成的重复内容
- 数据清洗: 去除异常的重复模式

**示例**
- 输入文本: `"Today is Sund Sund Sund Sund Sund Sunda and it's a happy day!"`
- 配置: `rep_len=10, min_ratio=0.0, max_ratio=0.5`
- 输出: 如果字符重复比例 > 50%，样本被过滤；否则保留