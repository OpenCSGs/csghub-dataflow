# 困惑度过滤器(perplexity_filter)

## 算子功能

困惑度过滤器是一个智能文本质量评估工具,能够判断文本的质量好坏。它使用人工智能(AI)来给文本打分,分数越低表示文本质量越好。如果文本的分数太高(质量太差),就会被过滤掉。


## 处理逻辑

1. 接收待评估的文本
2. 清理文本中的特殊标记
3. 调用AI服务(大语言模型)评估文本质量
4. AI返回一个困惑度分数
5. 将分数与设定的阈值比较
6. 如果分数 <= 阈值:保留文本
7. 如果分数 > 阈值:过滤文本


### 示例

**配置文件(YAML):**
```yaml
模型网址: "https://dashscope.aliyuncs.com/compatible-mode/v1"
模型名称: "qwen-max"
身份验证令牌: "sk-xxxxxxxxxxxxx"
最大困惑度: 1500
```

**输入数据(JSON):**
```json
{
  "text": "人工智能正在改变我们的生活方式,从智能手机到自动驾驶汽车,AI技术无处不在。",
  "meta": {"source": "article"}
}
```


**输出数据(JSON):**
```json
{
  "text": "人工智能正在改变我们的生活方式,从智能手机到自动驾驶汽车,AI技术无处不在。",
  "meta": {"source": "article"},
  "stats": {
    "perplexity": 45.0,
    "perplexity_detail": {
      "perplexity": "45.0",
      "keep": true,
      "reason": "kept",
      "num_chars": 42
    }
  }
}
```

**说明:** 这是一段语法正确、表达流畅的优质文本,困惑度分数很低(45),远低于阈值1500,因此被保留。
