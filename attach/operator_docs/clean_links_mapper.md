链接地址清理（`clean_links_mapper`）
- 输入："详情见 http://example.com 或 https://foo.bar/path。"
- 输出："详情见  或 。"
- 核心：删除以 http/https/ftp 等前缀开头的 URL 链接。