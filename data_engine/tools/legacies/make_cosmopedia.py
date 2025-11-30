import os

import fire
import pandas as pd
from loguru import logger

from data_engine.core.data import add_same_content_to_new_column
from data_engine.format import load_formatter
from data_engine.ops.filter.language_id_score_filter import \
    LanguageIDScoreFilter
from data_engine.ops.mapper.text_make_cosmopedia import MakeCosmopediaMapper
from data_engine.utils.constant import Fields, StatsKeys

def main(src_dir, target_dir, suffixes=[], num_proc=1,
         web_text_max_len=800, model_url="https://euqnoct5ophc.space.opencsg.com/v1/chat/completions",
         model="THUDM/LongWriter-glm4-9b", auth_token="9acc3ea387b5479607bdeb5386af6e3483fbf070",
         content='''网页摘录："{web_text}"。
以 WikiHow 的风格写一篇长而非常详细的教程，教程与此网页摘录有相关性。
教程中需要包括对每个步骤的深入解释以及它如何帮助实现预期结果。你可以自由补充其他相关知识。
确保清晰性和实用性，让读者能够轻松遵循教程完成任务。内容中不应包含广告或涉及隐私的信息。
不要使用图像。请直接开始撰写教程。'''):

    # check if the source directory exists.
    if not os.path.exists(src_dir):
        raise ValueError('The raw source data directory does not exist,'
                         ' Please check and retry.')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir, exist_ok=True)

    formatter = load_formatter(src_dir, text_keys=['text', 'title'], suffixes=suffixes)
    dataset = formatter.load_dataset(num_proc)

    op = MakeCosmopediaMapper()
    op.web_text_max_len = web_text_max_len
    op.model_url = model_url
    op.model = model
    op.auth_token = auth_token
    op.content = content

    dataset = dataset.map(op.process, num_proc=num_proc)

    output_file = os.path.join(target_dir, 'cosmopedia_output.jsonl')
    dataset.to_json(output_file, force_ascii=False)
    logger.info(f'Dataset saved to {output_file}')

    return output_file

