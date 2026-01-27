from typing import List, Tuple, Union

from loguru import logger

from ..base_op import OPERATORS, Filter, Sample, Param, DataType

OP_NAME = 'multi_keyword_filter'


@OPERATORS.register_module(OP_NAME)
class MultiKeywordFilter(Filter):
    """Filter to remove samples that contain any of the specified keywords."""

    def __init__(self,
                 keywords: Union[str, List[str], Tuple[str]] = [],
                 case_sensitive: bool = False,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param keywords: Keywords to filter. Recommended format:
            - A list/tuple: list of keywords like ["keyword1", "keyword2", ","] (recommended)
            - A string: single keyword or comma-separated keywords like "keyword1,keyword2" (for backward compatibility)
              Note: If you need to use comma as a keyword, use list format instead.
        :param case_sensitive: Whether the keyword matching is case sensitive.
            If False, matching will be case-insensitive.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.case_sensitive = case_sensitive
        
        # Enable detailed logging for this filter
        self.enable_detailed_logging = True
        
        # Normalize keywords to a list
        # Priority: list/tuple > string (for backward compatibility)
        if keywords is None:
            self.keywords = []
        elif isinstance(keywords, (list, tuple)):
            # Direct list/tuple input (recommended format)
            self.keywords = list(keywords)
        elif isinstance(keywords, str):
            # Handle comma-separated string (for backward compatibility)
            # Support both English comma (,) and Chinese comma (，)
            if ',' in keywords or '，' in keywords:
                # Replace Chinese comma with English comma for consistent splitting
                normalized_keywords = keywords.replace('，', ',')
                self.keywords = [kw.strip() for kw in normalized_keywords.split(',') if kw.strip()]
            else:
                self.keywords = [keywords] if keywords else []
        else:
            self.keywords = []
        
        # Remove empty keywords
        self.keywords = [kw for kw in self.keywords if kw]
        
        # Log initialization
        logger.info(f"[{OP_NAME}] Initialized with keywords={self.keywords}, "
                    f"case_sensitive={self.case_sensitive}, text_key={self.text_key}")

    def compute_stats(self, sample):
        # multi_keyword_filter doesn't compute stats, but we add detail for logging
        if not self.keywords:
            keep = True
            reason = 'kept'
            matched_keyword = None
        else:
            text = sample[self.text_key]
            matched_keyword = None
            
            # Convert to lowercase if case-insensitive matching
            if not self.case_sensitive:
                text_lower = text.lower()
                keywords_to_check = [kw.lower() for kw in self.keywords]
                
                # Check if any keyword is found in the text
                for i, keyword in enumerate(keywords_to_check):
                    if keyword in text_lower:
                        matched_keyword = self.keywords[i]  # Use original case
                        break
            else:
                keywords_to_check = self.keywords
                
                # Check if any keyword is found in the text
                for keyword in keywords_to_check:
                    if keyword in text:
                        matched_keyword = keyword
                        break
            
            keep = matched_keyword is None
            reason = 'kept' if keep else 'keyword_found'
        
        # Store detailed information for logging
        sample['__dj__stats__']['multi_keyword_filter_detail'] = {
            'matched_keyword': matched_keyword,
            'keep': keep,
            'reason': reason,
            'case_sensitive': self.case_sensitive
        }
        
        return sample

    def process(self, sample):
        """
        Filter samples that contain any of the keywords.
        
        :param sample: sample to check
        :return: True to keep the sample, False to filter it out
        """
        if not self.keywords:
            # If no keywords specified, keep all samples
            return True
        
        text = sample[self.text_key]
        
        # Convert to lowercase if case-insensitive matching
        if not self.case_sensitive:
            # Case-insensitive: convert both text and keywords to lowercase
            text_lower = text.lower()
            keywords_to_check = [kw.lower() for kw in self.keywords]
            
            # Check if any keyword is found in the text
            for keyword in keywords_to_check:
                if keyword in text_lower:
                    logger.info(f"[{OP_NAME}] Filtered out sample (case-insensitive): keyword '{keyword}' found in text '{text[:100]}...'")
                    return False
        else:
            # Case-sensitive: keep original case for both text and keywords
            keywords_to_check = self.keywords
            
            # Check if any keyword is found in the text
            for keyword in keywords_to_check:
                if keyword in text:
                    logger.info(f"[{OP_NAME}] Filtered out sample (case-sensitive): keyword '{keyword}' found in text '{text[:100]}...'")
                    return False
        
        # No keywords found, keep the sample
        return True

    @classmethod
    @property
    def description(cls):
        return """Filter to remove samples that contain any of the specified keywords."""

    @classmethod
    @property
    def sample(cls):
        return Sample("这是一个测试文本，包含一些关键字", "")

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("keywords", DataType.LIST, None, []),
            Param("case_sensitive", DataType.BOOLEAN, None, False),
        ]

