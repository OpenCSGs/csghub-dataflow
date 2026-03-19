# 数据聚合生成 (gather_generated_data_filter)

## 算子功能

这是一个专门处理AI生成的问答数据的工具,它能清理特殊字符,转换数据格式,去除重复问题,过滤无效对话。


## 处理逻辑

### 第一步:检查已有对话

如果样本已经有conversation字段:
- 直接返回,不处理
- 避免重复处理

### 第二步:清理instruction字段

从指令中清理特殊字符:
- 移除"||"字符
- 移除"<|im_end|>"标记
- 去除首尾空白
- 生成first_prompt字段
- 如果长度<3,设为None

### 第三步:清理response字段

从响应中清理特殊字符:
- 移除"||"字符
- 移除"<|im_end|>"标记
- 去除首尾空白
- 生成first_answer字段
- 如果长度<3,设为None

### 第四步:构建对话格式

根据清理结果构建对话:
- 如果问题或答案为None → conversation=None
- 否则 → 构建标准ChatML格式

### 第五步:去重检查

使用哈希集合记录问题:
- 检查first_prompt是否已存在
- 如果存在 → 标记为重复
- 将first_prompt加入集合

### 第六步:过滤判断

决定是否保留样本:
- 重复问题 → 过滤
- conversation为None → 过滤
- 其他情况 → 保留

### 示例

**输入数据:**
```json
{
  "instruction": "什么是人工智能？||",
  "response": "人工智能是计算机科学的一个分支<|im_end|>"
}
```


**输出数据:**
```json
{
  "instruction": "什么是人工智能？||",
  "response": "人工智能是计算机科学的一个分支<|im_end|>",
  "first_prompt": "什么是人工智能？",
  "first_answer": "人工智能是计算机科学的一个分支",
  "conversation": [
    {"role": "user", "content": "什么是人工智能？"},
    {"role": "assistant", "content": "人工智能是计算机科学的一个分支"}
  ]
}
```
