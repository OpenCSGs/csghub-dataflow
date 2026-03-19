# SimHash近似去重器 (document_simhash_deduplicator)

## 算子功能

这是一个基于SimHash算法的智能近似去重工具，就像一个"文本指纹比对器"。它为每个文本生成一个64位的二进制指纹，通过比较指纹的汉明距离来判断文本是否相似，特别适合长文本的快速去重。

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

### 第三步：计算SimHash

为每个文本片段计算哈希，合并生成64位SimHash指纹。

### 第四步：查找匹配

使用分块技术快速找到汉明距离≤阈值的文本对。

### 第五步：构建图

将相似文本对构建成图，相似的文本之间有边。

### 第六步：聚类

使用BFS（广度优先搜索）将连通的文本聚成一组。

### 第七步：去重

每个聚类只保留第一个文本，删除其他重复文本。

### 示例

**配置：**
```yaml
分词: "空格"
窗口大小: 6
小写: false
忽略模式: null
块数量: 6
汉明距离: 4
```

**输入数据：**
```json
[
  {"text": "Machine learning is a branch of artificial intelligence"},
  {"text": "Machine learning is a branch of AI technology"},
  {"text": "Deep learning is a subset of machine learning"},
  {"text": "Machine learning is a branch of artificial intelligence"}
]
```

**输出数据：**
```json
[
  {"text": "Machine learning is a branch of artificial intelligence"},
  {"text": "Deep learning is a subset of machine learning"}
]
```
