# 代码问答对生成器 (generate_code_qa_pair_mapper)

## 算子功能

这是一个代码逆向需求生成工具,它能看懂代码在做什么,然后用中文描述出来,把"代码"转换成"需求-代码"问答对。


## 处理逻辑

### 第一步:构建提示

使用固定的中文模板:
```
为了输出下面代码片段,请生成对应prompt内容,
该prompt应该用中文详细描述需求,
比如使用python实现什么功能。请回复:prompt=?
代码片段:
{代码}
```

### 第二步:调用AI模型

发送HTTP请求到AI服务:
- 使用API密钥认证
- 等待AI生成需求描述(最多120秒)
- 获取AI的回复

### 第三步:提取需求描述

从AI回复中提取需求:
- 移除"prompt="前缀
- 提取纯净的需求描述文本
- 清理多余的空白

### 第四步:构建问答对

组装成标准格式:
- input: AI生成的需求描述
- response: 原始代码片段
- 格式: 字典结构

### 第五步:错误处理

如果出现问题:
- API调用失败 → 返回原样本
- 解析失败 → 返回原样本
- 其他错误 → 返回原样本

### 示例1
**配置:**
```yaml
prompt_template: "https://api.deepseek.com/chat/completions"
模型名称: "deepseek-chat"
auth_token: "sk-xxxxxxxxxxxxx"
```

**输入数据:**
```json
{
  "text": "def hello_world():\n    print(\"Hello, World!\")\nhello_world()"
}
```

**输出数据:**
```json
{
  "text": {
    "input": "编写一个Python函数名为hello_world,该函数打印\"Hello, World!\",然后调用这个函数",
    "response": "def hello_world():\n    print(\"Hello, World!\")\nhello_world()"
  }
}
```
