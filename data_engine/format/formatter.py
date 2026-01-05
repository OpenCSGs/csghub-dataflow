import os
from typing import List, Tuple, Union

from datasets import Dataset, DatasetDict, concatenate_datasets, load_dataset
from loguru import logger

from data_engine.utils.constant import Fields
from data_engine.utils.file_utils import (find_files_with_suffix,
                                          is_absolute_path)
from data_engine.utils.registry import Registry

FORMATTERS = Registry('Formatters')


class BaseFormatter:
    """Base class to load dataset."""

    def load_dataset(self, *args) -> Dataset:
        raise NotImplementedError


class LocalFormatter(BaseFormatter):
    """The class is used to load a dataset from local files or local
    directory."""

    def __init__(
        self,
        dataset_path: str,
        type: str,
        suffixes: Union[str, List[str], Tuple[str]] = None,
        text_keys: List[str] = None,
        add_suffix=False,
        **kwargs,
    ):
        """
        Initialization method.

        :param dataset_path: path to a dataset file or a dataset
            directory
        :param type: a packaged dataset module type (json, csv, etc.)
        :param suffixes: files with specified suffixes to be processed
        :param text_keys: key names of field that stores sample
            text.
        :param add_suffix: whether to add the file suffix to dataset
            meta info
        :param kwargs: extra args
        """
        self.type = type
        self.kwargs = kwargs
        self.text_keys = text_keys
        self.dataset_path = dataset_path
        self.suffixes = suffixes
        self.add_suffix = add_suffix

    def load_dataset(self, num_proc: int = 1, global_cfg=None) -> Dataset:
        """
        Load a dataset from dataset file or dataset directory, and unify its
        format.

        :param num_proc: number of processes when loading the dataset
        :param global_cfg: global cfg used in consequent processes,
        :return: formatted dataset
        """
        from datasets.exceptions import DatasetGenerationError
        
        self.data_files = find_files_with_suffix(self.dataset_path, self.suffixes)
        
        # Try to load dataset normally first
        try:
            datasets = load_dataset(
                self.type,
                data_files={
                    key.strip('.'): self.data_files[key]
                    for key in self.data_files
                },
                num_proc=num_proc,
                **self.kwargs
            )
        except Exception as e:
            # Only handle type conversion/inference errors, other errors should be raised directly
            error_msg = str(e).lower()
            is_type_error = (
                isinstance(e, DatasetGenerationError) or
                'type' in error_msg or
                'arrow' in error_msg or
                'inference' in error_msg or
                'conversion' in error_msg or
                'schema' in error_msg
            )
            
            if not is_type_error:
                # Not a type conversion error, raise directly
                raise
            
            # If loading fails due to type inference issues (e.g., empty strings in any field)
            # Clean the data files by replacing ALL empty strings with None
            original_error = e
            logger.warning(f"Dataset loading failed with type conversion error: {e}")
            logger.info("Attempting to fix data by cleaning empty strings in all fields...")
            
            import json
            import tempfile
            import os
            from pathlib import Path
            
            # Clean all fields: replace empty strings with None to avoid type conversion errors
            cleaned_files = {}
            try:
                for suffix, file_list in self.data_files.items():
                    cleaned_list = []
                    for file_path in file_list:
                        # Create a temporary cleaned file using NamedTemporaryFile (Windows compatible)
                        temp_file = tempfile.NamedTemporaryFile(
                            mode='w', 
                            suffix=suffix, 
                            delete=False, 
                            encoding='utf-8'
                        )
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f_in:
                                for line in f_in:
                                    try:
                                        data = json.loads(line)
                                        # Replace empty strings with None for ALL fields
                                        # This prevents PyArrow type inference errors for any field type
                                        for field, value in list(data.items()):
                                            if value == '':
                                                data[field] = None
                                        temp_file.write(json.dumps(data, ensure_ascii=False) + '\n')
                                    except json.JSONDecodeError:
                                        # If not valid JSON, write as-is
                                        temp_file.write(line)
                            temp_file.close()
                            cleaned_list.append(temp_file.name)
                        except Exception as cleanup_error:
                            temp_file.close()
                            try:
                                os.unlink(temp_file.name)
                            except:
                                pass
                            raise cleanup_error
                    cleaned_files[suffix] = cleaned_list
                
                # Retry loading with cleaned files
                datasets = load_dataset(
                    self.type,
                    data_files={
                        key.strip('.'): cleaned_files[key]
                        for key in cleaned_files
                    },
                    num_proc=num_proc,
                    **self.kwargs
                )
                logger.info("Successfully loaded dataset after cleaning all empty strings")
            except Exception as retry_error:
                # If retry also fails, raise the original error with context
                logger.error(f"Failed to load dataset even after cleaning. Original error: {original_error}")
                logger.error(f"Retry error: {retry_error}")
                raise original_error from retry_error
            finally:
                # Clean up temporary files
                for file_list in cleaned_files.values():
                    for temp_file in file_list:
                        try:
                            os.unlink(temp_file)
                        except:
                            pass
        if self.add_suffix:
            logger.info('Add suffix info into dataset...')
            datasets = add_suffixes(datasets, num_proc)
        else:
            from data_engine.core.data import NestedDataset
            datasets = NestedDataset(
                concatenate_datasets([ds for _, ds in datasets.items()]))
        ds = unify_format(datasets,
                          text_keys=self.text_keys,
                          num_proc=num_proc,
                          global_cfg=global_cfg)
        return ds


class RemoteFormatter(BaseFormatter):
    """The class is used to load a dataset from repository of huggingface
    hub."""

    def __init__(self,
                 dataset_path: str,
                 text_keys: List[str] = None,
                 **kwargs):
        """
        Initialization method.

        :param dataset_path: a dataset file or a dataset directory
        :param text_keys: key names of field that stores sample
            text.
        :param kwargs: extra args
        """
        self.path = dataset_path
        self.text_keys = text_keys
        self.kwargs = kwargs

    def load_dataset(self, num_proc: int = 1, global_cfg=None) -> Dataset:
        """
        Load a dataset from HuggingFace, and unify its format.

        :param num_proc: number of processes when loading the dataset
        :param global_cfg: the global cfg used in consequent processes,
        :return: formatted dataset
        """
        ds = load_dataset(self.path,
                          split='train',
                          num_proc=num_proc,
                          **self.kwargs)
        ds = unify_format(ds,
                          text_keys=self.text_keys,
                          num_proc=num_proc,
                          global_cfg=global_cfg)
        return ds


def add_suffixes(datasets: DatasetDict, num_proc: int = 1) -> Dataset:
    """
    Add suffix filed to datasets.

    :param datasets: a DatasetDict object
    :param num_proc: number of processes to add suffixes
    :return: datasets with suffix features.
    """
    logger.info('Add suffix column for dataset')
    from data_engine.core.data import add_same_content_to_new_column
    for key, ds in datasets.items():
        if Fields.suffix not in ds.features:
            datasets[key] = ds.map(add_same_content_to_new_column,
                                   fn_kwargs={
                                       'new_column_name': Fields.suffix,
                                       'initial_value': '.' + key
                                   },
                                   num_proc=num_proc,
                                   desc='Adding new column for suffix')
    datasets = concatenate_datasets([ds for _, ds in datasets.items()])
    from data_engine.core.data import NestedDataset
    return NestedDataset(datasets)


def unify_format(
    dataset: Dataset,
    text_keys: Union[List[str], str] = 'text',
    num_proc: int = 1,
    global_cfg=None,
) -> Dataset:
    """
    Get an unified internal format, conduct the following modifications.

    1. check keys of dataset

    2. filter out those samples with empty or None text

    :param dataset: input dataset
    :param text_keys: original text key(s) of dataset.
    :param num_proc: number of processes for mapping
    :param global_cfg: the global cfg used in consequent processes,
        since cfg.text_key may be modified after unifying

    :return: unified_format_dataset
    """
    from data_engine.core.data import NestedDataset
    if isinstance(dataset, DatasetDict):
        datasets = list(dataset.values())
        assert len(datasets) == 1, 'Please make sure the passed datasets ' \
                                   'contains only 1 dataset'
        dataset = datasets[0]
    assert isinstance(dataset, Dataset) or \
           isinstance(dataset, NestedDataset), \
           'Currently we only support processing data' \
           'with huggingface-Dataset format'

    if text_keys is None:
        text_keys = []

    if isinstance(text_keys, str):
        text_keys = [text_keys]

    logger.info('Unifying the input dataset formats...')

    dataset = NestedDataset(dataset)

    # 1. check text related keys
    for key in text_keys:
        if key not in dataset.features:
            err_msg = f'There is no key [{key}] in dataset. You might set ' \
                      f'wrong text_key in the config file for your dataset. ' \
                      f'Please check and retry!'
            logger.error(err_msg)
            raise ValueError(err_msg)

    # 2. filter out those samples with empty or None text
    # TODO: optimize the filtering operation for better efficiency
    logger.info(f'There are {len(dataset)} sample(s) in the original dataset.')

    def non_empty_text(sample, target_keys):
        for target_key in target_keys:
            # TODO: case for CFT, in which the len(sample[target_key]) == 0
            if sample[target_key] is None:
                # we filter out the samples contains at least None column
                # since the op can not handle it now
                return False
        return True

    dataset = dataset.filter(non_empty_text,
                             num_proc=num_proc,
                             fn_kwargs={'target_keys': text_keys})
    logger.info(f'{len(dataset)} samples left after filtering empty text.')

    # 3. convert relative paths to absolute paths
    if global_cfg:
        ds_dir = global_cfg.dataset_dir
        image_key = global_cfg.image_key
        audio_key = global_cfg.audio_key
        video_key = global_cfg.video_key

        data_path_keys = []
        if image_key in dataset.features:
            data_path_keys.append(image_key)
        if audio_key in dataset.features:
            data_path_keys.append(audio_key)
        if video_key in dataset.features:
            data_path_keys.append(video_key)
        if len(data_path_keys) == 0:
            # no image/audio/video path list in dataset, no need to convert
            return dataset

        if ds_dir == '':
            return dataset

        logger.info('Converting relative paths in the dataset to their '
                    'absolute version. (Based on the directory of input '
                    'dataset file)')

        # function to convert relative paths to absolute paths
        def rel2abs(sample, path_keys, dataset_dir):
            for path_key in path_keys:
                if path_key not in sample:
                    continue
                paths = sample[path_key]
                if not paths:
                    continue
                new_paths = [
                    path if os.path.isabs(path) else os.path.join(
                        dataset_dir, path) for path in paths
                ]
                sample[path_key] = new_paths
            return sample

        dataset = dataset.map(rel2abs,
                              num_proc=num_proc,
                              fn_kwargs={
                                  'path_keys': data_path_keys,
                                  'dataset_dir': ds_dir
                              })
    else:
        logger.warning('No global config passed into unify_format function. '
                       'Relative paths in the dataset might not be converted '
                       'to their absolute versions. Data of other modalities '
                       'might not be able to find by Data-Juicer.')

    return dataset


def load_formatter(dataset_path,
                   text_keys=None,
                   suffixes=None,
                   add_suffix=False,
                   **kwargs) -> BaseFormatter:
    """
    Load the appropriate formatter for different types of data formats.

    :param dataset_path: Path to dataset file or dataset directory
    :param text_keys: key names of field that stores sample text.
        Default: None
    :param suffixes: the suffix of files that will be read. Default:
        None
    :return: a dataset formatter.
    """

    if suffixes is None:
        suffixes = []
    ext_num = {}
    if os.path.isdir(dataset_path) or os.path.isfile(dataset_path):
        file_dict = find_files_with_suffix(dataset_path, suffixes)
        if not file_dict:
            raise IOError(
                'Unable to find files matching the suffix from {}'.format(
                    dataset_path))
        for ext in file_dict:
            ext_num[ext] = len(file_dict[ext])

    # local dataset
    if ext_num:
        formatter_num = {}
        for name, formatter in FORMATTERS.modules.items():
            formatter_num[name] = 0
            for ext in ext_num:
                if ext in formatter.SUFFIXES:
                    formatter_num[name] += ext_num[ext]
        formatter = max(formatter_num, key=lambda x: formatter_num[x])
        target_suffixes = set(ext_num.keys()).intersection(
            set(FORMATTERS.modules[formatter].SUFFIXES))
        return FORMATTERS.modules[formatter](dataset_path,
                                             text_keys=text_keys,
                                             suffixes=target_suffixes,
                                             add_suffix=add_suffix,
                                             **kwargs)

    # try huggingface dataset hub
    elif not is_absolute_path(dataset_path) and dataset_path.count('/') <= 1:
        return RemoteFormatter(dataset_path, text_keys=text_keys, **kwargs)

    # no data
    else:
        raise ValueError(f'Unable to load the dataset from [{dataset_path}]. '
                         f'It might be because DataFlow doesn\'t support '
                         f'the format of this dataset, or the path of this '
                         f'dataset is incorrect.Please check if it\'s a valid '
                         f'dataset path and retry.')
