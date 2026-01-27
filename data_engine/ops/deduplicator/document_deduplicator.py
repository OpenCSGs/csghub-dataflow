# Some code here has been modified from:
# https://github.com/bigscience-workshop/data-preparation/blob/main/preprocessing/training/01a_catalogue_cleaning_and_filtering/clean_helpers/deduplication.py
# --------------------------------------------------------

import hashlib
import string
from collections import defaultdict
from typing import Dict, Set

import regex as re

from data_engine.utils.constant import HashKeys

from ..base_op import OPERATORS, Deduplicator, Sample, Param, DataType


@OPERATORS.register_module('document_deduplicator')
class DocumentDeduplicator(Deduplicator):
    """
    Deduplicator to deduplicate samples at document-level using exact matching.

    Using md5 hash to deduplicate samples.
    """

    def __init__(self,
                 lowercase: bool = False,
                 ignore_non_character: bool = False,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param lowercase: Whether to convert sample text to lower case
        :param ignore_non_character: Whether to ignore non-alphabet
            characters, including whitespaces, digits, and punctuations
        :param args: extra args
        :param kwargs: extra args.
        """
        super().__init__(*args, **kwargs)
        self.lowercase = lowercase
        self.remove_non_character_regex = re.compile(
            f'\s+|\d+|[{re.escape(string.punctuation)}]'  # noqa: W605
        ) if ignore_non_character else None
        
        # Enable detailed logging for this deduplicator
        self.enable_detailed_logging = True

    def compute_hash(self, sample):
        """
        Compute md5 hash values for the sample.

        :param sample: input sample
        :return: sample with md5 hash value.
        """
        # check if it's computed already
        if HashKeys.hash in sample:
            return sample

        text = sample[self.text_key]
        if self.lowercase:
            text = text.lower()
        if self.remove_non_character_regex:
            text = self.remove_non_character_regex.sub('', text)

        def _get_hash(txt):
            return hashlib.md5(txt.strip().encode('utf-8')).hexdigest()

        sample[HashKeys.hash] = _get_hash(text)
        return sample

    def process(self, dataset, show_num=0):
        """
        For doc-level, dataset --> dataset.

        :param dataset: input dataset
        :param show_num: number of traced samples used when tracer is
            open.
        :return: deduplicated dataset and the sampled duplicate pairs.
        """
        # Store original dataset size for logging
        original_size = len(dataset)
        
        # no need to deduplicate because too few samples
        if len(dataset) <= 1:
            if getattr(self, 'enable_detailed_logging', False):
                self._log_dedup_summary(original_size, original_size, 0, {})
            return dataset, {}

        dup_hashes = None
        hash2ids: Dict[int, Set[int]] = defaultdict(set)
        
        # Build hash to sample IDs mapping
        for sid, hash_val in enumerate(dataset[HashKeys.hash]):
            hash2ids[hash_val].add(sid)
        
        if show_num > 0:
            # sample duplicate pairs
            dup_samples = sorted(list(hash2ids.items()),
                                 key=lambda x: len(x[1]),
                                 reverse=True)
            dup_hashes = set([
                item[0] for item in dup_samples if len(item[1]) > 1
            ][:show_num])

        def _filter_dup_helper(sample, hashes):
            hash = sample[HashKeys.hash]
            if show_num > 0 and hash in dup_hashes \
                    and len(dup_pairs[hash]) < 2:
                # tracer is open and not enough duplicate sample pairs
                dup_pairs[hash].append(sample)
            if hash in hashes:
                return False
            else:
                hashes.add(hash)
                return True

        hashes = set()
        dup_pairs = {hash_v: [] for hash_v in dup_hashes} if dup_hashes else {}
        dataset = dataset.filter(
            _filter_dup_helper,
            fn_kwargs=dict(hashes=hashes),
            load_from_cache_file=False if show_num > 0 else True)  # num_proc=1
        
        # Generate detailed logging if enabled
        if getattr(self, 'enable_detailed_logging', False):
            deduplicated_size = len(dataset)
            self._log_dedup_summary(original_size, deduplicated_size, 
                                   original_size - deduplicated_size, hash2ids)
        
        return dataset, dup_pairs

    @classmethod
    @property
    def description(cls):
        return """
    Deduplicator to deduplicate samples at document-level using exact matching.

    Using md5 hash to deduplicate samples.
    """

    @classmethod
    @property
    def sample(cls):
        return Sample("{"
            "    'text':"
            "    'This paper proposed a novel method on LLM pretraining.'"
            "},"
            "{"
            "    'text':"
            "    'This paper proposed a novel method on LLM pretraining.'"
            "}", 
            "{"
            "    'text':"
            "    'This paper proposed a novel method on LLM pretraining.'"
            "},")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("lowercase", DataType.BOOLEAN, None, False),
            Param("ignore_non_character", DataType.BOOLEAN, None, False)
        ]
    
    def _log_dedup_summary(self, total, kept, removed, hash2ids):
        """
        Generate and log summary statistics for deduplication.
        
        :param total: Total number of documents before deduplication
        :param kept: Number of unique documents kept
        :param removed: Number of duplicate documents removed
        :param hash2ids: Mapping from hash values to document IDs
        """
        try:
            from loguru import logger
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            
            # Calculate statistics
            unique_hashes = len(hash2ids)
            duplicate_groups = sum(1 for ids in hash2ids.values() if len(ids) > 1)
            
            # Find largest duplicate group
            max_dup_count = max((len(ids) for ids in hash2ids.values()), default=0)
            
            # Output logs line by line for better display in UI
            self._log_line("="*60)
            self._log_line(f"[{self._name}] Deduplication Summary Statistics")
            self._log_line("="*60)
            self._log_line(f"Total documents: {total}")
            self._log_line(f"Unique documents kept: {kept} ({kept/total*100:.2f}%)")
            self._log_line(f"Duplicate documents removed: {removed} ({removed/total*100:.2f}%)")
            self._log_line("")
            self._log_line(f"Unique hash values: {unique_hashes}")
            self._log_line(f"Duplicate groups: {duplicate_groups}")
            self._log_line(f"Largest duplicate group: {max_dup_count} documents")
            
            # Add deduplicator-specific parameters
            self._log_line("")
            self._log_line("Deduplicator parameters:")
            self._log_line(f"  - Lowercase: {self.lowercase}")
            self._log_line(f"  - Ignore non-character: {self.remove_non_character_regex is not None}")
            self._log_line(f"  - Hash algorithm: MD5")
            
            self._log_line("="*60)
            
        except Exception as e:
            import traceback
            error_msg = f"Failed to generate deduplication logging: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            if hasattr(self, 'job_uid') and self.job_uid:
                from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_error
                insert_pipline_job_run_task_log_error(
                    self.job_uid,
                    error_msg,
                    operator_name=self._name,
                    operator_index=self.pipline_index
                )
    
    def _log_line(self, message):
        """Log a single line to both logger and MongoDB."""
        from loguru import logger
        logger.info(message)
        # Only write to MongoDB if job_uid exists
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.mongo_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(
                self.job_uid,
                message,
                operator_name=self._name,
                operator_index=self.pipline_index
            )