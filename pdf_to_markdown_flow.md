# PDF 转 Markdown 调用链和逻辑说明

## 调用链概览

```
API 请求
  ↓
format_task (Celery 任务)
  ↓
下载数据集文件
  ↓
遍历 PDF 文件
  ↓
convert_pdf_to_markdown()
  ↓
启动 mineru_worker.py 子进程
  ↓
MinerU API 服务器处理 PDF
  ↓
生成 middle_json
  ↓
转换为 Markdown
  ↓
上传结果
```

## 详细调用链

### 1. 入口：Celery 任务

**文件**: `data_celery/formatify/tasks.py`

**函数**: `format_task(task_id, user_name, user_token)`

**位置**: ```33:34:data_celery/formatify/tasks.py```

**主要步骤**:
1. 从数据库获取任务信息
2. 创建临时目录
3. 下载数据集文件（从 CSGHub）
4. 查找 PDF 文件
5. 调用转换函数

### 2. 选择转换函数

**位置**: ```226:229:data_celery/formatify/tasks.py```

```python
case DataFormatTypeEnum.PDF.value:
    match format_task.to_data_type:
        case DataFormatTypeEnum.Markdown.value:
            convert_func = convert_pdf_to_markdown
```

### 3. 遍历文件并转换

**位置**: ```247:273:data_celery/formatify/tasks.py```

- 遍历下载的文件目录
- 对每个 PDF 文件调用 `convert_pdf_to_markdown()`
- 传递 `mineru_api_url` 参数

### 4. PDF 转 Markdown 核心函数

**函数**: `convert_pdf_to_markdown(file_path, task_uid, mineru_api_url)`

**位置**: ```668:783:data_celery/formatify/tasks.py```

**主要步骤**:

#### 4.1 配置 MinerU API
```python
# 获取 MinerU API URL
if mineru_api_url:
    server_url = mineru_api_url
else:
    server_url = os.getenv("MINERU_API_URL", "http://111.4.242.20:30000")

# 配置 backend
backend = os.getenv("MINERU_BACKEND", "sglang-client")
```

#### 4.2 创建临时目录
```python
temp_output_dir = Path(file_path).parent / f"_temp_pdf_convert_{pdf_file_name}"
temp_output_dir.mkdir(exist_ok=True)
```

#### 4.3 启动 MinerU 子进程
```python
cmd = [
    python_exe,
    str(mineru_worker_script),  # mineru_worker.py
    file_path,                   # PDF 文件路径
    str(temp_output_dir),        # 临时输出目录
    server_url,                  # MinerU API URL
    backend,                     # backend 类型
    str(result_json_path)        # 结果 JSON 文件路径
]

process = subprocess.Popen(cmd, ...)
process.wait()
```

### 5. MinerU Worker 子进程

**文件**: `data_celery/formatify/mineru_worker.py`

**函数**: `main()`

**位置**: ```12:65:data_celery/formatify/mineru_worker.py```

**主要步骤**:

#### 5.1 读取 PDF 文件
```python
pdf_bytes = read_fn(Path(pdf_file_path))
```

#### 5.2 调用 MinerU API
```python
middle_json, _ = vlm_doc_analyze(
    pdf_bytes,
    image_writer=image_writer,
    backend=backend,backend=backend,
    server_url=server_url
)
```

**关键点**:
- `vlm_doc_analyze` 是 MinerU 库的函数
- 通过 HTTP 调用 MinerU API 服务器
- 使用指定的 backend（sglang-client/transformers/sglang-engine）
- 返回 `middle_json`（包含 PDF 解析结果）

#### 5.3 保存结果
```python
result = {
    "success": True,
    "middle_json": middle_json
}
# 保存到 result_json_path
```

### 6. 生成 Markdown

**位置**: ```738:753:data_celery/formatify/tasks.py```

**主要步骤**:

#### 6.1 读取 MinerU 结果
```python
with open(result_json_path, 'r', encoding='utf-8') as f:
    result_data = json.load(f)

middle_json = result_data["middle_json"]
```

#### 6.2 准备环境
```python
local_image_dir, local_md_dir = prepare_env(str(temp_output_dir), pdf_file_name, "vlm")
md_writer = FileBasedDataWriter(local_md_dir)
```

#### 6.3 生成 Markdown 内容
```python
pdf_info = middle_json["pdf_info"]
md_content_str = vlm_union_make(pdf_info, MakeMode.MM_MD, image_dir)
```

**关键点**:
- `vlm_union_make` 将 PDF 信息转换为 Markdown
- `MakeMode.MM_MD` 指定输出格式为 Markdown

#### 6.4 保存 Markdown 文件
```python
md_writer.write_string(markdown_filename, md_content_str)
markdown_file_path = Path(local_md_dir) / markdown_filename
final_markdown_path = os.path.splitext(file_path)[0] + '.md'
shutil.move(str(markdown_file_path), final_markdown_path)
```

### 7. 清理和返回

**位置**: ```755:765:data_celery/formatify/tasks.py```

- 删除原始 PDF 文件
- 删除临时目录
- 返回转换结果

## 关键组件

### MinerU API 服务器
- **URL**: 通过 `MINERU_API_URL` 环境变量配置，默认 `http://111.4.242.20:30000`
- **作用**: 处理 PDF 文件，返回解析结果
- **Backend**: 支持 `sglang-client`, `transformers`, `sglang-engine`

### MinerU 库
- **模块**: `mineru.backend.vlm.vlm_analyze`
- **函数**: `vlm_doc_analyze()` - 分析 PDF
- **模块**: `mineru.backend.vlm.vlm_middle_json_mkcontent`
- **函数**: `vlm_union_make()` - 生成 Markdown

### 子进程设计
- **原因**: 避免阻塞 Celery Worker
- **实现**: 使用 `subprocess.Popen` 启动独立进程
- **通信**: 通过 JSON 文件传递结果

## 数据流

```
PDF 文件
  ↓
mineru_worker.py (子进程)
  ↓
MinerU API 服务器 (HTTP 请求)
  ↓
middle_json (PDF 解析结果)
  ↓
vlm_union_make() (生成 Markdown)
  ↓
Markdown 文件
```

## 错误处理

1. **MinerU API 连接失败**: 记录错误，返回失败状态
2. **Backend 不支持**: 记录错误信息，包含支持的 backend 列表
3. **PDF 解析失败**: 记录错误，继续处理下一个文件
4. **文件写入失败**: 记录错误，返回失败状态

## 配置参数

- `MINERU_API_URL`: MinerU API 服务器地址
- `MINERU_BACKEND`: Backend 类型（sglang-client/transformers/sglang-engine）
- `mineru_api_url`: 任务级别的 MinerU API URL（优先级最高）

