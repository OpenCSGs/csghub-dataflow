Unicode 标点规范化（`punctuation_normalization_mapper`）
- 输入："Hello！这是一个"测试"。"
- 输出："Hello! 这是一个"测试"."
- 核心：将全角/特殊 Unicode 标点映射为标准 ASCII 标点，避免分词和 token 统计时受到干扰。