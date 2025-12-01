# PDF 转 Markdown 功能测试

这个目录用于测试项目中的 PDF 转 Markdown 功能是否正常工作。

## 目录结构

```
tests/pdf_to_makedown/
├── input/          # 输入文件夹，放置待测试的 PDF 文件
├── output/          # 输出文件夹，转换后的 Markdown 文件会保存在这里
├── test_pdf_to_markdown.py  # 测试脚本
└── README.md        # 本说明文件
```

## 使用方法

### 1. 准备测试文件

将需要测试的 PDF 文件放入 `input` 文件夹中。

### 2. 运行测试

在项目根目录下运行：

```bash
python tests/pdf_to_makedown/pdf_to_markdown.py
```

或者在测试目录下运行：

```bash
cd tests/pdf_to_makedown
python pdf_to_markdown.py
```

### 3. 查看结果

- 转换成功的 Markdown 文件会保存在 `output` 文件夹中
- 测试脚本会在控制台输出详细的测试信息和诊断结果

## 测试内容

测试脚本会执行以下检查：

1. **环境配置检查**
   - Python 版本
   - 环境变量（MINERU_API_URL, MINERU_BACKEND）
   - mineru_worker.py 脚本是否存在
   - 必要的 Python 包是否已安装

2. **PDF 文件查找**
   - 扫描 input 文件夹中的所有 PDF 文件

3. **转换测试**
   - 对每个 PDF 文件执行转换
   - 记录转换过程和结果
   - 检查输出文件是否生成

4. **结果总结**
   - 显示成功/失败统计
   - 提供详细的错误诊断信息

## 环境变量配置

测试脚本会读取以下环境变量：

- `MINERU_API_URL`: MinerU API 服务器地址（默认: http://111.4.242.20:30000）
- `MINERU_BACKEND`: MinerU 后端类型（默认: http-client）

支持的 backend 值：
- `transformers`
- `sglang-engine`
- `sglang-client`
- `http-client`

可以通过 `.env` 文件或系统环境变量进行配置。

## 常见问题诊断

### 1. "Unsupported backend" 错误

**原因**: MinerU API 服务器不支持指定的 backend

**解决方法**:
- 检查 `MINERU_BACKEND` 环境变量
- 确保使用服务器支持的 backend 值
- 查看 MinerU API 服务器的文档确认支持的 backend

### 2. 连接错误

**原因**: 无法连接到 MinerU API 服务器

**解决方法**:
- 检查 `MINERU_API_URL` 环境变量是否正确
- 检查网络连接
- 确认 MinerU API 服务器是否正常运行

### 3. 模块导入错误

**原因**: 缺少必要的 Python 包

**解决方法**:
- 安装 mineru 包：`pip install mineru`
- 检查其他依赖包是否已安装

### 4. 文件权限错误

**原因**: 文件读写权限不足

**解决方法**:
- 检查 input 文件夹的读取权限
- 检查 output 文件夹的写入权限
- 确保有足够的磁盘空间

## 输出说明

测试脚本会输出以下信息：

- ✓ 绿色：成功信息
- ✗ 红色：错误信息
- ⚠ 黄色：警告信息
- ℹ 蓝色：一般信息

测试完成后会显示：
- 总测试数
- 成功/失败统计
- 每个文件的详细结果
- 失败原因诊断

## 注意事项

1. 确保在项目根目录下运行测试，以便正确加载模块
2. 确保已正确配置环境变量
3. 确保 MinerU API 服务器可访问
4. 大文件转换可能需要较长时间，请耐心等待

