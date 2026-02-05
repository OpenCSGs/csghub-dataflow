IP 地址清理（`clean_ip_mapper`）

**使用场景**
- 数据脱敏: 清除文本中的IP地址信息
- 隐私保护: 防止IP地址泄露
- 日志清洗: 去除日志中的敏感IP信息

**示例**
- 输入文本: `"ftp://example.com/188.46.244.216my-page.html"`
- 配置: `pattern=默认, repl=''`
- 输出文本: `"ftp://example.com/my-page.html"`