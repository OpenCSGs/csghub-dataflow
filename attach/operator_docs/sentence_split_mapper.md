句子分割（`sentence_split_mapper`）

**使用场景**
- 句子分割: 将段落分割成独立的句子
- 数据预处理: 为句子级任务准备数据
- 文本结构化: 将连续文本转换为句子列表

**示例**
- 输入文本: `"Smithfield employs 3,700 people at its plant in Sioux Falls, South Dakota. The plant slaughters 19,500 pigs a day — 5 percent of U.S. pork."`
- 配置: `lang='en'`
- 输出文本:
  ```
  Smithfield employs 3,700 people at its plant in Sioux Falls, South Dakota.
  The plant slaughters 19,500 pigs a day — 5 percent of U.S. pork.
  ```