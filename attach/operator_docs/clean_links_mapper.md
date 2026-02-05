链接清理（`clean_links_mapper`）

**使用场景**
- 文本清洗: 去除文本中的URL链接
- 内容提取: 只保留纯文本内容
- 隐私保护: 清除可能包含敏感信息的链接

**示例**
- 输入文本: `"这是个测试,https://example.com/my-page.html?param1=value1&param2=value2"`
- 配置: `pattern=默认, repl=''`
- 输出文本: `"这是个测试,"`