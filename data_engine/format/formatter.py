import os
from glob import escape as glob_escape
from typing import List, Tuple, Union

from datasets import Dataset, DatasetDict, concatenate_datasets, load_dataset
from loguru import logger

from data_engine.utils.constant import Fields
from data_engine.utils.file_utils import (find_files_with_suffix,
                                          is_absolute_path)
from data_engine.utils.registry import Registry

FORMATTERS = Registry('Formatters')


def escape_glob_chars(file_path: str) -> str:
    """
    Escape glob special characters ([ ] * ?) in file paths,
    to prevent fsspec from interpreting them as glob patterns.
    """
    return glob_escape(file_path)


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
        
        # Escape glob special characters in file paths to avoid fsspec parsing errors
        # e.g., [ ] characters in filenames would be misinterpreted as glob patterns
        escaped_data_files = {
            key: [escape_glob_chars(f) for f in files]
            for key, files in self.data_files.items()
        }
        
        # Try to load dataset normally first
        try:
            datasets = load_dataset(
                self.type,
                data_files={
                    key.strip('.'): escaped_data_files[key]
                    for key in escaped_data_files
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
                'schema' in error_msg or
                'parse' in error_msg or
                'cast' in error_msg
            )
            
            if not is_type_error:
                # Not a type conversion error, raise directly
                raise
            
            # If loading fails due to type inference issues, retry with explicit features
            # This handles two scenarios:
            # 1. Empty strings cannot be parsed as non-string types (e.g., timestamp)
            # 2. Type conflicts between files (e.g., null vs string, Sequence[null] vs Sequence[string])
            original_error = e
            logger.warning(f"Dataset loading failed with type conversion error: {e}")
            
            try:
                # Collect all file paths
                all_file_paths = []
                for suffix, file_list in self.data_files.items():
                    for file_path in file_list:
                        all_file_paths.append(file_path)
                
                # Step 1: Infer unified schema from all files (read first line of each)
                unified_schema = self._infer_unified_schema(all_file_paths)
                
                # Step 2: Build Features object from unified schema
                features = self._build_features_from_schema(unified_schema)
                
                # Step 3: Reload with explicit features - this prevents type inference conflicts
                # Note: We don't set nullable here because Value doesn't support _nullable parameter
                # Instead, we'll handle missing struct fields by preprocessing the data files
                datasets = self._load_dataset_with_struct_filling(
                    escaped_data_files, features, unified_schema, num_proc
                )
            except Exception as retry_error:
                logger.error(f"Failed to load dataset even with explicit features. Original error: {original_error}")
                logger.error(f"Retry error: {retry_error}")
                
                # Parse and log detailed error information
                self._log_detailed_conversion_error(retry_error, unified_schema)
                
                raise original_error from retry_error
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


    def _get_file_type_from_path(self, file_path: str) -> str:
        """
        Determine file type from file extension.
        
        :param file_path: path to the file
        :return: file type ('json', 'csv', 'parquet', or 'unknown')
        """
        file_path_lower = file_path.lower()
        if file_path_lower.endswith('.jsonl') or file_path_lower.endswith('.jsonl.zst') or file_path_lower.endswith('.json'):
            return 'json'
        elif file_path_lower.endswith('.csv'):
            return 'csv'
        elif file_path_lower.endswith('.parquet'):
            return 'parquet'
        else:
            # Fallback to self.type if available, otherwise 'json' as default
            return getattr(self, 'type', 'json')
    
    def _read_sample_from_file(self, file_path: str, file_type: str, sample_lines: int = 1) -> list:
        """
        Read sample data from file based on file type.
        
        :param file_path: path to the file
        :param file_type: type of file ('json', 'csv', 'parquet')
        :param sample_lines: number of lines/records to sample (default: 1)
        :return: list of sample records (dicts)
        """
        samples = []
        
        try:
            if file_type == 'json':
                import json
                with open(file_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= sample_lines:
                            break
                        try:
                            data = json.loads(line.strip())
                            if isinstance(data, dict):
                                samples.append(data)
                        except json.JSONDecodeError:
                            continue
            
            elif file_type == 'csv':
                import csv
                with open(file_path, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= sample_lines:
                            break
                        # Convert all values to appropriate types (CSV reads as strings)
                        # We'll let type inference handle the conversion
                        samples.append(row)
            
            elif file_type == 'parquet':
                try:
                    import pyarrow.parquet as pq
                    table = pq.read_table(file_path, columns=None)
                    # Convert to list of dicts
                    for i in range(min(sample_lines, len(table))):
                        row_dict = {}
                        for col_name in table.column_names:
                            value = table[col_name][i].as_py()
                            row_dict[col_name] = value
                        samples.append(row_dict)
                except ImportError:
                    # Fallback to pandas if pyarrow not available
                    import pandas as pd
                    df = pd.read_parquet(file_path, nrows=sample_lines)
                    samples = df.to_dict('records')
            
            else:
                logger.warning(f"Unknown file type '{file_type}' for file: {file_path}, skipping")
        
        except Exception as e:
            logger.warning(f"Failed to read sample from file {file_path} (type: {file_type}): {e}")
        
        return samples
    
    def _infer_unified_schema(self, file_list: list, sample_lines: int = 1) -> dict:
        """
        Read first N lines of each file to infer unified schema.
        Uses type priority to select the best type for each field.
        Supports JSON/JSONL, CSV, and Parquet file formats.
        
        :param file_list: list of file paths
        :param sample_lines: number of lines to sample from each file (default: 1)
        :return: unified schema dict {field_name: best_type or struct_info}
        """
        from collections import defaultdict
        
        # Type priority (higher number = higher priority, more general types preferred)
        TYPE_PRIORITY = {
            'null': 0,
            'bool': 1,
            'int64': 2,
            'float64': 3,
            'timestamp': 4,
            'string': 5,  # string is highest, can accommodate all
            # List types
            'list[null]': 10,
            'list[bool]': 11,
            'list[int64]': 12,
            'list[float64]': 13,
            'list[string]': 15,
        }
        
        # Record types for each field across all files
        # Use list instead of set because struct types (dicts) are not hashable
        field_types = defaultdict(list)
        # Record which file has which type for each field (for error reporting)
        # Structure: {field_name: [(file_path, inferred_type), ...]}
        field_types_by_file = defaultdict(list)
        
        for file_path in file_list:
            # Determine file type from extension
            file_type = self._get_file_type_from_path(file_path)
            
            # Read sample data from file
            samples = self._read_sample_from_file(file_path, file_type, sample_lines)
            
            # Infer types from samples
            for data in samples:
                if not isinstance(data, dict):
                    continue
                for field, value in data.items():
                    inferred_type = self._infer_type_from_value(value)
                    field_types[field].append(inferred_type)
                    field_types_by_file[field].append((file_path, inferred_type))
        
        # Select the best type for each field and detect conflicts
        unified_schema = {}
        conflicts_detected = []
        
        for field, types in field_types.items():
            # Separate simple types (strings) from complex types (dicts for struct)
            simple_types = [t for t in types if isinstance(t, str)]
            complex_types = [t for t in types if isinstance(t, dict)]
            
            if complex_types:
                # Check for struct type conflicts
                struct_conflicts = self._detect_struct_conflicts(field, complex_types, field_types_by_file[field])
                if struct_conflicts:
                    conflicts_detected.append(struct_conflicts)
                
                # Merge all struct types to include all fields from all files
                unified_schema[field] = self._merge_struct_types(complex_types)
            elif simple_types:
                # Check for simple type conflicts
                unique_simple = set(simple_types)
                if len(unique_simple) > 1:
                    # Multiple types found, log conflict
                    type_files_map = defaultdict(list)
                    for file_path, inferred_type in field_types_by_file[field]:
                        if isinstance(inferred_type, str):
                            type_files_map[inferred_type].append(file_path)
                    
                    conflicts_detected.append({
                        'field': field,
                        'type': 'simple',
                        'conflicts': {t: list(set(files)) for t, files in type_files_map.items()},
                        'selected': max(unique_simple, key=lambda t: TYPE_PRIORITY.get(t, -1))
                    })
                
                # Use unique simple types and select highest priority
                best_type = max(unique_simple, key=lambda t: TYPE_PRIORITY.get(t, -1))
                unified_schema[field] = best_type
            else:
                # Fallback to string
                unified_schema[field] = 'string'
        
        # Log all detected conflicts
        if conflicts_detected:
            logger.warning("Detected type conflicts across files:")
            for conflict in conflicts_detected:
                self._log_type_conflict(conflict)
        
        return unified_schema
    
    def _merge_struct_types(self, struct_types: list) -> dict:
        """
        Merge multiple struct type definitions into a unified struct that includes all fields.
        For fields with the same name but different types, use type priority to select the best type.
        
        :param struct_types: list of struct type dicts, each with format:
            {'type': 'struct', 'fields': {'field1': 'string', 'field2': 'int64', ...}}
        :return: merged struct type dict
        """
        from collections import defaultdict
        
        if not struct_types:
            return {'type': 'struct', 'fields': {}}
        
        # Type priority for selecting best type when same field has different types
        TYPE_PRIORITY = {
            'null': 0,
            'bool': 1,
            'int64': 2,
            'float64': 3,
            'timestamp': 4,
            'string': 5,  # string is highest, can accommodate all
            'list[null]': 10,
            'list[bool]': 11,
            'list[int64]': 12,
            'list[float64]': 13,
            'list[string]': 15,
        }
        
        # Collect all fields from all structs
        merged_fields = {}
        field_type_occurrences = defaultdict(list)  # Track all types for each field
        
        for struct_type in struct_types:
            if isinstance(struct_type, dict) and struct_type.get('type') == 'struct':
                fields = struct_type.get('fields', {})
                for field_name, field_type in fields.items():
                    field_type_occurrences[field_name].append(field_type)
        
        # For each field, select the best type (highest priority)
        for field_name, type_list in field_type_occurrences.items():
            # Handle simple types (strings)
            simple_types = [t for t in type_list if isinstance(t, str)]
            complex_types = [t for t in type_list if isinstance(t, dict)]
            
            if complex_types:
                # If there are complex types (nested structs), merge them recursively
                merged_fields[field_name] = self._merge_struct_types(complex_types)
            elif simple_types:
                # Select highest priority simple type
                unique_simple = set(simple_types)
                best_type = max(unique_simple, key=lambda t: TYPE_PRIORITY.get(t, -1))
                merged_fields[field_name] = best_type
            else:
                # Fallback to string
                merged_fields[field_name] = 'string'
        
        return {'type': 'struct', 'fields': merged_fields}
    
    def _detect_struct_conflicts(self, field_name: str, struct_types: list, field_types_by_file: list) -> dict:
        """
        Detect conflicts in struct types across files.
        
        :param field_name: name of the field
        :param struct_types: list of struct type dicts
        :param field_types_by_file: list of (file_path, inferred_type) tuples
        :return: conflict info dict or None if no conflict
        """
        # Group struct types by their field structure
        struct_groups = {}
        for struct_type in struct_types:
            # Create a hashable representation of struct fields
            struct_key = tuple(sorted(struct_type.get('fields', {}).items()))
            if struct_key not in struct_groups:
                struct_groups[struct_key] = {
                    'struct': struct_type,
                    'files': []
                }
        
        # Map files to struct groups
        for file_path, inferred_type in field_types_by_file:
            if isinstance(inferred_type, dict) and inferred_type.get('type') == 'struct':
                struct_key = tuple(sorted(inferred_type.get('fields', {}).items()))
                for key, group in struct_groups.items():
                    if key == struct_key:
                        group['files'].append(file_path)
                        break
        
        # Check if there are multiple different struct structures
        if len(struct_groups) > 1:
            return {
                'field': field_name,
                'type': 'struct',
                'conflicts': {i: {
                    'struct': group['struct'],
                    'files': list(set(group['files']))
                } for i, group in enumerate(struct_groups.values(), 1)}
            }
        return None
    
    def _format_file_path(self, file_path: str, max_length: int = 100) -> str:
        """
        Format file path for logging, truncating if too long.
        
        :param file_path: full file path
        :param max_length: maximum length before truncating
        :return: formatted file path
        """
        if len(file_path) <= max_length:
            return file_path
        # Show last part of path if too long
        return "..." + file_path[-(max_length-3):]
    
    def _log_type_conflict(self, conflict: dict):
        """
        Log type conflict information in a user-friendly format.
        
        :param conflict: conflict info dict
        """
        field_name = conflict['field']
        conflict_type = conflict['type']
        
        if conflict_type == 'struct':
            logger.warning(f"  Field '{field_name}' (struct type):")
            for struct_id, struct_info in conflict['conflicts'].items():
                struct_fields = struct_info['struct'].get('fields', {})
                files = struct_info['files']
                fields_str = ', '.join([f"'{k}': {v}" for k, v in struct_fields.items()])
                logger.warning(f"    Structure {struct_id} found in {len(files)} file(s):")
                logger.warning(f"      Fields: {{{fields_str}}}")
                # Log file paths (limit to first 5 to avoid too long logs)
                if len(files) <= 5:
                    for file_path in files:
                        logger.warning(f"        - {self._format_file_path(file_path)}")
                else:
                    for file_path in files[:5]:
                        logger.warning(f"        - {self._format_file_path(file_path)}")
                    logger.warning(f"        ... and {len(files) - 5} more file(s)")
            logger.warning(f"    Selected unified type: Merged structure (includes all fields from all files)")
            logger.warning(f"    ✅  All struct fields have been merged. Missing fields will be automatically filled with null.")
        
        elif conflict_type == 'simple':
            logger.warning(f"  Field '{field_name}':")
            for type_name, files in conflict['conflicts'].items():
                logger.warning(f"    - Type '{type_name}' found in {len(files)} file(s)")
                # Log file paths (limit to first 5)
                if len(files) <= 5:
                    for file_path in files:
                        logger.warning(f"        {self._format_file_path(file_path)}")
                else:
                    for file_path in files[:5]:
                        logger.warning(f"        {self._format_file_path(file_path)}")
                    logger.warning(f"        ... and {len(files) - 5} more file(s)")
            logger.warning(f"    Selected unified type: '{conflict['selected']}' (highest priority)")
    
    def _log_detailed_conversion_error(self, error: Exception, unified_schema: dict):
        """
        Parse and log detailed information about type conversion errors.
        
        :param error: the exception that occurred
        :param unified_schema: the unified schema that was used
        """
        error_msg = str(error)
        
        # Try to extract field name and type information from error message
        # Common patterns:
        # - "Couldn't cast array of type\n{actual_type}\nto\n{expected_type}"
        # - "Couldn't cast array of type struct<...> to {...}"
        
        if "Couldn't cast array of type" in error_msg:
            logger.error("=" * 80)
            logger.error("Type Conversion Error Details:")
            logger.error("=" * 80)
            
            # Try to extract type information
            lines = error_msg.split('\n')
            actual_type = None
            expected_type = None
            
            for i, line in enumerate(lines):
                if "Couldn't cast array of type" in line and i + 1 < len(lines):
                    actual_type = lines[i + 1].strip() if i + 1 < len(lines) else None
                if "to\n" in line or (i > 0 and "to" in lines[i-1] and actual_type):
                    # Next line should be expected type
                    if i < len(lines):
                        expected_type = lines[i].strip()
                        break
            
            if actual_type:
                logger.error(f"  Actual type in data: {actual_type}")
            if expected_type:
                logger.error(f"  Expected type: {expected_type}")
            
            # Try to identify which field this might be related to
            # Look for struct field names in the error message
            if "struct<" in error_msg or "struct" in error_msg.lower():
                # Extract struct field names from error message
                import re
                struct_match = re.search(r'struct<([^>]+)>', error_msg)
                if struct_match:
                    actual_fields = struct_match.group(1)
                    logger.error(f"  Actual struct fields: {actual_fields}")
                
                # Try to match with unified schema
                for field_name, schema_type in unified_schema.items():
                    if isinstance(schema_type, dict) and schema_type.get('type') == 'struct':
                        expected_fields = schema_type.get('fields', {})
                        if expected_fields:
                            expected_fields_str = ', '.join([f"{k}: {v}" for k, v in expected_fields.items()])
                            logger.error(f"  Expected struct fields for '{field_name}': {{{expected_fields_str}}}")
                            
                            # Check if this might be the problematic field
                            if any(field in actual_fields for field in expected_fields.keys()):
                                logger.error(f"  ⚠️  This error is likely related to field: '{field_name}'")
                                logger.error(f"  ⚠️  The struct structure in your data files differs from the inferred schema.")
                                logger.error(f"  ⚠️  Please check the files mentioned in the type conflict warnings above.")
                                break
            
            logger.error("=" * 80)
            logger.error("Recommendation:")
            logger.error("  - Review the type conflict warnings logged above")
            logger.error("  - Ensure all files have consistent struct field structures")
            logger.error("  - Missing fields will be filled with null, but extra fields cause errors")
            logger.error("=" * 80)
    
    def _infer_type_from_value(self, value):
        """
        Infer PyArrow type from Python value.
        
        :param value: Python value
        :return: type name string, or dict for struct types
        """
        if value is None:
            return 'null'
        elif isinstance(value, bool):
            return 'bool'
        elif isinstance(value, int):
            return 'int64'
        elif isinstance(value, float):
            return 'float64'
        elif isinstance(value, str):
            return 'string'
        elif isinstance(value, list):
            if not value:
                return 'list[null]'
            # Infer inner type from list elements
            inner_types = [self._infer_type_from_value(v) for v in value]
            # For simple types, select highest priority
            simple_types = [t for t in inner_types if isinstance(t, str)]
            if simple_types:
                TYPE_PRIORITY = {
                    'null': 0, 'bool': 1, 'int64': 2, 'float64': 3, 'string': 5
                }
                best_inner = max(simple_types, key=lambda t: TYPE_PRIORITY.get(t, -1))
                return f'list[{best_inner}]'
            # If all elements are structs, return list of struct
            struct_types = [t for t in inner_types if isinstance(t, dict)]
            if struct_types:
                return {'type': 'list[struct]', 'element': struct_types[0]}
            return 'list[string]'  # Default fallback
        elif isinstance(value, dict):
            # For struct, return the internal structure
            struct_fields = {}
            for k, v in value.items():
                struct_fields[k] = self._infer_type_from_value(v)
            return {'type': 'struct', 'fields': struct_fields}
        else:
            return 'string'  # Default fallback
    
    def _cast_to_unified_schema(self, dataset: Dataset, unified_schema: dict) -> Dataset:
        """
        Cast dataset fields to unified schema types.
        This ensures type consistency when merging datasets from multiple files.
        
        :param dataset: input dataset
        :param unified_schema: unified schema dict {field_name: type_name}
        :return: dataset with unified types
        """
        from datasets import Features, Value, Sequence
        
        # Map type names to datasets Features
        TYPE_MAP = {
            'null': Value('null'),
            'bool': Value('bool'),
            'int64': Value('int64'),
            'float64': Value('float64'),
            'string': Value('string'),
            'timestamp': Value('string'),  # Convert timestamp to string for safety
            'list[null]': Sequence(Value('string')),  # Convert null list to string list
            'list[bool]': Sequence(Value('bool')),
            'list[int64]': Sequence(Value('int64')),
            'list[float64]': Sequence(Value('float64')),
            'list[string]': Sequence(Value('string')),
        }
        
        new_features = {}
        for name, feature in dataset.features.items():
            if name in unified_schema:
                target_type = unified_schema[name]
                
                # Handle struct/complex types - keep as-is
                if target_type in ('struct', 'list[struct]'):
                    new_features[name] = feature
                elif target_type in TYPE_MAP:
                    new_features[name] = TYPE_MAP[target_type]
                else:
                    # Unknown type, keep original
                    new_features[name] = feature
            else:
                # Field not in unified schema, keep original
                new_features[name] = feature
        
        try:
            return dataset.cast(Features(new_features))
        except Exception as e:
            logger.warning(f"Failed to cast to unified schema: {e}, returning original dataset")
            return dataset
    
    def _build_features_from_schema(self, unified_schema: dict):
        """
        Build a datasets.Features object from unified schema dict.
        
        :param unified_schema: dict mapping field names to type info (string or dict for struct)
        :return: Features object for use with load_dataset
        """
        from datasets import Features, Value, Sequence
        
        # Map type names to datasets Features
        TYPE_MAP = {
            'null': Value('string'),  # null -> string for safety
            'bool': Value('bool'),
            'int64': Value('int64'),
            'float64': Value('float64'),
            'string': Value('string'),
            'timestamp': Value('string'),  # timestamp -> string for safety
            'list[null]': Sequence(Value('string')),  # null list -> string list
            'list[bool]': Sequence(Value('bool')),
            'list[int64]': Sequence(Value('int64')),
            'list[float64]': Sequence(Value('float64')),
            'list[string]': Sequence(Value('string')),
        }
        
        def build_feature(type_info):
            """Recursively build feature from type info"""
            if isinstance(type_info, str):
                # Simple type
                if type_info in TYPE_MAP:
                    return TYPE_MAP[type_info]
                else:
                    logger.warning(f"Unknown type '{type_info}', defaulting to string")
                    return Value('string')
            elif isinstance(type_info, dict):
                # Complex type (struct or list[struct])
                type_name = type_info.get('type', '')
                if type_name == 'struct':
                    # Build struct feature
                    struct_fields = {}
                    for field_name, field_type in type_info.get('fields', {}).items():
                        struct_fields[field_name] = build_feature(field_type)
                    return struct_fields
                elif type_name == 'list[struct]':
                    # Build list of struct feature
                    element_type = type_info.get('element', {})
                    if isinstance(element_type, dict) and element_type.get('type') == 'struct':
                        struct_fields = {}
                        for field_name, field_type in element_type.get('fields', {}).items():
                            struct_fields[field_name] = build_feature(field_type)
                        return Sequence(struct_fields)
                    return Sequence(Value('string'))  # Fallback
                else:
                    logger.warning(f"Unknown complex type '{type_name}', defaulting to string")
                    return Value('string')
            else:
                return Value('string')  # Fallback
        
        features_dict = {}
        for field_name, type_info in unified_schema.items():
            features_dict[field_name] = build_feature(type_info)
        
        return Features(features_dict)
    
    def _load_dataset_with_struct_filling(self, escaped_data_files: dict, features, unified_schema: dict, num_proc: int = 1):
        """
        Load dataset and fill missing fields (both struct and non-struct).
        Uses streaming mode as fallback when normal loading fails due to schema mismatch.
        
        Handles the following scenarios:
        1. Struct field mismatch between files (e.g., different nested fields)
        2. Missing columns in some files (e.g., CSV/Parquet files with different columns)
        
        :param escaped_data_files: escaped file paths dict
        :param features: Features object
        :param unified_schema: unified schema dict
        :param num_proc: number of processes
        :return: loaded datasets
        """
        from datasets import DatasetDict, load_dataset
        
        # Find all struct fields that need filling (used by _load_with_streaming_and_filling)
        struct_fields_to_fill = {}
        for field_name, type_info in unified_schema.items():
            if isinstance(type_info, dict) and type_info.get('type') == 'struct':
                struct_fields_to_fill[field_name] = list(type_info.get('fields', {}).keys())
        
        # Try loading normally first (with features parameter)
        try:
            return load_dataset(
                self.type,
                data_files={
                    key.strip('.'): escaped_data_files[key]
                    for key in escaped_data_files
                },
                features=features,
                num_proc=num_proc,
                **self.kwargs
            )
        except Exception as load_error:
            # Check both the error message and its cause (nested exception)
            error_msg = str(load_error).lower()
            error_cause_msg = str(load_error.__cause__).lower() if load_error.__cause__ else ""
            
            # Check if it's a schema mismatch error that can be handled by streaming mode
            # This includes:
            # 1. Struct casting errors (struct field mismatch between files)
            # 2. Missing column errors for CSV (KeyError, field does not exist)
            # 3. Column name mismatch errors for Parquet (CastError, column names don't match)
            is_schema_mismatch_error = (
                # Struct casting errors (JSON)
                ('cast' in error_msg and 'struct' in error_msg) or
                ('cast' in error_cause_msg and 'struct' in error_cause_msg) or
                ('couldn\'t cast array' in error_cause_msg and 'struct' in error_cause_msg) or
                # Missing column errors (CSV)
                ('does not exist' in error_cause_msg and 'field' in error_cause_msg) or
                ('keyerror' in error_cause_msg) or
                ('does not exist in table schema' in error_cause_msg) or
                # Column name mismatch errors (Parquet)
                ('column names don\'t match' in error_cause_msg) or
                ('casterror' in error_cause_msg and 'column' in error_cause_msg)
            )
            
            if is_schema_mismatch_error:
                # If loading fails due to schema mismatch, use appropriate fallback method
                logger.warning("Loading with features failed due to schema mismatch (missing columns or struct field differences). "
                             "Trying fallback method to fill missing fields...")
                
                # For Parquet files, use PyArrow-based loading (streaming mode doesn't work for Parquet schema mismatch)
                if self.type == 'parquet':
                    logger.info("Using PyArrow-based loading for Parquet files...")
                    return self._load_parquet_with_filling(escaped_data_files, features, unified_schema)
                else:
                    # For JSON/CSV, use streaming mode
                    logger.info("Using streaming mode for JSON/CSV files...")
                    return self._load_with_streaming_and_filling(escaped_data_files, features, unified_schema, num_proc)
            else:
                raise
    
    def _load_parquet_with_filling(self, escaped_data_files: dict, features, unified_schema: dict):
        """
        Load Parquet files using PyArrow directly, fill missing fields, then create unified dataset.
        This method bypasses datasets library's schema enforcement for Parquet files.
        
        :param escaped_data_files: escaped file paths dict
        :param features: Features object
        :param unified_schema: unified schema dict
        :return: loaded datasets
        """
        import pyarrow.parquet as pq
        from datasets import Dataset, DatasetDict
        
        # Get all field names from unified_schema (for filling missing fields)
        all_schema_fields = set(unified_schema.keys())
        
        # Find all struct fields that need filling
        struct_fields_to_fill = {}
        for field_name, type_info in unified_schema.items():
            if isinstance(type_info, dict) and type_info.get('type') == 'struct':
                struct_fields_to_fill[field_name] = list(type_info.get('fields', {}).keys())
        
        def fill_missing_fields(record: dict) -> dict:
            """Fill missing fields in a single record"""
            # 1. Fill missing non-struct fields with None
            for field_name in all_schema_fields:
                if field_name not in record:
                    if field_name in struct_fields_to_fill:
                        # Struct field: initialize as dict with all required fields set to None
                        record[field_name] = {field: None for field in struct_fields_to_fill[field_name]}
                    else:
                        # Non-struct field: initialize as None
                        record[field_name] = None
            
            # 2. Handle struct fields that exist but need internal fields filled
            for struct_field_name, required_fields in struct_fields_to_fill.items():
                if struct_field_name in record:
                    struct_value = record[struct_field_name]
                    if struct_value is None:
                        record[struct_field_name] = {field: None for field in required_fields}
                    elif isinstance(struct_value, dict):
                        for field in required_fields:
                            if field not in struct_value:
                                struct_value[field] = None
                        record[struct_field_name] = struct_value
            
            return record
        
        # Collect all records from all Parquet files
        all_records = []
        
        for suffix, file_paths in escaped_data_files.items():
            for file_path in file_paths:
                # Unescape the glob characters to get actual file path
                # Note: escaped_data_files contains glob-escaped paths, we need original paths for PyArrow
                actual_path = file_path.replace('[', '[').replace(']', ']')  # glob_escape uses [[] and []] patterns
                # Actually, glob_escape escapes [ as [[] and ] as []], so we need to reverse that
                import re
                actual_path = re.sub(r'\[(\[)\]', r'\1', file_path)  # [[] -> [
                actual_path = re.sub(r'\[(\])\]', r'\1', actual_path)  # []] -> ]
                actual_path = re.sub(r'\[(\*)\]', r'\1', actual_path)  # [*] -> *
                actual_path = re.sub(r'\[(\?)\]', r'\1', actual_path)  # [?] -> ?
                
                try:
                    # Read Parquet file using PyArrow (no schema enforcement)
                    table = pq.read_table(actual_path)
                    
                    # Convert to list of dicts
                    # Use to_pydict() for efficiency, then restructure
                    columns_dict = table.to_pydict()
                    num_rows = table.num_rows
                    
                    for i in range(num_rows):
                        record = {col: columns_dict[col][i] for col in columns_dict}
                        # Fill missing fields
                        filled_record = fill_missing_fields(record)
                        all_records.append(filled_record)
                    
                    logger.debug(f"Loaded {num_rows} records from {actual_path}")
                    
                except Exception as e:
                    logger.error(f"Failed to read Parquet file {actual_path}: {e}")
                    raise
        
        logger.info(f"Total {len(all_records)} records loaded from Parquet files")
        
        # Create dataset from list with unified features
        dataset = Dataset.from_list(all_records, features=features)
        
        # Return as DatasetDict with 'parquet' split (consistent with normal loading)
        return DatasetDict({'parquet': dataset})
    
    def _load_with_streaming_and_filling(self, escaped_data_files: dict, features, unified_schema: dict, num_proc: int = 1):
        """
        Load dataset using streaming mode, fill missing struct fields, then convert.
        This is a fallback when normal loading fails due to struct field mismatch.
        
        :param escaped_data_files: escaped file paths dict
        :param features: Features object
        :param unified_schema: unified schema dict
        :param num_proc: number of processes
        :return: loaded datasets
        """
        from datasets import DatasetDict, load_dataset
        
        # Find all struct fields that need filling
        struct_fields_to_fill = {}
        for field_name, type_info in unified_schema.items():
            if isinstance(type_info, dict) and type_info.get('type') == 'struct':
                struct_fields_to_fill[field_name] = list(type_info.get('fields', {}).keys())
        
        # Get all field names from unified_schema (for filling missing non-struct fields)
        all_schema_fields = set(unified_schema.keys())
        
        def fill_missing_fields(sample):
            """Fill missing fields (both struct and non-struct) with null/default values"""
            # 1. Fill missing non-struct fields with None
            for field_name in all_schema_fields:
                if field_name not in sample:
                    if field_name in struct_fields_to_fill:
                        # Struct field: initialize as dict with all required fields set to None
                        sample[field_name] = {field: None for field in struct_fields_to_fill[field_name]}
                    else:
                        # Non-struct field: initialize as None
                        sample[field_name] = None
            
            # 2. Handle struct fields that exist but need internal fields filled
            for struct_field_name, required_fields in struct_fields_to_fill.items():
                if struct_field_name in sample:
                    struct_value = sample[struct_field_name]
                    if struct_value is None:
                        # If struct field is None, initialize it as a dict with all required fields set to None
                        sample[struct_field_name] = {field: None for field in required_fields}
                    elif isinstance(struct_value, dict):
                        # Fill missing fields with None
                        for field in required_fields:
                            if field not in struct_value:
                                struct_value[field] = None
                        sample[struct_field_name] = struct_value
                    else:
                        # If struct field is not None and not a dict (unexpected type), 
                        # initialize it as a dict with all required fields set to None
                        logger.warning(f"Field '{struct_field_name}' has unexpected type {type(struct_value).__name__}, "
                                     f"expected dict or None. Initializing as dict with None values.")
                        sample[struct_field_name] = {field: None for field in required_fields}
            
            return sample
        
        # Load in streaming mode first (avoids immediate type conversion)
        streaming_datasets = load_dataset(
            self.type,
            data_files={
                key.strip('.'): escaped_data_files[key]
                for key in escaped_data_files
            },
            streaming=True,
            **self.kwargs
        )
        
        # Fill missing struct fields and convert to regular dataset
        # Note: streaming mode returns IterableDatasetDict/IterableDataset, not DatasetDict/Dataset
        from datasets import IterableDatasetDict, IterableDataset
        
        # Check if it's IterableDatasetDict or DatasetDict
        is_iterable_dict = isinstance(streaming_datasets, IterableDatasetDict)
        is_regular_dict = isinstance(streaming_datasets, DatasetDict)
        
        if is_iterable_dict or is_regular_dict:
            filled_datasets = DatasetDict()
            for split_name, dataset in streaming_datasets.items():
                # Fill missing fields
                # Note: IterableDataset.map() doesn't support num_proc or desc, so we remove them
                if isinstance(dataset, IterableDataset):
                    filled_dataset = dataset.map(
                        fill_missing_fields
                    )
                else:
                    filled_dataset = dataset.map(
                        fill_missing_fields,
                        num_proc=num_proc,
                        desc=f'Filling missing struct fields in {split_name}'
                    )
                # Convert to list and create new dataset with features
                data_list = list(filled_dataset)
                from datasets import Dataset
                filled_datasets[split_name] = Dataset.from_list(data_list, features=features)
            return filled_datasets
        else:
            # Single dataset (IterableDataset or Dataset)
            # Fill missing fields
            if isinstance(streaming_datasets, IterableDataset):
                # IterableDataset.map() doesn't support num_proc or desc
                filled_dataset = streaming_datasets.map(
                    fill_missing_fields
                )
            else:
                filled_dataset = streaming_datasets.map(
                    fill_missing_fields,
                    num_proc=num_proc,
                    desc='Filling missing struct fields'
                )
            # Convert to list and create new dataset with features
            data_list = list(filled_dataset)
            from datasets import Dataset
            return Dataset.from_list(data_list, features=features)


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
