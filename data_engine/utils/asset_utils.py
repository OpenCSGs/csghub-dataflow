import json
import os

import requests
from loguru import logger

from .cache_utils import DATA_JUICER_ASSETS_CACHE

# Default directory to store auxiliary resources
ASSET_DIR = DATA_JUICER_ASSETS_CACHE

# Default cached assets links for downloading
ASSET_LINKS = {
    'flagged_words':
    'https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/'
    'data_juicer/flagged_words.json',
    'stopwords':
    'https://dail-wlcb.oss-cn-wulanchabu.aliyuncs.com/'
    'data_juicer/stopwords.json',
}


def load_words_asset(words_dir: str, words_type: str):
    """
    Load words from a asset file named `words_type`, if not find a valid asset
    file, then download it from ASSET_LINKS cached by data_engine team.

    :param words_dir: directory that stores asset file(s)
    :param words_type: name of target words assets
    :return: a dict that stores words assets, whose keys are language
        names, and the values are lists of words
    """
    words_dict = {}
    os.makedirs(words_dir, exist_ok=True)

    logger.info(f'[load_words_asset] Searching for {words_type} in directory: {words_dir}')
    
    # try to load words from `words_type` file
    for filename in os.listdir(words_dir):
        if filename.endswith('.json') and words_type in filename:
            file_path = os.path.join(words_dir, filename)
            logger.info(f'[load_words_asset] ✓ Found local file: {file_path}')
            with open(file_path, 'r') as file:
                loaded_words = json.load(file)
                for key in loaded_words:
                    if key in words_dict:
                        words_dict[key] += loaded_words[key]
                    else:
                        words_dict[key] = loaded_words[key]
            logger.info(f'[load_words_asset] ✓ Successfully loaded from local file (no network access)')
    
    # if the asset file is not found, then download it from ASSET_LINKS
    if not bool(words_dict):
        download_url = ASSET_LINKS[words_type]
        logger.warning(f'[load_words_asset] ✗ Local file NOT found in {words_dir}')
        logger.info(f'[load_words_asset] ⬇ Attempting to download from: {download_url}')
        
        response = requests.get(download_url)
        words_dict = response.json()
        
        # cache the asset file locally
        cache_path = os.path.join(words_dir, f'{words_type}.json')
        with open(cache_path, 'w') as file:
            json.dump(words_dict, file)
        logger.info(f'[load_words_asset] ✓ Downloaded and cached to: {cache_path}')

    return words_dict
