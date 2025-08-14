import os
import logging
import time
import concurrent.futures
from pathlib import Path
from typing import List, Dict, Callable, Optional


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('conversion.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('FileConverter')

class ConversionTask:
    def __init__(
            self, task_id: str, file_path: str, output_dir: str, 
            converter_func: Callable, **kwargs):
        self.task_id = task_id
        self.file_path = Path(file_path)
        self.output_dir = Path(output_dir)
        self.converter_func = converter_func
        self.kwargs = kwargs
        self.status = 'pending'
        self.start_time = None
        self.end_time = None
        self.result = None
        self.error = None

    def execute(self):
        try:
            self.status = 'running'
            self.start_time = time.time()
            logger.info(f'Starting conversion task {self.task_id}: {self.file_path}')


            self.output_dir.mkdir(parents=True, exist_ok=True)


            self.result = self.converter_func(
                str(self.file_path), 
                str(self.output_dir),
                **self.kwargs
            )

            self.status = 'completed'
            logger.info(f'Completed conversion task {self.task_id}: {self.file_path}')
            return self.result

        except Exception as e:
            self.status = 'failed'
            self.error = str(e)
            logger.error(f'Failed conversion task {self.task_id}: {self.file_path}, Error: {str(e)}', exc_info=True)
            raise
        finally:
            self.end_time = time.time()

class ParallelConverter:
    def __init__(self, max_workers: Optional[int] = None):
        self.max_workers = max_workers or os.cpu_count()
        self.tasks: List[ConversionTask] = []
        self.executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix='converter'
        )
        logger.info(f'Initialized ParallelConverter with max_workers={self.max_workers}')

    def add_task(self, task: ConversionTask):
        self.tasks.append(task)
        logger.info(f'Added task {task.task_id} to queue')

    def run_all(self) -> Dict[str, ConversionTask]:

        logger.info(f'Starting {len(self.tasks)} conversion tasks')
        futures = {
            self.executor.submit(task.execute): task 
            for task in self.tasks
        }

        results = {}
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            try:
                future.result()
            except Exception:

                pass
            results[task.task_id] = task

        logger.info(f'All conversion tasks completed')
        return results

    def shutdown(self):
        self.executor.shutdown()


from excel import excel_to_formats
from ppt import pptx_to_md
from word import docx_to_md_with_images


FORMAT_CONVERTERS = {
    '.xlsx': excel_to_formats,
    '.xls': excel_to_formats,
    '.pptx': pptx_to_md,
    '.docx': docx_to_md_with_images
}

def convert_files(
        file_paths: List[str], 
        output_dir: str, 
        max_workers: Optional[int] = None,** kwargs):


    converter = ParallelConverter(max_workers=max_workers)
    output_root = Path(output_dir)

    for i, file_path in enumerate(file_paths):
        file_path = Path(file_path)
        if not file_path.exists():
            logger.error(f'File not found: {file_path}')
            continue


        ext = file_path.suffix.lower()
        if ext not in FORMAT_CONVERTERS:
            logger.error(f'Unsupported file format: {ext} for file {file_path}')
            continue

        task_id = f'task_{i}_{file_path.stem}'

        task_output_dir = output_root / file_path.stem


        task = ConversionTask(
            task_id=task_id,
            file_path=str(file_path),
            output_dir=str(task_output_dir),
            converter_func=FORMAT_CONVERTERS[ext],
            **kwargs
        )
        converter.add_task(task)


    results = converter.run_all()
    converter.shutdown()
    return results

if __name__ == '__main__':

    files_to_convert = [
        'data/Excel/excel.xlsx',
        'data/ppt/ppt.pptx',
        'data/word/word.docx'
    ]
    
    results = convert_files(
        file_paths=files_to_convert,
        output_dir='data/converted_output',
        max_workers=3
    )
    

    print('\n转换结果汇总:')
    for task_id, task in results.items():
        status = '成功' if task.status == 'completed' else '失败'
        print(f'{task_id}: {task.file_path} - {status}')
        if task.error:
            print(f'  错误信息: {task.error}')