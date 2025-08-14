import zipfile
import shutil
import os
import zipfile
import logging
from pathlib import Path
from pptx2md import convert, ConversionConfig


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ppt_conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('PPTConverter')


def clean_pptx(input_pptx: Path, output_pptx: Path):

    temp_dir = Path("temp_pptx")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir()


    try:
        with zipfile.ZipFile(input_pptx, 'r') as zf:
            for name in zf.namelist():
                try:
                    zf.read(name)

                    target_path = temp_dir / name
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(target_path, "wb") as f:
                        f.write(zf.read(name))
                except Exception as e:
                    logger.warning(f"⚠️ 跳过损坏文件: {name} ({e})")


        with zipfile.ZipFile(output_pptx, 'w') as zf_out:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_dir)
                    zf_out.write(file_path, arcname)

        logger.info(f"成功清理PPT文件: {input_pptx}")
        return True
    except Exception as e:
        logger.error(f"清理PPT文件失败: {e}", exc_info=True)
        return False
    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


def pptx_to_md(input_path, output_dir, **kwargs):

    try:
        input_path = Path(input_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"开始处理PPT文件: {input_path}")


        output_md = output_dir / f"{input_path.stem}.md"
        image_dir = output_dir / "img"
        image_dir.mkdir(exist_ok=True)


        cleaned_pptx_path = output_dir / f"{input_path.stem}_cleaned.pptx"
        if not clean_pptx(input_path, cleaned_pptx_path):
            logger.warning(f"使用原始PPT文件继续转换: {input_path}")
            cleaned_pptx_path = input_path


        convert(
            ConversionConfig(
                pptx_path=cleaned_pptx_path,
                output_path=output_md,
                image_dir=image_dir,
                disable_notes=True
            )
        )

        if cleaned_pptx_path != input_path and cleaned_pptx_path.exists():
            cleaned_pptx_path.unlink()

        logger.info(f"PPT转换完成: {output_md}")
        return {
            "md_file": str(output_md),
            "image_dir": str(image_dir)
        }

    except Exception as e:
        logger.error(f"PPT转换失败: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    try:
        pptx_path = Path("data/ppt/ppt.pptx")
        output_dir = Path("data/ppt/output")
        output_dir.mkdir(exist_ok=True)
        pptx_to_md(str(pptx_path), str(output_dir))
        print("✅ 转换完成")
    except Exception as e:
        print(f"❌ 转换失败: {str(e)}")