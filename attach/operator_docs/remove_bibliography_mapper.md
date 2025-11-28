移除参考书目信息（`remove_bibliography_mapper`）
- 输入：包含 `\\bibliography{...}` 或参考文献环境的 LaTeX 文档。
- 输出：去除末尾参考文献信息后的正文文本。
- 核心：按照 LaTeX 结构识别并删除参考书目段落，减少引用列表对语料统计的影响。