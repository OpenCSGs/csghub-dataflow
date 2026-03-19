# 移除参考书目信息(remove_bibliography_mapper)

## 算子功能

这是一个专门用来清理LaTeX学术论文的工具,它能自动识别并删除论文末尾的参考文献部分和附录内容,只保留论文的正文部分。


## 处理逻辑

1. **扫描文档** - 从头到尾读取LaTeX文档内容
2. **查找标记** - 寻找5种常见的参考文献或附录标记
3. **定位位置** - 找到第一个匹配的标记位置
4. **执行删除** - 删除该标记及其后面的所有内容
5. **保留正文** - 只保留标记之前的正文部分
6. **记录统计** - 统计有多少文档被修改

算子能识别以下5种参考文献标记:

| 标记 | 说明 | 示例 |
|------|------|------|
| `\appendix` | 附录开始标记 | `\appendix` |
| `\begin{references}` | 参考文献环境(小写) | `\begin{references}...\end{references}` |
| `\begin{REFERENCES}` | 参考文献环境(大写) | `\begin{REFERENCES}...\end{REFERENCES}` |
| `\begin{thebibliography}` | 标准参考文献环境 | `\begin{thebibliography}{99}...` |
| `\bibliography{...}` | 参考文献命令 | `\bibliography{refs}` |

### 示例

**输入数据(JSON)**:
```json
{
  "text": "\\section{Conclusion}\nThis is the conclusion.\n\n\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n\\bibliography{sample-base}\n\\end{document}\n\\endinput"
}
```

**输出数据(JSON)**:
```json
{
  "text": "\\section{Conclusion}\nThis is the conclusion.\n\n\\clearpage\n\\bibliographystyle{ACM-Reference-Format}\n"
}
```