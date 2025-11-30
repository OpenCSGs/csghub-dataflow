# 文件格式转换工具

## 项目概述
这是一个支持多种文档格式并行转换的工具，能够将Excel、PowerPoint和Word文件转换为Markdown或其他格式，并提供错误处理和日志记录功能。

## 核心功能
- 批量转换Excel(.xlsx, .xls)、PowerPoint(.pptx)和Word(.docx)文件
- 并行处理多个转换任务以提高效率
- 详细的日志记录和错误处理
- 为不同文件类型生成结构化输出

## 文件结构
```
Format conversion/
├── converter.py        # 主程序，包含并行转换逻辑
├── excel.py            # Excel转换功能
├── ppt.py              # PowerPoint转换功能
├── word.py             # Word转换功能
├── data/
│   ├── Excel/          # Excel源文件和输出
│   ├── ppt/            # PPT源文件和输出
│   ├── word/           # Word源文件和输出
│   └── converted_output/ # 转换结果输出目录
├── *.log               # 各种转换日志文件
└── README.md           # 项目文档
```

## 转换方法及依赖库

### Excel转换
- **功能**：将Excel文件转换为JSON、CSV和Parquet格式
- **核心库**：pandas
- **代码位置**：excel.py
- **函数**：excel_to_formats

### PowerPoint转换
- **功能**：将PPTX文件转换为Markdown格式（包含图片提取）
- **核心库**：pptx2md, zipfile
- **代码位置**：ppt.py
- **函数**：pptx_to_md

### Word转换
- **功能**：将DOCX文件转换为Markdown格式（包含图片提取）
- **核心库**：mammoth
- **代码位置**：word.py
- **函数**：docx_to_md_with_images

### 并行处理
- **功能**：管理和执行多个并行转换任务
- **核心库**：concurrent.futures
- **代码位置**：converter.py
- **类**：ParallelConverter, ConversionTask

## 使用方法
1. 准备需要转换的文件，放置在data目录相应子文件夹中
2. 在converter.py的main函数中配置需要转换的文件路径
3. 运行主程序：`python converter.py`
4. 转换结果将保存在data/converted_output目录下

## 错误处理
- 所有转换错误会记录在相应的日志文件中
- 支持单个文件转换失败不影响其他文件处理
- 会自动创建输出目录，无需手动干预

## 日志文件
- conversion.log: 主程序转换日志
- excel_conversion.log: Excel转换专用日志
- ppt_conversion.log: PPT转换专用日志
- word_conversion.log: Word转换专用日志