邮箱后缀清理（`clean_email_mapper`）
- 输入："如有问题，请联系 test@example.com 或 admin@test.cn。"
- 输出："如有问题，请联系  或 。"
- 核心：利用正则匹配电子邮件地址并删除，保护隐私。