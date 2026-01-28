import copy
import traceback
from functools import wraps

import pyarrow as pa
from loguru import logger

from data_engine import is_cuda_available
from data_engine.utils.constant import Fields
from data_engine.utils.mm_utils import size_to_bytes
from data_engine.utils.process_utils import calculate_np
from data_engine.utils.registry import Registry

from data_celery.mongo_tools.tools import (insert_pipline_job_run_task_log_error,
                                           insert_pipline_job_run_task_log_info,
                                           insert_pipline_job_run_task_log_debug,
                                           set_pipline_job_operator_status,OperatorStatusEnum)

OPERATORS = Registry('Operators')
UNFORKABLE = Registry('Unforkable')


def convert_list_dict_to_dict_list(samples):
    # reconstruct samples from "list of dicts" to "dict of lists"
    keys = samples[0].keys()
    res_samples = {}
    for key in keys:
        res_samples[key] = [s[key] for s in samples]
    return res_samples


def convert_dict_list_to_list_dict(samples):
    # reconstruct samples from "dict of lists" to "list of dicts"
    reconstructed_samples = []
    keys = list(samples.keys())
    # take any key, since they should be of same length
    for i in range(len(samples[keys[0]])):
        reconstructed_samples.append({key: samples[key][i] for key in samples})
    return reconstructed_samples


def convert_arrow_to_python(method):

    @wraps(method)
    def wrapper(sample, *args, **kwargs):
        if isinstance(sample, pa.Table):
            sample = sample.to_pydict()
        return method(sample, *args, **kwargs)

    return wrapper


def catch_map_batches_exception(method):
    """
    For batched-map sample-level fault tolerance.
    """

    @wraps(method)
    @convert_arrow_to_python
    def wrapper(samples, *args, **kwargs):
        try:
            return method(samples, *args, **kwargs)
        except Exception as e:
            from loguru import logger
            logger.error(
                f'An error occurred in mapper operation when processing '
                f'samples {samples}, {type(e)}: {e}')
            traceback.print_exc()
            ret = {key: [] for key in samples.keys()}
            ret[Fields.stats] = []
            ret[Fields.source_file] = []
            return ret

    return wrapper


def catch_map_single_exception(method):
    """
    For single-map sample-level fault tolerance.
    The input sample is expected batch_size = 1.
    """

    def is_batched(sample):
        val_iter = iter(sample.values())
        first_val = next(val_iter)
        if not isinstance(first_val, list):
            return False
        first_len = len(first_val)
        return all(
            isinstance(val, list) and len(val) == first_len
            for val in val_iter)

    @wraps(method)
    @convert_arrow_to_python
    def wrapper(sample, *args, **kwargs):
        if is_batched(sample):
            try:
                sample = convert_dict_list_to_list_dict(sample)[0]
                res_sample = method(sample, *args, **kwargs)
                return convert_list_dict_to_dict_list([res_sample])
            except Exception as e:
                from loguru import logger
                logger.error(
                    f'An error occurred in mapper operation when processing '
                    f'sample {sample}, {type(e)}: {e}')
                traceback.print_exc()
                ret = {key: [] for key in sample.keys()}
                ret[Fields.stats] = []
                ret[Fields.source_file] = []
                return ret
        else:
            # without fault tolerance
            return method(sample, *args, **kwargs)

    return wrapper


class OP:

    _accelerator = 'cpu'
    _batched_op = False

    def __init__(self, *args, **kwargs):
        """
        Base class of operators.

        :param text_key: the key name of field that stores sample texts
            to be processed.
        :param image_key: the key name of field that stores sample image list
            to be processed
        :param audio_key: the key name of field that stores sample audio list
            to be processed
        :param video_key: the key name of field that stores sample video list
            to be processed
        """
        # init data keys
        self.text_key = kwargs.get('text_key', 'text')
        self.image_key = kwargs.get('image_key', 'images')
        self.audio_key = kwargs.get('audio_key', 'audios')
        self.video_key = kwargs.get('video_key', 'videos')

        # whether the model can be accelerated using cuda
        _accelerator = kwargs.get('accelerator', None)
        if _accelerator is not None:
            self.accelerator = _accelerator
        else:
            self.accelerator = self._accelerator

        self.pipline_index = 0
        self.job_uid = ""

        # parameters to determind the number of procs for this op
        self.num_proc = kwargs.get('num_proc', None)
        self.cpu_required = kwargs.get('cpu_required', 1)
        self.mem_required = kwargs.get('mem_required', 0)
        if isinstance(self.mem_required, str):
            self.mem_required = size_to_bytes(self.mem_required) / 1024**3

        # nested wrappers
        from data_engine.core.data import wrap_func_with_nested_access
        for name in ['process', 'compute_stats', 'compute_hash']:
            method = getattr(self, name, None)
            if method and callable(method):
                setattr(self, f'_{name}', method)
                method = wrap_func_with_nested_access(method)
                setattr(self, name, method)

    @classmethod
    def is_batched_op(cls):
        return cls._batched_op

    def process(self, *args, **kwargs):
        raise NotImplementedError

    def use_cuda(self):
        return self.accelerator == 'cuda' and is_cuda_available()

    def runtime_np(self):
        op_proc = calculate_np(self._name, self.mem_required,
                               self.cpu_required, self.num_proc,
                               self.use_cuda(),job_uid=self.job_uid,run_op_index=self.pipline_index)
        logger.debug(
            f'Op [{self._name}] running with number of procs:{op_proc}')
        insert_pipline_job_run_task_log_debug(self.job_uid,f'Op [{self._name}] running with number of procs:{op_proc}',
                                              operator_name=self._name,operator_index=self.pipline_index)
        return op_proc

    def remove_extra_parameters(self, param_dict, keys=None):
        """
            at the begining of the init of the mapper op, call
            self.remove_extra_parameters(locals())
            to get the init parameter dict of the op for convenience

        """
        if keys is None:
            param_dict = {
                k: v
                for k, v in param_dict.items() if not k.startswith('_')
            }
            param_dict.pop('self', None)
        else:
            param_dict = {k: v for k, v in param_dict.items() if k not in keys}
        return param_dict

    def add_parameters(self, init_parameter_dict, **extra_param_dict):
        """
            add parameters for each sample, need to keep extra_param_dict
            and init_parameter_dict unchanged.
        """
        related_parameters = copy.deepcopy(init_parameter_dict)
        related_parameters.update(extra_param_dict)
        return related_parameters

    @classmethod
    @property
    def description(cls):
        pass

    @classmethod
    @property
    def sample(cls):
        pass 

    @classmethod
    @property
    def init_params(cls):
        pass

class Mapper(OP):

    def __init__(self, *args, **kwargs):
        """
        Base class that conducts data editing.

        :param text_key: the key name of field that stores sample texts
            to be processed.
        :param image_key: the key name of field that stores sample image list
            to be processed
        :param audio_key: the key name of field that stores sample audio list
            to be processed
        :param video_key: the key name of field that stores sample video list 
            to be processed
        """
        super(Mapper, self).__init__(*args, **kwargs)

        # runtime wrappers
        if self.is_batched_op():
            self.process = catch_map_batches_exception(self.process)
        else:
            self.process = catch_map_single_exception(self.process)

    def process(self, sample):
        """
        For sample level, sample --> sample

        :param sample: sample to process
        :return: processed sample
        """
        raise NotImplementedError

    def run(self, dataset, *, exporter=None, tracer=None):
        insert_pipline_job_run_task_log_info(self.job_uid, f"starting mapper job", operator_name=self._name,
                                             operator_index=self.pipline_index)
        set_pipline_job_operator_status(self.job_uid,OperatorStatusEnum.Processing,self._name,self.pipline_index)
        try:
            new_dataset = dataset.map(
                self.process,
                num_proc=self.runtime_np(),
                with_rank=self.use_cuda(),
                desc=self._name + '_process',
            )
            if tracer:
                tracer.trace_mapper(self._name, dataset, new_dataset,
                                    self.text_key,job_uid=self.job_uid,pipeline_index=self.pipline_index)
            set_pipline_job_operator_status(self.job_uid,OperatorStatusEnum.SUCCESS,self._name,self.pipline_index)
            return new_dataset
        except Exception as e:
            # logger.error(f"An error occurred during data mapping: {e}")
            set_pipline_job_operator_status(self.job_uid,OperatorStatusEnum.ERROR,self._name,self.pipline_index)
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  f"An error occurred during data mapping: {e}",
                                                  operator_name=self._name,operator_index=self.pipline_index)
            raise
        finally:
            insert_pipline_job_run_task_log_info(self.job_uid,"ending mapper job",operator_name=self._name,operator_index=self.pipline_index)


class Filter(OP):

    def __init__(self, *args, **kwargs):
        """
        Base class that removes specific info.

        :param text_key: the key name of field that stores sample texts
            to be processed
        :param image_key: the key name of field that stores sample image list
            to be processed
        :param audio_key: the key name of field that stores sample audio list
            to be processed
        :param video_key: the key name of field that stores sample video list
            to be processed
        """
        super(Filter, self).__init__(*args, **kwargs)
        self.stats_export_path = kwargs.get('stats_export_path', None)

        # runtime wrappers
        if self.is_batched_op():
            self.compute_stats = catch_map_batches_exception(
                self.compute_stats)
        else:
            self.compute_stats = catch_map_single_exception(self.compute_stats)

    def compute_stats(self, sample, context=False):
        """
        Compute stats for the sample which is used as a metric to decide
        whether to filter this sample.

        :param sample: input sample.
        :param context: whether to store context information of intermediate
            vars in the sample temporarily.
        :return: sample with computed stats
        """
        raise NotImplementedError

    def process(self, sample):
        """
        For sample level, sample --> Boolean.

        :param sample: sample to decide whether to filter
        :return: true for keeping and false for filtering
        """
        raise NotImplementedError

    def run(self, dataset, *, exporter=None, tracer=None):
        insert_pipline_job_run_task_log_info(self.job_uid, f"starting filter job", operator_name=self._name,
                                             operator_index=self.pipline_index)
        set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.Processing, self._name, self.pipline_index)
        try:
            if Fields.stats not in dataset.features:
                from data_engine.core.data import add_same_content_to_new_column
                dataset = dataset.map(add_same_content_to_new_column,
                                      fn_kwargs={
                                          'new_column_name': Fields.stats,
                                          'initial_value': {}
                                      },
                                      num_proc=self.runtime_np(),
                                      desc='Adding new column for stats')
            dataset = dataset.map(self.compute_stats,
                                  num_proc=self.runtime_np(),
                                  with_rank=self.use_cuda(),
                                  desc=self._name + '_compute_stats')
            if self.stats_export_path is not None:
                exporter.export_compute_stats(dataset, self.stats_export_path)
            new_dataset = dataset.filter(self.process,
                                         num_proc=self.runtime_np(),
                                         desc=self._name + '_process')

            # Generate detailed logging if enabled
            if getattr(self, 'enable_detailed_logging', False):
                self._log_filter_details(dataset, new_dataset)

            if tracer:
                tracer.trace_filter(self._name, dataset, new_dataset,job_uid=self.job_uid,pipeline_index=self.pipline_index)
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.SUCCESS, self._name, self.pipline_index)
            return new_dataset
        except Exception as e:
            # logger.error(f"An error occurred during data mapping: {e}")
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.ERROR, self._name, self.pipline_index)
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  f"An error occurred during data filter: {e}",
                                                  operator_name=self._name, operator_index=self.pipline_index)
            raise
        finally:
            insert_pipline_job_run_task_log_info(self.job_uid, "ending filter job", operator_name=self._name,
                                                 operator_index=self.pipline_index)

    def _log_filter_details(self, original_dataset, filtered_dataset):
        """
        Generate detailed logging for filter operations.
        Collects statistics from all samples and provides a summary at the end.
        """
        try:
            total_samples = len(original_dataset)
            
            # Skip logging if dataset is empty
            if total_samples == 0:
                return
            
            kept_samples = len(filtered_dataset)
            filtered_samples = total_samples - kept_samples

            # Initialize counters
            stats_counters = {
                'total': total_samples,
                'kept': 0,
                'below_min': 0,
                'above_max': 0,
                'invalid_type': 0,
                'null_value': 0,
            }

            # Process samples and collect statistics
            for idx, sample in enumerate(original_dataset):
                stats = sample.get(Fields.stats, {})
                detail_key = None

                # Find the detail key (it might vary by filter type)
                for key in stats.keys():
                    if key.endswith('_detail'):
                        detail_key = key
                        break

                if detail_key and detail_key in stats:
                    detail = stats[detail_key]
                    keep = detail.get('keep', False)
                    reason = detail.get('reason', 'unknown')

                    # Update counters
                    if keep:
                        stats_counters['kept'] += 1
                    else:
                        stats_counters[reason] = stats_counters.get(reason, 0) + 1

            # Generate and log summary statistics (only once at the end)
            self._log_summary_statistics(stats_counters)

        except Exception as e:
            import traceback
            error_msg = f"Failed to generate detailed logging: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            insert_pipline_job_run_task_log_error(
                self.job_uid,
                error_msg,
                operator_name=self._name,
                operator_index=self.pipline_index
            )

    def _log_summary_statistics(self, stats_counters):
        """Generate and log summary statistics with percentages."""
        total = stats_counters['total']
        
        # Skip logging if dataset is empty
        if total == 0:
            return
        
        kept = stats_counters['kept']
        filtered = total - kept

        # Output logs line by line for better display in UI
        self._log_line("="*60)
        self._log_line(f"[{self._name}] Filter Summary Statistics")
        self._log_line("="*60)
        self._log_line(f"Total samples: {total}")
        self._log_line(f"Kept samples: {kept} ({kept/total*100:.2f}%)")
        self._log_line(f"Filtered samples: {filtered} ({filtered/total*100:.2f}%)")

        if filtered > 0:
            self._log_line("")
            self._log_line("Filtered breakdown:")

            # Dynamically show all non-zero filter reasons (excluding 'total' and 'kept')
            for reason, count in sorted(stats_counters.items()):
                if reason not in ['total', 'kept'] and count > 0:
                    # Format reason name for display
                    reason_display = reason.replace('_', ' ').title()
                    self._log_line(f"  - {reason_display}: {count} ({count/total*100:.2f}%)")
        else:
            self._log_line("")
            self._log_line("No samples filtered. All samples passed the filter.")

        # Log filter-specific parameters
        self._log_filter_parameters()
        
        self._log_line("="*60)

    def _log_filter_parameters(self):
        """Log filter-specific parameters based on filter type."""
        self._log_line("")
        self._log_line("Filter parameters:")
        
        # text_high_score_filter
        if self._name == 'text_high_score_filter':
            self._log_line(f"  - Score field: {getattr(self, 'score_field', 'N/A')}")
            self._log_line(f"  - Min score: {getattr(self, 'min_score', 'N/A')}")
            self._log_line(f"  - Max score: {getattr(self, 'max_score', 'N/A')}")
        
        # flagged_words_filter
        elif self._name == 'flagged_words_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Tokenization: {getattr(self, 'tokenization', False)}")
            max_ratio = getattr(self, 'max_ratio', 0)
            self._log_line(f"  - Max ratio: {max_ratio} ({max_ratio*100:.2f}%)")
            self._log_line(f"  - Use words augmentation: {getattr(self, 'use_words_aug', False)}")
        
        # character_repetition_filter
        elif self._name == 'character_repetition_filter':
            self._log_line(f"  - Repetition length (n-gram): {getattr(self, 'n', 'N/A')}")
            min_ratio = getattr(self, 'min_ratio', 0)
            max_ratio = getattr(self, 'max_ratio', 0)
            self._log_line(f"  - Min ratio: {min_ratio} ({min_ratio*100:.2f}%)")
            self._log_line(f"  - Max ratio: {max_ratio} ({max_ratio*100:.2f}%)")
        
        # text_length_filter
        elif self._name == 'text_length_filter':
            self._log_line(f"  - Min length: {getattr(self, 'min_len', 'N/A')} characters")
            self._log_line(f"  - Max length: {getattr(self, 'max_len', 'N/A')} characters")
        
        # alphanumeric_filter
        elif self._name == 'alphanumeric_filter':
            self._log_line(f"  - Tokenization: {getattr(self, 'tokenization', False)}")
            min_ratio = getattr(self, 'min_ratio', 0)
            max_ratio = getattr(self, 'max_ratio', 0)
            self._log_line(f"  - Min ratio: {min_ratio} ({min_ratio*100:.2f}%)")
            self._log_line(f"  - Max ratio: {max_ratio} ({max_ratio*100:.2f}%)")
        
        # word_repetition_filter
        elif self._name == 'word_repetition_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Tokenization: {getattr(self, 'tokenization', False)}")
            self._log_line(f"  - Repetition length (n-gram): {getattr(self, 'n', 'N/A')}")
            min_ratio = getattr(self, 'min_ratio', 0)
            max_ratio = getattr(self, 'max_ratio', 0)
            self._log_line(f"  - Min ratio: {min_ratio} ({min_ratio*100:.2f}%)")
            self._log_line(f"  - Max ratio: {max_ratio} ({max_ratio*100:.2f}%)")
        
        # text_action_filter
        elif self._name == 'text_action_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Min action number: {getattr(self, 'min_action_num', 'N/A')}")
        
        # words_num_filter
        elif self._name == 'words_num_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Tokenization: {getattr(self, 'tokenization', False)}")
            self._log_line(f"  - Min number: {getattr(self, 'min_num', 'N/A')} words")
            self._log_line(f"  - Max number: {getattr(self, 'max_num', 'N/A')} words")
        
        # average_line_length_filter
        elif self._name == 'average_line_length_filter':
            self._log_line(f"  - Min average length: {getattr(self, 'min_len', 'N/A')} chars/line")
            self._log_line(f"  - Max average length: {getattr(self, 'max_len', 'N/A')} chars/line")
        
        # language_id_score_filter
        elif self._name == 'language_id_score_filter':
            lang = getattr(self, 'lang', None)
            self._log_line(f"  - Target language(s): {lang if lang else 'Any'}")
            min_score = getattr(self, 'min_score', 0)
            self._log_line(f"  - Min confidence score: {min_score} ({min_score*100:.2f}%)")
        
        # maximum_line_length_filter
        elif self._name == 'maximum_line_length_filter':
            self._log_line(f"  - Min max length: {getattr(self, 'min_len', 'N/A')} characters")
            self._log_line(f"  - Max max length: {getattr(self, 'max_len', 'N/A')} characters")
        
        # perplexity_filter
        elif self._name == 'perplexity_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Max perplexity: {getattr(self, 'max_ppl', 'N/A')}")
        
        # special_characters_filter
        elif self._name == 'special_characters_filter':
            min_ratio = getattr(self, 'min_ratio', 0)
            max_ratio = getattr(self, 'max_ratio', 0)
            self._log_line(f"  - Min ratio: {min_ratio} ({min_ratio*100:.2f}%)")
            self._log_line(f"  - Max ratio: {max_ratio} ({max_ratio*100:.2f}%)")
        
        # specified_field_filter
        elif self._name == 'specified_field_filter':
            self._log_line(f"  - Field key: {getattr(self, 'field_key', 'N/A')}")
            target_value = getattr(self, 'target_value', [])
            if len(target_value) > 5:
                self._log_line(f"  - Target values: {target_value[:5]}... ({len(target_value)} total)")
            else:
                self._log_line(f"  - Target values: {target_value}")
        
        # specified_numeric_field_filter
        elif self._name == 'specified_numeric_field_filter':
            self._log_line(f"  - Field key: {getattr(self, 'field_key', 'N/A')}")
            self._log_line(f"  - Min value: {getattr(self, 'min_value', 'N/A')}")
            self._log_line(f"  - Max value: {getattr(self, 'max_value', 'N/A')}")
        
        # stopwords_filter
        elif self._name == 'stopwords_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Tokenization: {getattr(self, 'tokenization', False)}")
            min_ratio = getattr(self, 'min_ratio', 0)
            self._log_line(f"  - Min ratio: {min_ratio} ({min_ratio*100:.2f}%)")
            self._log_line(f"  - Use words augmentation: {getattr(self, 'use_words_aug', False)}")
        
        # suffix_filter
        elif self._name == 'suffix_filter':
            suffixes = getattr(self, 'suffixes', [])
            if len(suffixes) > 10:
                self._log_line(f"  - Allowed suffixes: {suffixes[:10]}... ({len(suffixes)} total)")
            else:
                self._log_line(f"  - Allowed suffixes: {suffixes}")
        
        # text_entity_dependency_filter
        elif self._name == 'text_entity_dependency_filter':
            self._log_line(f"  - Language: {getattr(self, 'lang', 'N/A')}")
            self._log_line(f"  - Min dependency edges: {getattr(self, 'min_dependency_num', 'N/A')}")
            self._log_line(f"  - Keep strategy: {getattr(self, 'any_or_all', 'N/A')}")
        
        # token_num_filter
        elif self._name == 'token_num_filter':
            self._log_line(f"  - Tokenizer: {getattr(self, 'hf_tokenizer', 'N/A')}")
            self._log_line(f"  - Min tokens: {getattr(self, 'min_num', 'N/A')}")
            self._log_line(f"  - Max tokens: {getattr(self, 'max_num', 'N/A')}")
        
        # text_bloom_filter
        elif self._name == 'text_bloom_filter':
            self._log_line(f"  - Hash function: {getattr(self, 'hash_func', 'N/A')}")
            error_rate = getattr(self, 'error_rate', 0)
            self._log_line(f"  - Error rate: {error_rate}")
            self._log_line(f"  - Initial capacity: {getattr(self, 'initial_capacity', 'N/A')}")
        
        # multi_keyword_filter
        elif self._name == 'multi_keyword_filter':
            keywords = getattr(self, 'keywords', [])
            if len(keywords) > 10:
                self._log_line(f"  - Keywords: {keywords[:10]}... ({len(keywords)} total)")
            else:
                self._log_line(f"  - Keywords: {keywords}")
            self._log_line(f"  - Case sensitive: {getattr(self, 'case_sensitive', False)}")
        
        # Default fallback for unknown filters
        else:
            self._log_line(f"  - Filter type: {self._name}")
            self._log_line(f"  - (No specific parameter display configured)")

    def _log_line(self, message):
        """Log a single line to both logger and MongoDB."""
        logger.info(message)
        # Only write to MongoDB if job_uid exists
        if hasattr(self, 'job_uid') and self.job_uid:
            insert_pipline_job_run_task_log_info(
                self.job_uid,
                message,
                operator_name=self._name,
                operator_index=self.pipline_index
            )


class Deduplicator(OP):

    def __init__(self, *args, **kwargs):
        """
        Base class that conducts deduplication.

        :param text_key: the key name of field that stores sample texts
            to be processed
        :param image_key: the key name of field that stores sample image list
            to be processed
        :param audio_key: the key name of field that stores sample audio list
            to be processed
        :param video_key: the key name of field that stores sample video list
            to be processed
        """
        super(Deduplicator, self).__init__(*args, **kwargs)

        # runtime wrappers
        if self.is_batched_op():
            self.compute_hash = catch_map_batches_exception(self.compute_hash)
        else:
            self.compute_hash = catch_map_single_exception(self.compute_hash)

    def compute_hash(self, sample):
        """
        Compute hash values for the sample.

        :param sample: input sample
        :return: sample with computed hash value.
        """
        raise NotImplementedError

    def process(self, dataset, show_num=0):
        """
        For doc-level, dataset --> dataset.

        :param dataset: input dataset
        :param show_num: number of traced samples used when tracer is
            open.
        :return: deduplicated dataset and the sampled duplicate pairs.
        """
        raise NotImplementedError

    def run(self, dataset, *, exporter=None, tracer=None):
        insert_pipline_job_run_task_log_info(self.job_uid, f"starting duplicate job", operator_name=self._name,
                                             operator_index=self.pipline_index)
        set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.Processing, self._name, self.pipline_index)
        try:
            dataset = dataset.map(self.compute_hash,
                                  num_proc=self.runtime_np(),
                                  with_rank=self.use_cuda(),
                                  desc=self._name + '_compute_hash')
            show_num = tracer.show_num if tracer else 0
            new_dataset, dup_pairs = self.process(dataset, show_num)
            if tracer:
                tracer.trace_deduplicator(self._name, dataset, dup_pairs,job_uid=self.job_uid,pipeline_index=self.pipline_index)
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.SUCCESS, self._name, self.pipline_index)
            return new_dataset
        except Exception as e:
            # logger.error(f"An error occurred during data mapping: {e}")
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.ERROR, self._name, self.pipline_index)
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  f"An error occurred during data duplicate: {e}",
                                                  operator_name=self._name, operator_index=self.pipline_index)
            raise
        finally:
            insert_pipline_job_run_task_log_info(self.job_uid, "ending duplicate job", operator_name=self._name,
                                                 operator_index=self.pipline_index)


class Selector(OP):

    def __init__(self, *args, **kwargs):
        """
        Base class that conducts selection in dataset-level.

        :param text_key: the key name of field that stores sample texts
            to be processed
        :param image_key: the key name of field that stores sample image list
            to be processed
        :param audio_key: the key name of field that stores sample audio list
            to be processed
        :param video_key: the key name of field that stores sample video list
            to be processed
        """
        super(Selector, self).__init__(*args, **kwargs)

    def process(self, dataset):
        """
        Dataset --> dataset.

        :param dataset: input dataset
        :return: selected dataset.
        """
        raise NotImplementedError

    def run(self, dataset, *, exporter=None, tracer=None):
        insert_pipline_job_run_task_log_info(self.job_uid, f"starting select job", operator_name=self._name,
                                             operator_index=self.pipline_index)
        set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.Processing, self._name, self.pipline_index)
        try:
            new_dataset = self.process(dataset)
            if tracer:
                tracer.trace_filter(self._name, dataset, new_dataset,job_uid=self.job_uid,pipeline_index=self.pipline_index)
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.SUCCESS, self._name, self.pipline_index)
            return new_dataset
        except Exception as e:
            # logger.error(f"An error occurred during data mapping: {e}")
            set_pipline_job_operator_status(self.job_uid, OperatorStatusEnum.ERROR, self._name, self.pipline_index)
            insert_pipline_job_run_task_log_error(self.job_uid,
                                                  f"An error occurred during data select: {e}",
                                                  operator_name=self._name, operator_index=self.pipline_index)
            raise
        finally:
            insert_pipline_job_run_task_log_info(self.job_uid, "ending select job", operator_name=self._name,
                                                 operator_index=self.pipline_index)


from dataclasses import dataclass
from enum import Enum

class DataType(Enum):
    INTEGER = int
    FLOAT = float
    STRING = str
    BOOLEAN = bool
    LIST = list
    PositiveFloat = 1
    ClosedUnitInterval = 2
    from_2_to_20 = 3
    SEARCH_SELECT = "search-select"
    SELECT_MODEL = "select-model"

@dataclass
class Sample:
    before: str
    after: str

@dataclass
class Param:
    name: str
    type: DataType
    options: dict
    default: any

