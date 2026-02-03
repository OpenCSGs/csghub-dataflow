HTML 代码清理（`clean_html_mapper`）

**使用场景**
- 网页内容提取: 从HTML页面中提取纯文本
- 数据清洗: 去除爬取数据中的HTML标签
- 文本预处理: 为NLP任务准备干净的文本数据

**示例**
- 输入文本: `"<a href='https://www.example.com/file.html' target='_blank'>Test</a>"`
- 输出文本: `"Test"`

- 输入："<p>欢迎访问 <b>示例网站</b></p>"
- 输出："欢迎访问 示例网站"
- 核心：解析并移除 HTML 标签，保留纯文本内容。