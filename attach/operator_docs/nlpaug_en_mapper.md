英文数据增强（`nlpaug_en_mapper`）

**使用场景**
- 数据增强: 扩充训练数据集
- 鲁棒性训练: 提高模型对噪声的容忍度
- 模拟真实场景: 模拟用户输入错误

**示例**
- 输入文本: `"I am going to the park."`
- 配置: `delete_random_word=True, aug_num=1`
- 输出文本: `"I am to the park."` (删除了"going")