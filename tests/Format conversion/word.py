import mammoth
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('word_conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WordConverter')


def docx_to_md_with_images(input_path, output_dir, **kwargs):
    """
    将Word文件转换为Markdown格式
    :param input_path: Word文件路径
    :param output_dir: 输出目录
    :param kwargs: 额外参数
    :return: 转换结果字典
    """
    try:
        docx_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # 设置输出Markdown路径和图片目录
        output_md_path = output_dir / f"{docx_path.stem}.md"
        image_dir = output_dir / "images"
        image_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始处理Word文件: {docx_path}")

        def convert_image(image):
            # 正确用法 ↓↓↓
            with image.open() as image_bytes:
                data = image_bytes.read()
            image_name = f"image{convert_image.counter}.png"
            convert_image.counter += 1
            image_path = image_dir / image_name
            with open(image_path, "wb") as f:
                f.write(data)
            return {"src": str(image_path.relative_to(output_md_path.parent))}

        convert_image.counter = 1

        with open(docx_path, "rb") as docx_file:
            result = mammoth.convert_to_markdown(
                docx_file,
                convert_image=mammoth.images.img_element(convert_image)
            )
            md_text = result.value

            with open(output_md_path, "w", encoding="utf-8") as f:
                f.write(md_text)

            logger.info(f"✅ 转换完成，Markdown 文件：{output_md_path.resolve()}")
            logger.info(f"✅ 图片提取目录：{image_dir.resolve()}")

            return {
                "md_file": str(output_md_path),
                "image_dir": str(image_dir)
            }

    except Exception as e:
        logger.error(f"Word转换失败: {str(e)}", exc_info=True)
        raise


# 示例调用
if __name__ == "__main__":
    try:
        docx_to_md_with_images(
            r"data/word/word.docx",
            r"data/word/output",
        )
    except Exception as e:
        logger.error(f"示例调用失败: {str(e)}")
