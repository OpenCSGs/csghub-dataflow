# 移除评论信息(remove_comments_mapper)

## 算子功能

这是一个专门用来清理LaTeX文档中注释的工具,它能自动识别并删除LaTeX文档中的注释内容,只保留实际的代码和文本。


## 处理逻辑

算子的工作流程分为两个步骤:

1. **移除行内注释** - 删除代码行后面的注释(从`%`到行尾)
2. **移除多行注释** - 删除整行都是注释的行(行首以`%`开头)


### 示例

**配置文件(YAML)**:
```yaml
内联: true
多行: true
```

**输入数据(JSON)**:
```json
{
  "text": "%% This is a comment\n%% Another comment line\n\\documentclass{article}\n\\title{My Paper}"
}
```

**输出数据(JSON)**:
```json
{
  "text": "\\documentclass{article}\n\\title{My Paper}"
}
```
