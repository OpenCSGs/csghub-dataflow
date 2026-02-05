问答提取（`extract_qa_mapper`）

**使用场景**
- 对话数据生成: 从文档中自动生成对话训练数据
- 知识提取: 将文档转换为问答形式
- 数据增强: 为对话模型创建训练数据

**示例**
- 输入文本: `"蒙古国的首都是乌兰巴托(Ulaanbaatar)。它是蒙古国最大的城市,也是该国的政治、经济和文化中心。"`
- 输出:
  ```json
  [
    {
      "messages": [
        {"role": "user", "content": "蒙古国的首都是哪里?"},
        {"role": "assistant", "content": "蒙古国的首都是乌兰巴托(Ulaanbaatar)。"}
      ]
    },
    {
      "messages": [
        {"role": "user", "content": "乌兰巴托在蒙古国是什么样的城市?"},
        {"role": "assistant", "content": "乌兰巴托是蒙古国最大的城市,也是该国的政治、经济和文化中心。"}
      ]
    }
  ]
  ```