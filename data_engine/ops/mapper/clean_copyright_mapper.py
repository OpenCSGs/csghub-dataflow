# --------------------------------------------------------
# Clean copyright notices from documents (PDF->MD->JSONL pipeline).
# For everyday documents, not source code.
# --------------------------------------------------------

from typing import List, Tuple, Union

import regex as re
from loguru import logger

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType


@OPERATORS.register_module('clean_copyright_mapper')
class CleanCopyrightMapper(Mapper):
    """Remove copyright notices from documents (PDF->MD->JSONL)."""

    def __init__(self,
                 matching_rules: Union[str, List[str], Tuple[str]] = [],
                 *args,
                 **kwargs):
        """
        :param matching_rules: User-defined regex patterns for copyright removal (required).
            All matching content is replaced with space. No built-in patterns.
            - List/tuple: ["pattern1", "pattern2"] (recommended)
            - String: single pattern or comma-separated patterns "pattern1,pattern2"
        """
        super().__init__(*args, **kwargs)
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.modified_samples = 0
        self.unmodified_samples = 0

        # Normalize matching_rules to list (same as multi_keyword_filter)
        if matching_rules is None:
            raw_patterns = []
        elif isinstance(matching_rules, (list, tuple)):
            raw_patterns = list(matching_rules)
        elif isinstance(matching_rules, str):
            if ',' in matching_rules or '，' in matching_rules:
                normalized = matching_rules.replace('，', ',')
                raw_patterns = [p.strip() for p in normalized.split(',') if p.strip()]
            else:
                raw_patterns = [matching_rules] if matching_rules else []
        else:
            raw_patterns = []
        raw_patterns = [p for p in raw_patterns if p]

        # Fix over-escaped regex from JSON/frontend (e.g. \\d -> \d for digit match)
        # Only fix \\X -> \X for chars where \X is a standard regex escape; never touch correct \X
        _OVER_ESCAPE_PAIRS = (
            ('d', 'd'), ('s', 's'), ('w', 'w'), ('D', 'D'), ('S', 'S'), ('W', 'W'),  # \d \s \w etc
            ('n', 'n'), ('r', 'r'), ('t', 't'), ('f', 'f'), ('b', 'b'),  # \n \r \t \f \b
            ('.', '.'), ('+', '+'), ('*', '*'), ('?', '?'), ('-', '-'),  # \. \+ \* \? \-
            ('$', '$'),  # \$ for literal $ (e.g. $99.99)
            ('[', '['), (']', ']'), ('(', '('), (')', ')'),  # \[ \] \( \) literal brackets/parens
            ('{', '{'), ('}', '}'), ('|', '|'), ('^', '^'),  # \{ \} \| \^ literal in patterns
        )

        def _fix_over_escape(s):
            changed = True
            while changed:
                changed = False
                for _before, _after in _OVER_ESCAPE_PAIRS:
                    old, new = '\\\\' + _before, '\\' + _after
                    if old in s:
                        s = s.replace(old, new)
                        changed = True
            return s

        # Compile custom regex patterns; skip invalid ones with warning
        self.matching_rules = []
        self._invalid_regex_warnings = []  # stored for MongoDB logging in run()
        fixed_patterns = []
        for p in raw_patterns:
            p_fixed = _fix_over_escape(p)
            fixed_patterns.append(p_fixed)
            try:
                self.matching_rules.append(re.compile(p_fixed))
            except re.error as e:
                msg = f"[clean_copyright_mapper] Invalid matching_rules regex, skipped: {p_fixed!r} - {e}"
                logger.warning(msg)
                self._invalid_regex_warnings.append(msg)

        # Debug: log matching_rules for troubleshooting
        if raw_patterns:
            logger.info(
                f"[clean_copyright_mapper] matching_rules: raw_input={raw_patterns!r}, "
                f"after_fix={fixed_patterns!r}, compiled={len(self.matching_rules)} pattern(s)"
            )

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1

        original = sample[self.text_key]
        text = original

        # 1. Apply user-defined matching_rules (replace matched content with space)
        for pat in self.matching_rules:
            text = pat.sub(' ', text)

        # 2. Collapse excessive blank lines
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = text.strip()

        sample[self.text_key] = text

        if getattr(self, 'enable_detailed_logging', False):
            if sample[self.text_key] != original:
                self.modified_samples += 1
            else:
                self.unmodified_samples += 1

        return sample

    @classmethod
    @property
    def description(cls):
        return "Remove copyright notices from documents (PDF->MD->JSONL)."

    @classmethod
    @property
    def sample(cls):
        return Sample(
            "Copyright (c) 2024 Example Corp. All rights reserved.\n\nDocument body here.",
            "Document body here."
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("matching_rules", DataType.LIST, None, []),
        ]

    def run(self, dataset, *, exporter=None, tracer=None):
        # Log invalid regex warnings to MongoDB when job_uid is available
        invalid_warnings = getattr(self, '_invalid_regex_warnings', [])
        if invalid_warnings and hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.pg_log_tools.tools import insert_pipline_job_run_task_log_info
            for msg in invalid_warnings:
                insert_pipline_job_run_task_log_info(
                    self.job_uid, msg,
                    operator_name=self._name, operator_index=self.pipline_index
                )
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples = 0
            self.modified_samples = 0
            self.unmodified_samples = 0
        result = super().run(dataset, exporter=exporter, tracer=tracer)
        if getattr(self, 'enable_detailed_logging', False):
            self._log_mapper_summary()
        return result

    def _log_mapper_summary(self):
        try:
            total = self.total_samples
            modified = self.modified_samples
            unmodified = self.unmodified_samples
            if total == 0:
                return
            self._log_line("=" * 60)
            self._log_line(f"[{self._name}] Copyright cleanup summary")
            self._log_line("=" * 60)
            self._log_line(f"Total samples processed: {total}")
            self._log_line(f"Samples with copyright removed: {modified} ({modified / total * 100:.2f}%)")
            self._log_line(f"Unchanged: {unmodified} ({unmodified / total * 100:.2f}%)")
            self._log_line("=" * 60)
        except Exception as e:
            import traceback
            from loguru import logger
            error_msg = f"Failed to generate mapper logging: {e}\n{traceback.format_exc()}"
            logger.error(error_msg)
            if hasattr(self, 'job_uid') and self.job_uid:
                from data_celery.pg_log_tools.tools import insert_pipline_job_run_task_log_error
                insert_pipline_job_run_task_log_error(
                    self.job_uid, error_msg,
                    operator_name=self._name, operator_index=self.pipline_index
                )

    def _log_line(self, message):
        from loguru import logger
        logger.info(message)
        if hasattr(self, 'job_uid') and self.job_uid:
            from data_celery.pg_log_tools.tools import insert_pipline_job_run_task_log_info
            insert_pipline_job_run_task_log_info(
                self.job_uid, message,
                operator_name=self._name, operator_index=self.pipline_index
            )
