注释移除（`remove_comments_mapper`）

**使用场景**
- LaTeX文档清洗: 去除注释内容
- 代码提取: 只保留实际的LaTeX代码
- 文档标准化: 统一文档格式

**示例**
- 输入文本:
  ```latex
  %% This is a comment
  \documentclass{article}
  \title{My Paper} % inline comment
  %% Another comment
  \begin{document}
  ```
- 输出文本:
  ```latex
  \documentclass{article}
  \title{My Paper}
  \begin{document}
  ```