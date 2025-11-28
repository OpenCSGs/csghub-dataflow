字段信息过滤（`specified_field_filter`）
- 输入：结构化样本（例如含有 `lang`, `source`, `domain` 字段）。
- 输出：只保留字段值属于目标集合（如 `lang in ["zh","en"]`）的样本。
- 核心：按字段取值做 whitelist 过滤。