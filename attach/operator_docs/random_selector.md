# 随机样本选择器(random_selector)

## 算子功能

随机选择器是一个数据抽样工具,能够从大量数据中随机抽取指定数量或比例的样本。每个样本被抽中的机会都是平等的。

## 处理逻辑

1. 检查数据集大小(如果太小就不抽样)
2. 检查是否设置了选择参数
3. 计算要选择多少个样本
4. 使用随机算法抽取样本
5. 返回抽取的样本
6. 记录统计信息

### 示例1

**配置文件(YAML):**
```yaml
选择比率: 0.1
选择数量: 1
```

**输入数据(JSON):**
```json
{

  {"text": "sample1", "score": 0.9},
  {"text": "sample2", "score": 0.8},
  {"text": "sample3", "score": 0.7},
  {"text": "sample4", "score": 0.6},
  {"text": "sample5", "score": 0.5},
  {"text": "sample6", "score": 0.4},
  {"text": "sample7", "score": 0.3},
  {"text": "sample8", "score": 0.2},
  {"text": "sample9", "score": 0.1},
  {"text": "sample10", "score": 0.05}

}
```

**输出数据(JSON):**
```json
{
  {"text": "sample7", "score": 0.3}
}
```
