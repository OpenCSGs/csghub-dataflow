from jsonargparse.typing import PositiveInt, NonNegativeInt
import regex as re
from loguru import logger

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'md_to_jsonl_sentence_chunk_mapper'

with AvailabilityChecking(['transformers'], OP_NAME):
    import transformers  # noqa: F401


def split_sentence_mixed(text):
    """
    Split text into sentences for mixed Chinese-English text.
    Supports both Chinese (。！？) and English (.!?) punctuation.
    """
    text = re.sub('([.。！!？\?])([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('(\.{6})([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('(\…{2})([^’”])', r'\1\n\2', text)  # noqa
    text = re.sub('([.。!！？\?\.{6}\…{2}][’”])([^’”])', r'\1\n\2', text)  # noqa
    sentences = text.split('\n')
    return [s.strip() for s in sentences if s.strip()]


def split_sentence_with_positions(text):
    """
    Split text into sentences and return their (start, end) positions in the original text.
    This preserves original newlines and separators when generating chunks.
    
    Supports both Chinese (。！？) and English (.!?) punctuation.
    
    :param text: input text to split
    :return: list of (start, end) tuples representing sentence ranges in original text
    
    Edge cases handled:
    - Empty text / whitespace only: returns []
    - No punctuation in text: returns [(0, len(text))] as single sentence
    - Text ending without punctuation: includes final segment
    - Consecutive punctuation: filters out empty ranges
    - Leading punctuation: filters out empty ranges
    """
    if not text or not text.strip():
        return []
    
    # Pattern to match sentence-ending punctuation (language-agnostic)
    # - Single punctuation: .。！!？?
    # - Ellipsis: ...... or ……
    # - Punctuation followed by quotes
    # - Do NOT split on . when part of ordinal/number (generic rule for any document format):
    #   - Arabic numerals: 1. 2. 3.2 1.0, decimals, versions
    #   - Roman numerals: I. II. III. IV.
    #   - Common abbrev. (Mr. Dr. etc. often end with these letters)
    # Quote characters: ' " ' " (ASCII and Chinese quotes)
    quote_chars = "'\"\u2018\u2019\u201c\u201d"
    # . only when NOT preceded by digit or Roman numeral letter (covers ordinals, versions, abbrev.)
    # Exclude . when part of file extension (e.g. .jpg in ![](/xxx.jpg)) to avoid splitting markdown images
    _sent_end_dot = r'(?<![0-9IVXLCDMivxlcdm])\.(?!\s*(?:jpe?g|png|gif|webp|svg|bmp|pdf)\b)'
    # Exclude ASCII ! when part of markdown image syntax ![](
    _sent_end_bang = r'!(?!\[)'
    sent_end = rf'(?:[。！？?]|{_sent_end_bang}|{_sent_end_dot})'
    # Build pattern
    pattern = re.compile(
        f'({sent_end}(?![{quote_chars}])|'  # Punctuation not followed by quote
        r'\.{6}|'  # Six dots (English ellipsis)
        r'\…{2}|'  # Two … (Chinese ellipsis)
        f'{sent_end}[{quote_chars}])'  # Punctuation followed by quote
    )
    
    # Collect split points (positions after sentence-ending punctuation)
    split_points = [0]
    for m in pattern.finditer(text):
        split_points.append(m.end())
    
    # Handle text ending without punctuation: add len(text) as final split point
    if split_points[-1] < len(text):
        split_points.append(len(text))
    
    # Remove duplicates and sort
    split_points = sorted(set(split_points))
    
    # Generate ranges, filtering out empty/whitespace-only segments
    ranges = []
    for i in range(len(split_points) - 1):
        start, end = split_points[i], split_points[i + 1]
        if text[start:end].strip():  # Skip whitespace-only segments
            ranges.append((start, end))
    
    # If no valid ranges but text has content, return entire text as one sentence
    if not ranges and text.strip():
        ranges = [(0, len(text))]
    
    return ranges


@OPERATORS.register_module(OP_NAME)
class MdToJsonlSentenceChunkMapper(Mapper):
    """Mapper to split text samples into chunks at sentence boundaries."""

    _batched_op = True
    # When model/tokenizer loading fails, propagate exception to fail the task
    _raise_on_exception = True

    def __init__(self,
                 hf_tokenizer: str = 'EleutherAI/pythia-6.9b-deduped',
                 chunk_size: PositiveInt = 512,
                 chunk_overlap: NonNegativeInt = 0,
                 min_sentences_per_chunk: PositiveInt = 1,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param hf_tokenizer: the tokenizer name of Hugging Face tokenizers.
            Default is 'EleutherAI/pythia-6.9b-deduped'.
            Other options: 'hfl/chinese-bert-wwm-ext'.
        :param chunk_size: Maximum number of tokens per chunk. Default is 512.
        :param chunk_overlap: Number of tokens to overlap between consecutive chunks. Default is 0.
        :param min_sentences_per_chunk: Minimum number of sentences to include in each chunk. Default is 1.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.hf_tokenizer = hf_tokenizer
        
        # Validate parameters and warn if unreasonable
        if self.chunk_overlap >= self.chunk_size:
            logger.warning(
                f"Unreasonable parameter: chunk_overlap ({self.chunk_overlap}) >= chunk_size ({self.chunk_size}). "
                f"This will cause overlap to be larger than chunk itself. "
                f"Auto-adjusting chunk_overlap to 0. "
                f"Recommendation: Set chunk_overlap < chunk_size (ideally < chunk_size/2)."
            )
            self.chunk_overlap = 0
        elif self.chunk_overlap > self.chunk_size / 2:
            logger.warning(
                f"Unreasonable parameter: chunk_overlap ({self.chunk_overlap}) > chunk_size/2 ({self.chunk_size/2:.0f}). "
                f"Large overlap may cause frequent chunk overflow in sentence-based chunking. "
                f"Task will continue, but expect more ERROR logs about chunk overflow. "
                f"Recommendation: Reduce chunk_overlap to < {self.chunk_size/2:.0f} or increase chunk_size."
            )
        
        if self.min_sentences_per_chunk < 1:
            logger.warning(
                f"Unreasonable parameter: min_sentences_per_chunk ({self.min_sentences_per_chunk}) < 1. "
                f"Auto-adjusting to 1. "
                f"Each chunk must contain at least 1 sentence."
            )
            self.min_sentences_per_chunk = 1
        
        # Prepare tokenizer model
        self.tokenizer_model_key = prepare_model(
            model_type='huggingface',
            pretrained_model_name_or_path=hf_tokenizer,
            return_model=False)

    def _split_text_by_sentences(self, text, tokenizer):
        """
        Split text into chunks at sentence boundaries, respecting token limits.
        Uses position-based slicing to preserve original newlines and separators.

        :param text: input text to split
        :param tokenizer: tokenizer instance for counting tokens
        :return: list of text chunks (preserving original formatting)
        """
        if not text or not text.strip():
            return []

        # Ensure text is properly encoded as UTF-8 string (cross-platform compatible)
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Get sentence ranges (start, end) instead of sentence strings
        # This preserves original newlines and separators
        sentence_ranges = split_sentence_with_positions(text)
        
        if not sentence_ranges:
            return [text] if text.strip() else []

        # Calculate token count for each sentence range
        sentence_info_list = []
        for start, end in sentence_ranges:
            sentence_text = text[start:end]
            try:
                tokens = tokenizer.encode(sentence_text, add_special_tokens=False)
                token_count = len(tokens)
            except Exception:
                token_count = len(sentence_text)
            
            sentence_info_list.append({
                'start': start,
                'end': end,
                'token_count': token_count
            })

        chunks = []
        # Store (start, end) tuples for current chunk
        current_chunk_ranges = []
        current_chunk_token_count = 0
        
        def create_chunk():
            """Helper function to create a chunk from current ranges by slicing original text"""
            nonlocal current_chunk_token_count
            if len(current_chunk_ranges) >= self.min_sentences_per_chunk:
                # Slice from original text to preserve newlines/separators
                first_start = current_chunk_ranges[0][0]
                last_end = current_chunk_ranges[-1][1]
                chunk_text = text[first_start:last_end]
                
                if chunk_text.strip():
                    if current_chunk_token_count > self.chunk_size:
                        overflow_amount = current_chunk_token_count - self.chunk_size
                        logger.warning(
                            f"Chunk overflow detected: Created chunk has {current_chunk_token_count} tokens, "
                            f"exceeds chunk_size ({self.chunk_size}) by {overflow_amount} tokens. "
                            f"Contains {len(current_chunk_ranges)} sentence(s). "
                            f"Operation: Preserving full chunk without truncation."
                        )
                    chunks.append(chunk_text)
                return True
            return False
        
        def reset_chunk_with_overlap():
            """Reset chunk while handling overlap, keeping ranges from the end"""
            nonlocal current_chunk_ranges, current_chunk_token_count
            if self.chunk_overlap > 0:
                overlap_tokens = 0
                overlap_ranges = []
                # Work backwards from the end of current chunk
                for j in range(len(current_chunk_ranges) - 1, -1, -1):
                    rng = current_chunk_ranges[j]
                    # Find token count for this range
                    rng_token_count = 0
                    for info in sentence_info_list:
                        if info['start'] == rng[0] and info['end'] == rng[1]:
                            rng_token_count = info['token_count']
                            break
                    
                    if overlap_tokens + rng_token_count <= self.chunk_overlap:
                        overlap_ranges.insert(0, rng)
                        overlap_tokens += rng_token_count
                    else:
                        break
                
                current_chunk_ranges = overlap_ranges
                current_chunk_token_count = overlap_tokens
            else:
                current_chunk_ranges = []
                current_chunk_token_count = 0
        
        i = 0
        while i < len(sentence_info_list):
            sent_info = sentence_info_list[i]
            sent_range = (sent_info['start'], sent_info['end'])
            
            # Check if adding this sentence would exceed chunk_size
            if current_chunk_token_count + sent_info['token_count'] > self.chunk_size:
                if len(current_chunk_ranges) >= self.min_sentences_per_chunk:
                    if create_chunk():
                        reset_chunk_with_overlap()
                        # Check if overlap + current sentence still exceeds
                        if current_chunk_token_count + sent_info['token_count'] > self.chunk_size:
                            actual_total = current_chunk_token_count + sent_info['token_count']
                            logger.warning(
                                f"Chunk overflow detected: Current sentence ({sent_info['token_count']} tokens) + "
                                f"overlap ({current_chunk_token_count} tokens) = {actual_total} tokens exceeds "
                                f"chunk_size ({self.chunk_size}). "
                                f"Operation: Clearing overlap and preserving full sentence as new chunk. "
                                f"Suggestion: Reduce chunk_overlap or increase chunk_size."
                            )
                            current_chunk_ranges = []
                            current_chunk_token_count = 0
                        else:
                            continue
                else:
                    # Force add this sentence to meet min_sentences_per_chunk
                    if sent_info['token_count'] > self.chunk_size:
                        overflow_amount = sent_info['token_count'] - self.chunk_size
                        sentence_preview = text[sent_info['start']:sent_info['end']][:100]
                        logger.warning(
                            f"Chunk overflow detected: Single sentence has {sent_info['token_count']} tokens, "
                            f"exceeds chunk_size ({self.chunk_size}) by {overflow_amount} tokens. "
                            f"Operation: Preserving full sentence as oversized chunk (will not truncate). "
                            f"Sentence preview: '{sentence_preview}...' "
                            f"Suggestion: Increase chunk_size parameter to accommodate long sentences."
                        )
                    current_chunk_ranges.append(sent_range)
                    current_chunk_token_count += sent_info['token_count']
                    i += 1
                    continue
            
            # Add sentence to current chunk
            current_chunk_ranges.append(sent_range)
            current_chunk_token_count += sent_info['token_count']
            
            # Check if we should create a chunk now
            if len(current_chunk_ranges) >= self.min_sentences_per_chunk:
                if i + 1 < len(sentence_info_list):
                    next_sent_info = sentence_info_list[i + 1]
                    if current_chunk_token_count + next_sent_info['token_count'] > self.chunk_size:
                        if create_chunk():
                            reset_chunk_with_overlap()
                            i += 1
                            continue
            
            i += 1

        # Add remaining sentences as final chunk (always preserve, even if < min_sentences_per_chunk)
        if current_chunk_ranges:
            first_start = current_chunk_ranges[0][0]
            last_end = current_chunk_ranges[-1][1]
            chunk_text = text[first_start:last_end]
            
            if chunk_text.strip():
                if current_chunk_token_count > self.chunk_size:
                    overflow_amount = current_chunk_token_count - self.chunk_size
                    logger.warning(
                        f"Final chunk overflow detected: Final chunk has {current_chunk_token_count} tokens, "
                        f"exceeds chunk_size ({self.chunk_size}) by {overflow_amount} tokens. "
                        f"Contains {len(current_chunk_ranges)} sentence(s). "
                        f"Operation: Preserving full chunk without truncation. "
                        f"Suggestion: Increase chunk_size or reduce chunk_overlap."
                    )
                chunks.append(chunk_text)

        return chunks if chunks else [text]

    def process(self, samples):
        """
        Process samples and split text by sentence boundaries.
        Uses mixed Chinese-English sentence segmentation by default.

        :param samples: input samples (dict of lists)
        :return: output samples (dict of lists) with split chunks
        """
        tokenizer = get_model(self.tokenizer_model_key)
        
        # Reconstruct samples from "dict of lists" to "list of dicts"
        reconstructed_samples = []
        for i in range(len(samples[self.text_key])):
            reconstructed_samples.append(
                {key: samples[key][i] for key in samples.keys()})
        
        # Process each sample and split into chunks
        output_samples = []
        for sample in reconstructed_samples:
            text = sample.get(self.text_key, '')
            chunks = self._split_text_by_sentences(text, tokenizer)
            
            # Create a new sample for each chunk
            for chunk in chunks:
                new_sample = sample.copy()
                new_sample[self.text_key] = chunk
                output_samples.append(new_sample)
        
        # Reconstruct samples from "list of dicts" to "dict of lists"
        if not output_samples:
            # Return empty dict with same structure if no output
            return {key: [] for key in samples.keys()}
        
        # Get all keys from all samples (in case some samples have different keys)
        all_keys = set()
        for sample in output_samples:
            all_keys.update(sample.keys())
        
        res_samples = {}
        for key in all_keys:
            res_samples[key] = [s.get(key, None) for s in output_samples]
        
        return res_samples

    @classmethod
    @property
    def description(cls):
        return """Mapper to split text samples into chunks at sentence boundaries. 
        Supports mixed Chinese-English text by default."""

    @classmethod
    @property
    def sample(cls):
        return Sample(
            'This is a long text. It contains multiple sentences. Each sentence will be preserved. The chunks respect sentence boundaries.',
            'This is a long text. It contains multiple sentences. Each sentence will be preserved. The chunks respect sentence boundaries.')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_tokenizer", DataType.STRING, {
                "EleutherAI/pythia-6.9b-deduped": "EleutherAI/pythia-6.9b-deduped",
                "hfl/chinese-bert-wwm-ext": "hfl/chinese-bert-wwm-ext"
            }, "EleutherAI/pythia-6.9b-deduped"),
            Param("chunk_size", DataType.PositiveFloat, None, 512),
            Param("chunk_overlap", DataType.PositiveFloat, None, 0),
            Param("min_sentences_per_chunk", DataType.PositiveFloat, None, 1),
        ]

