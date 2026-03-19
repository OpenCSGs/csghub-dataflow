# 文档去重MinHashLSH (document_minhash_deduplicator)

## 算子功能

这是一个基于MinHash算法的智能近似去重工具，它不要求文本完全相同，而是能识别高度相似的文本（比如改了几个词的抄袭文章），并将它们去重。

## 处理逻辑

### 第一步：文本预处理

根据配置对文本进行预处理：
- 转小写（lowercase=True）
- 移除特定模式（ignore_pattern）

### 第二步：分词切片

根据tokenization方法将文本切成片段：
- space：按空格分词
- character：按字符切片
- punctuation：按标点分词
- sentencepiece：使用SentencePiece模型

### 第三步：计算MinHash签名

为每个文本生成多个MinHash值，形成签名。

### 第四步：LSH分桶

将MinHash签名分成多个band，相似文本会落入相同的桶。

### 第五步：聚类

使用UnionFind算法将相似文本聚成一组。

### 第六步：去重

每个聚类只保留第一个文本，删除其他重复文本。

### 示例

**配置：**
```yaml
分词: "字符"
窗口大小: 3
小写: false
jaccard 阈值: 0.8
忽略模式: null
排列数量: 256
频带数量: null
每个频带的行数: null
分词模型: null
```

**输入数据：**
```json
[
  {"text": "人工智能正在改变世界"},
  {"text": "人工智能正在改变这个世界"},
  {"text": "AI正在改变世界"},
  {"text": "机器学习是AI的核心"}
]
```

**输出数据：**
```json
[
  {"text": "人工智能正在改变世界"},
  {"text": "AI正在改变世界"},
  {"text": "机器学习是AI的核心"}
]
```
