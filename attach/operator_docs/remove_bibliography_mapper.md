参考文献移除（`remove_bibliography_mapper`）

**使用场景**
- 学术论文处理: 去除论文的参考文献部分
- 正文提取: 只保留论文的正文内容
- 数据清洗: 为NLP任务准备纯文本数据

**示例**
- 输入文本:
  ```latex
  \section{Conclusion}
  This is the conclusion.
  \clearpage
  \bibliographystyle{ACM-Reference-Format}
  \bibliography{sample-base}
  \end{document}
  ```
- 输出文本:
  ```latex
  \section{Conclusion}
  This is the conclusion.
  \clearpage
  \bibliographystyle{ACM-Reference-Format}
  ```