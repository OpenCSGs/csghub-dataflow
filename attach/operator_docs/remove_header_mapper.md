# 移除文件头(remove_header_mapper)

## 算子功能

这是一个专门用来清理LaTeX文档头部的工具,它能自动找到论文正文的开始位置(第一个章节标记),然后把前面的所有内容(标题、作者、摘要等)全部删除,只保留从第一个章节开始的正文部分。


## 处理逻辑

1. **扫描文档** - 从头到尾读取LaTeX文档内容
2. **查找章节标记** - 寻找第一个出现的章节标记(如`\section`, `\chapter`等)
3. **定位位置** - 确定第一个章节标记的位置
4. **执行删除** - 删除该标记之前的所有内容
5. **保留正文** - 保留从第一个章节开始的所有内容
6. **特殊处理** - 如果没有找到章节标记,根据参数决定是清空还是保留


## 支持的章节标记

算子能识别7种LaTeX章节标记(按层级从高到低):

| 标记 | 层级 | 说明 | 示例 |
|------|------|------|------|
| `\part` | 1 | 部分(最高层级) | `\part{Part One}` |
| `\chapter` | 2 | 章(用于书籍) | `\chapter{Introduction}` |
| `\section` | 3 | 节(最常用) | `\section{Methods}` |
| `\subsection` | 4 | 小节 | `\subsection{Data Collection}` |
| `\subsubsection` | 5 | 子小节 | `\subsubsection{Details}` |
| `\paragraph` | 6 | 段落 | `\paragraph{Note}` |
| `\subparagraph` | 7 | 子段落(最低层级) | `\subparagraph{Remark}` |

**特殊支持**:
- 星号变体: `\section*{Introduction}` (无编号章节)
- 可选参数: `\section[Short]{Long Title}` (短标题和长标题)



### 示例

**配置文件(YAML)**:
```yaml
删除无标题部分: true
```

**输入数据(JSON)**:
```json
{
  "text": "\\documentclass{article}\n\\title{My Research Paper}\n\\author{John Doe}\n\\begin{document}\n\\maketitle\n\\begin{abstract}\nThis is the abstract.\n\\end{abstract}\n\\section{Introduction}\nThis is the introduction.\n\\section{Methods}\nThis is the methods section."
}
```

**输出数据(JSON)**:
```json
{
  "text": "\\section{Introduction}\nThis is the introduction.\n\\section{Methods}\nThis is the methods section."
}
```
