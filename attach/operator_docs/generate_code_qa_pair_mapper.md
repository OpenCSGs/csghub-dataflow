代码问答对生成（`generate_code_qa_pair_mapper`）

**使用场景**
- 代码数据增强: 为代码片段生成对应的需求描述
- 训练数据生成: 创建代码生成任务的训练数据
- 代码理解: 自动生成代码的功能描述

**示例**
- 输入代码:
  ```python
  def hello_world():
      print("Hello, World!")
  hello_world()
  ```
- 输出:
  ```json
  {
    "text": {
      "input": "编写一个Python函数名为hello_world,打印Hello, World!并调用它",
      "response": "def hello_world():\n    print(\"Hello, World!\")\nhello_world()"
    }
  }
  ```