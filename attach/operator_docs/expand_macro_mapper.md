宏展开（`expand_macro_mapper`）

**使用场景**
- LaTeX文档处理: 展开自定义宏,便于后续处理
- 文档标准化: 将宏定义内联到文档中
- 数据预处理: 为机器学习模型准备LaTeX数据

**示例**
- 输入文本:
  ```latex
  \newcommand{\mycommand}{Hello World}
  This is \mycommand test.
  ```
- 输出文本:
  ```latex
  \newcommand{\mycommand}{Hello World}
  This is Hello World test.
  ```