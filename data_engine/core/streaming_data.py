"""
Streaming Dataset Wrapper for Low Memory Processing

This module provides a wrapper around HuggingFace's IterableDataset
to enable streaming mode processing with minimal memory footprint.
"""

import traceback
from loguru import logger
from datasets import IterableDataset
from tqdm import tqdm


class StreamingDataset:
    """
    Wrapper class for IterableDataset to provide a similar interface
    to NestedDataset while operating in streaming mode.
    
    Key differences from NestedDataset:
    - No caching or fingerprint management
    - No multi-process parallelism (num_proc is ignored)
    - No random access (len(), select() not supported)
    - Significantly lower memory usage
    - Optional batch processing for efficiency
    - Optional tqdm progress bar support with total sample count
    

    """
    
    def __init__(self, iterable_dataset, batch_size=1, total_samples=None):
        """
        Initialize StreamingDataset
        
        Args:
            iterable_dataset: HuggingFace IterableDataset instance
            batch_size: Number of samples to process in each batch (default: 1)
                       Larger batch_size can improve efficiency but uses more memory
            total_samples: Total number of samples in dataset (optional)
                          If provided, enables progress bar with percentage and ETA
        """
        if not isinstance(iterable_dataset, IterableDataset):
            raise TypeError(
                f"Expected IterableDataset, got {type(iterable_dataset)}. "
                f"Make sure to load dataset with streaming=True"
            )
        
        self.dataset = iterable_dataset
        self._supports_streaming = True
        self.batch_size = batch_size
        self.total_samples = total_samples
        
        if batch_size > 1:
            logger.info(f'StreamingDataset initialized with batch_size={batch_size} '
                       f'for improved processing efficiency')
        
        if total_samples is not None:
            logger.info(f'StreamingDataset initialized with total_samples={total_samples:,} '
                       f'(progress bar will be displayed)')
    
    def map(self, function=None, **kwargs):
        """
        Apply a function to each sample (or batch) in the dataset.
        
        Args:
            function: Function to apply to each sample or batch
            **kwargs: Additional arguments
                - batched: If True, function receives a batch dict with lists of values
                - batch_size: Override instance batch_size for this operation
                - num_proc: Ignored (streaming is single-process)
                - with_rank: Ignored (no GPU parallelism in streaming)
                - desc: Description for progress display
                - disable_progress_bar: If True, disable progress bar even if total_samples is set
        
        Returns:
            StreamingDataset: New streaming dataset with function applied
        """
        # Extract parameters
        desc = kwargs.get('desc', 'Processing')
        batched = kwargs.get('batched', False)
        operation_batch_size = kwargs.get('batch_size', self.batch_size)
        disable_progress_bar = kwargs.get('disable_progress_bar', False)
        
        # Warn about ignored parameters
        ignored_params = ['num_proc', 'with_rank', 'new_fingerprint']
        for param in ignored_params:
            if param in kwargs and kwargs[param] is not None:
                logger.debug(f"Parameter '{param}' is ignored in streaming mode")
        
        if function is None:
            function = lambda x: x
        
        # Wrap function with progress bar if total_samples is available
        if self.total_samples is not None and not disable_progress_bar:
            wrapped_function = self._wrap_with_progress_bar(
                function, 
                desc=desc, 
                total=self.total_samples,
                batched=batched,
                batch_size=operation_batch_size
            )
        else:
            wrapped_function = function
        
        # Apply function using IterableDataset's map
        if batched:
            # Explicitly requested batched processing
            mapped_ds = self.dataset.map(
                wrapped_function,
                batched=True,
                batch_size=operation_batch_size
            )
            logger.debug(f'{desc}: Applied batched function with batch_size={operation_batch_size} in streaming mode')
        else:
            # Single sample processing
            mapped_ds = self.dataset.map(wrapped_function)
            logger.debug(f'{desc}: Applied function in streaming mode')
        
        # Preserve total_samples for chained operations
        return StreamingDataset(mapped_ds, batch_size=self.batch_size, total_samples=self.total_samples)
    
    def filter(self, function=None, **kwargs):
        """
        Filter samples based on a predicate function.
        
        Args:
            function: Predicate function that returns True to keep sample
                     - If batched=False: function(sample: Dict) -> bool
                     - If batched=True: function(batch: Dict[str, List]) -> List[bool]
            **kwargs: Additional arguments
                - batched: If True, function receives batches and returns List[bool] (default: False)
                - batch_size: Batch size for filtering (uses instance default if not specified)
                - desc: Description for progress display
                - disable_progress_bar: If True, disable progress bar even if total_samples is set
                - num_proc: Ignored (streaming is single-process)
        
        Returns:
            StreamingDataset: Filtered streaming dataset


        """
        desc = kwargs.get('desc', 'Filtering')
        batched = kwargs.get('batched', False)
        operation_batch_size = kwargs.get('batch_size', self.batch_size)
        disable_progress_bar = kwargs.get('disable_progress_bar', False)
        
        # Warn about ignored parameters
        if 'num_proc' in kwargs and kwargs['num_proc'] is not None:
            logger.debug("Parameter 'num_proc' is ignored in streaming mode")
        
        # Default function
        if function is None:
            if batched:
                # For batched mode, return list of True with same length as batch
                function = lambda batch: [True] * len(batch[next(iter(batch))])
            else:
                # For single sample mode, return True
                function = lambda x: True
        
        # Wrap function with progress bar if total_samples is available
        if self.total_samples is not None and not disable_progress_bar:
            wrapped_function = self._wrap_with_progress_bar(
                function, 
                desc=desc, 
                total=self.total_samples,
                batched=batched,
                batch_size=operation_batch_size,
                is_filter=True
            )
        else:
            wrapped_function = function
        
        # Apply filter using IterableDataset's filter
        # HuggingFace IterableDataset.filter DOES support batched parameter
        if batched:
            filtered_ds = self.dataset.filter(
                wrapped_function,
                batched=True,
                batch_size=operation_batch_size
            )
            logger.debug(f'{desc}: Applied batched filter with batch_size={operation_batch_size} in streaming mode')
        else:
            filtered_ds = self.dataset.filter(wrapped_function)
            logger.debug(f'{desc}: Applied filter in streaming mode')
        
        # Note: After filtering, total_samples is no longer accurate, set to None
        return StreamingDataset(filtered_ds, batch_size=self.batch_size, total_samples=None)

    def _wrap_with_progress_bar(self, function, desc, total, batched=False, batch_size=1, is_filter=False):
        """
        Wrap a function with tqdm progress bar.
        
        Args:
            function: Function to wrap
            desc: Description for progress bar
            total: Total number of samples
            batched: Whether function is batched
            batch_size: Batch size for batched processing
            is_filter: Whether this is a filter operation
        
        Returns:
            Wrapped function with progress bar
        """
        # Create a closure to maintain progress bar state
        pbar = {'bar': None, 'count': 0}
        
        def wrapped_function(sample):
            # Initialize progress bar on first call
            if pbar['bar'] is None:
                pbar['bar'] = tqdm(
                    total=total,
                    desc=desc,
                    unit='samples',
                    dynamic_ncols=True,
                    colour='green'
                )
            
            # Call original function
            result = function(sample)
            
            # Update progress bar
            if batched:
                # For batched processing, get the batch size from the sample
                if isinstance(sample, dict):
                    # Get the first key to determine batch size
                    first_key = next(iter(sample.keys()))
                    current_batch_size = len(sample[first_key])
                else:
                    current_batch_size = batch_size
                pbar['bar'].update(current_batch_size)
                pbar['count'] += current_batch_size
            else:
                # For single sample processing
                pbar['bar'].update(1)
                pbar['count'] += 1
            
            # Close progress bar when done
            if pbar['count'] >= total:
                pbar['bar'].close()
            
            return result
        
        return wrapped_function

    
    def process(self, operators, *, exporter=None, checkpointer=None, tracer=None):
        """
        Process dataset through a list of operators.
        
        Args:
            operators: List of operator instances to apply
            exporter: Exporter for saving results (optional)
            checkpointer: Ignored in streaming mode (no checkpoints)
            tracer: Ignored in streaming mode (no tracing)
        
        Returns:
            StreamingDataset: Processed dataset
        
        Raises:
            ValueError: If any operator doesn't support streaming mode
        """
        if operators is None:
            return self
        
        if not isinstance(operators, list):
            operators = [operators]
        
        # Warn about unsupported features
        if checkpointer is not None:
            logger.warning(
                "Checkpointing is not supported in streaming mode and will be ignored"
            )
        if tracer is not None:
            logger.warning(
                "Tracing is not supported in streaming mode and will be ignored"
            )
        
        dataset = self
        processed_count = 0
        
        for op in operators:
            # Check if operator supports streaming
            if not getattr(op, '_supports_streaming', False):
                raise ValueError(
                    f"Operator [{op._name}] does not support streaming mode. "
                    f"Please either:\n"
                    f"  1. Remove this operator from the pipeline, or\n"
                    f"  2. Use normal mode (set use_streaming=False)"
                )
            
            logger.info(f'Processing with operator [{op._name}] in streaming mode...')
            
            try:
                # Run operator in streaming mode
                dataset = op.run(dataset, exporter=exporter, tracer=None)
                processed_count += 1
                logger.info(
                    f'OP [{op._name}] completed in streaming mode '
                    f'({processed_count}/{len(operators)})'
                )
            except Exception as e:
                logger.error(
                    f'An error occurred during Op [{op._name}] in streaming mode: {e}'
                )
                raise
        
        return dataset

    
    def __iter__(self):
        """
        Iterate over samples in the dataset.
        
        Returns:
            Iterator over dataset samples
        """
        return iter(self.dataset)
    
    def __repr__(self):
        return f"StreamingDataset({self.dataset})"
    
    def take(self, n):
        """
        Take first n samples from the dataset.
        
        Args:
            n: Number of samples to take
        
        Returns:
            StreamingDataset: Dataset with first n samples
        """
        # Update total_samples to n if it was set
        new_total = min(n, self.total_samples) if self.total_samples is not None else n
        return StreamingDataset(self.dataset.take(n), batch_size=self.batch_size, total_samples=new_total)
    
    def skip(self, n):
        """
        Skip first n samples from the dataset.
        
        Args:
            n: Number of samples to skip
        
        Returns:
            StreamingDataset: Dataset with first n samples skipped
        """
        # Update total_samples if it was set
        new_total = max(0, self.total_samples - n) if self.total_samples is not None else None
        return StreamingDataset(self.dataset.skip(n), batch_size=self.batch_size, total_samples=new_total)
    
    def shuffle(self, seed=None, buffer_size=1000):
        """
        Shuffle the dataset using a buffer.
        
        Note: This is not a true shuffle but uses a buffer-based approach.
        For true random shuffle, use normal mode instead.
        
        Args:
            seed: Random seed
            buffer_size: Size of shuffle buffer
        
        Returns:
            StreamingDataset: Shuffled dataset
        """
        return StreamingDataset(
            self.dataset.shuffle(seed=seed, buffer_size=buffer_size),
            batch_size=self.batch_size,
            total_samples=self.total_samples
        )


def is_streaming_dataset(dataset):
    """
    Check if a dataset is in streaming mode.
    
    Args:
        dataset: Dataset to check
    
    Returns:
        bool: True if dataset is StreamingDataset, False otherwise
    """
    return isinstance(dataset, StreamingDataset)


def catch_streaming_exception(method):
    """
    Exception handler for streaming mode operations.
    Converts error samples to dict with empty lists, which will be filtered out.
    
    This matches catch_map_single_exception in base_op.py for consistency:
    - Returns {key: []} for all keys to maintain schema
    - Logs error details for debugging
    - Empty list values will be filtered out by filter_empty_samples
    """
    from functools import wraps
    from data_engine.utils.constant import Fields
    
    @wraps(method)
    def wrapper(sample, *args, **kwargs):
        try:
            return method(sample, *args, **kwargs)
        except Exception as e:
            logger.error(
                f'An error occurred in streaming operation when processing '
                f'sample, {type(e)}: {e}'
            )
            traceback.print_exc()
            # Return dict with empty lists (matches normal mode behavior)
            # This maintains the schema structure while marking sample as invalid
            ret = {key: [] for key in sample.keys()} if sample else {}
            ret[Fields.stats] = []
            ret[Fields.source_file] = []
            return ret
    return wrapper


def filter_empty_samples(dataset):
    """
    Filter out samples with empty list values that resulted from exceptions.
    Should be applied after map operations that might return {key: []} on error.
    
    Args:
        dataset: StreamingDataset that might contain error samples
    
    Returns:
        StreamingDataset with error samples removed
    """
    from data_engine.utils.constant import Fields
    
    def is_not_empty(sample):
        # Filter out samples where all values are empty lists (error samples)
        # Check if sample is empty or if it's an error sample from catch_streaming_exception
        if not sample:
            return False
        
        # Check if this is an error sample: all values are empty lists
        # Skip checking Fields.stats and Fields.source_file as they're added by exception handler
        data_keys = [k for k in sample.keys() if k not in [Fields.stats, Fields.source_file]]
        if not data_keys:
            # Only has stats/source_file, likely an error sample
            return False
        
        # Check if all data values are empty lists
        all_empty = all(
            isinstance(sample[key], list) and len(sample[key]) == 0
            for key in data_keys
        )
        return not all_empty
    
    # Apply filter using dataset's filter method (preserves StreamingDataset wrapper)
    return dataset.filter(is_not_empty, desc='filter_empty_samples')
