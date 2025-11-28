优化 Instruction（`optimize_instruction_mapper`）
- 输入："写一个简单的鱼香肉丝做法。"
- 输出：更完整的任务描述，例如："请提供一份包含详细食材、步骤、火候说明和注意事项的鱼香肉丝菜谱。"
- 核心：利用如 Qwen2-7B-Instruct-Refine 的模型，将短指令扩写为结构清晰、约束更明确的长指令，提升指令数据质量。