版权信息清理（`clean_copyright_mapper`）
- 输入："/* Copyright XXX 2024 */\n// some license text\nint main() {return 0;}"
- 输出："int main() {return 0;}"
- 核心：优先识别并删除开头包含 `copyright` 的 `/* ... */` 块注释；
  如果文档以一串 `//`、`#`、`--` 注释行（或空行）开头，也会整体跳过这些头部注释，保留后面的正文。