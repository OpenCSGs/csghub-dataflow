宏定义扩展（`expand_macro_mapper`）
- 输入：一段包含 `\\newcommand` 等宏定义的 LaTeX 文档。
- 输出：宏已被展开、替换为实际文本的 LaTeX 文本。
- 核心：借助 LaTeX 解析，将常见宏在正文中展开，方便后续统计与过滤。