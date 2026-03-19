# 英文语义增强 (nlpaug_en_mapper)

## 算子功能

这是一个英文文本数据增强工具,它能通过9种不同的方法对英文文本进行变换,模拟各种真实场景中的错误,从1个样本生成多个变体样本。


## 处理逻辑

### 第一步:选择增强方法

根据配置启用方法:
- 可以启用1个或多个方法
- 每个方法都是开关(true/false)
- 建议同时使用1-3种方法

### 第二步:确定处理模式

两种模式:
- **并行模式**(sequential=false): 每个方法独立处理
- **顺序模式**(sequential=true): 方法依次处理同一文本

### 第三步:应用增强方法

根据模式处理:
- 并行模式: 每个方法生成aug_num个样本
- 顺序模式: 所有方法组合生成aug_num个样本

### 第四步:决定是否保留原始

根据配置:
- keep_original_sample=true: 保留原始+增强样本
- keep_original_sample=false: 仅保留增强样本

### 第五步:复制其他字段

处理完整样本:
- 复制所有其他字段到增强样本
- 确保数据完整性


### 示例

**配置:**
```yaml
随机删除单词: true
随机交换单词位置: true
单词拼写错误: false
随机拆分单词: false
键盘输入错误字符: false
光学字符识别错误: false
随机删除字符: false
随机交换字符位置: false
随机插入字符: false
```

**输入数据:**
```json
{
  "text": "I am going to the park."
}
```

**输出数据:**
```json
[
  {"text": "I am going to the park."},
  {"text": "I going to the park."}
]
```
