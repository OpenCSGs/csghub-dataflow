邮箱后缀清理（`clean_email_mapper`）

**使用场景**
- 数据脱敏: 清除文本中的个人邮箱信息
- 隐私保护: 防止邮箱地址泄露
- 数据清洗: 去除无关的联系方式信息

**示例**
- 输入文本: `"联系我: happy day euqdh@cjqi.com"`
- 配置: `pattern=默认, repl=''`
- 输出文本: `"联系我: happy day "`

- 输入："如有问题，请联系 test@example.com 或 admin@test.cn。"
- 输出："如有问题，请联系  或 。"
- 核心：利用正则匹配电子邮件地址并删除，保护隐私。