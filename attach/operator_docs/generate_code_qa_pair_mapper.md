代码转换成 QA 对数据集（`generate_code_qa_pair_mapper`）
- 输入：Python 代码片段：
  ```python
  def hello_world():
      print("Hello, World!")
  hello_world()
  ```
- 输出：`{"text": {"input": "用 Python 编写一个输出 Hello World 的函数，并调用它", "response": "def hello_world():..."}}`
- 核心：调用本地/服务化 LLM，根据代码生成对应的中文描述式「需求 prompt」，形成 `input(自然语言描述) / response(代码)` 的 QA 对，用于代码指令微调数据集。