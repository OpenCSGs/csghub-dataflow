文档头部移除（`remove_header_mapper`）

**使用场景**
- 论文处理: 去除论文的前言部分
- 正文提取: 从第一个章节开始提取内容
- 数据清洗: 去除文档的元数据部分

**示例**
- 输入文本:
  ```latex
  \documentclass{article}
  \title{My Paper}
  \author{John Doe}
  \begin{document}
  \maketitle
  \section{Introduction}
  This is the introduction.
  ```
- 输出文本:
  ```latex
  \section{Introduction}
  This is the introduction.
  ```