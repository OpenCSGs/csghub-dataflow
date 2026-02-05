去重并保存（`dedup_and_save_deduplicator`）

**使用场景**
- 增量去重: 保存去重记录用于后续增量处理
- 去重审计: 记录去重过程和结果
- 数据追踪: 追踪哪些数据被去重

**示例**
- 输入: 数据集
- 配置: `dedup_method='minhash', save_path='dedup_records.json'`
- 输出: 去重后的数据集 + 去重记录文件
