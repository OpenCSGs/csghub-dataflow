from jsonargparse.typing import PositiveInt, NonNegativeInt
from loguru import logger

from data_engine.utils.availability_utils import AvailabilityChecking
from data_engine.utils.model_utils import get_model, prepare_model

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType

OP_NAME = 'md_to_jsonl_chunk_mapper'

with AvailabilityChecking(['transformers'], OP_NAME):
    import transformers  # noqa: F401


@OPERATORS.register_module(OP_NAME)
class MdToJsonlChunkMapper(Mapper):
    """Mapper to split text samples into chunks by token count."""

    _batched_op = True
    # When model/tokenizer loading fails, propagate exception to fail the task
    _raise_on_exception = True

    def __init__(self,
                 hf_tokenizer: str = 'EleutherAI/pythia-6.9b-deduped',
                 chunk_size: PositiveInt = 100,
                 overlap: NonNegativeInt = 0,
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param hf_tokenizer: the tokenizer name of Hugging Face tokenizers.
            Default is 'EleutherAI/pythia-6.9b-deduped' which is a general-purpose tokenizer.
            Other options: 'hfl/chinese-bert-wwm-ext'.
        :param chunk_size: The number of tokens per chunk. Default is 100.
        :param overlap: The number of overlapping tokens between adjacent chunks. Default is 0 (no overlap).
            This helps preserve context at chunk boundaries.
        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.hf_tokenizer = hf_tokenizer
        
        # Validate parameters and warn if unreasonable
        if self.overlap >= self.chunk_size:
            logger.warning(
                f"Unreasonable parameter: overlap ({self.overlap}) >= chunk_size ({self.chunk_size}). "
                f"This will cause overlap to be larger than chunk itself. "
                f"Auto-adjusting overlap to 0. "
                f"Recommendation: Set overlap < chunk_size (ideally < chunk_size/2)."
            )
            self.overlap = 0
        elif self.overlap > self.chunk_size / 2:
            logger.warning(
                f"Unreasonable parameter: overlap ({self.overlap}) > chunk_size/2 ({self.chunk_size/2:.0f}). "
                f"Large overlap ratio may reduce processing efficiency. "
                f"Task will continue with current settings. "
                f"Recommendation: Consider reducing overlap to < {self.chunk_size/2:.0f} for better efficiency."
            )
        
        self.model_key = prepare_model(
            model_type='huggingface',
            pretrained_model_name_or_path=hf_tokenizer,
            return_model=False)

    def _split_text_by_tokens(self, text, tokenizer):
        """
        Split text into chunks by token count with optional overlap.
        Uses offset_mapping to slice at character boundaries, avoiding corruption
        when token boundaries cut through multi-byte Unicode characters (any lang).

        :param text: input text to split
        :param tokenizer: tokenizer instance
        :return: list of text chunks
        """
        if not text or not text.strip():
            return []

        # Ensure text is properly encoded as UTF-8 string (cross-platform compatible)
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Tokenize with offset_mapping for character-aligned boundaries (fixes UTF-8 split bug)
        try:
            enc = tokenizer(
                text,
                add_special_tokens=False,
                return_offsets_mapping=True,
                return_attention_mask=False,
            )
        except TypeError:
            # Fallback for tokenizers that don't support return_offsets_mapping
            enc = None

        offset_mapping = enc.get('offset_mapping') if enc else None
        if enc is not None and offset_mapping is not None:
            # Handle batched format: [[(0,1),(1,2),...]] for batch of 1
            if offset_mapping and isinstance(offset_mapping[0], (list, tuple)) and len(offset_mapping[0]) == 2 and isinstance(offset_mapping[0][0], (int, float)):
                pass  # offset_mapping[0] is (0,1) tuple, so it's flat - OK
            elif offset_mapping and isinstance(offset_mapping[0], list):
                offset_mapping = offset_mapping[0]  # Unwrap batch
            # Use character-boundary slicing: slice original text by token-aligned char positions
            token_ids = enc['input_ids'] if isinstance(enc['input_ids'][0], int) else enc['input_ids'][0]
            chunks = []
            step_size = self.chunk_size - self.overlap if self.overlap > 0 else self.chunk_size
            # When overlap=0: enforce strict boundary adjacency to prevent any character duplication
            # between chunks (works for any language/script: CJK, Latin, etc.)
            prev_end_char = 0 if self.overlap == 0 else None

            for i in range(0, len(token_ids), step_size):
                end_idx = min(i + self.chunk_size, len(offset_mapping))
                if end_idx <= 0:
                    continue
                start_char = max(offset_mapping[i][0], prev_end_char) if prev_end_char is not None else offset_mapping[i][0]
                end_char = offset_mapping[end_idx - 1][1]
                if start_char >= end_char:
                    continue
                chunk_text = text[start_char:end_char]
                if chunk_text.strip():
                    chunks.append(chunk_text.strip())
                if self.overlap == 0:
                    prev_end_char = end_char
            if chunks:
                return chunks
            logger.debug('offset_mapping produced no chunks, falling back to character-based split')

        # Fallback: character-boundary split when offset_mapping unavailable
        # Find char positions for each token boundary, then slice original text
        try:
            full_tokens = tokenizer.encode(text, add_special_tokens=False)
        except Exception:
            return [text]
        if not full_tokens:
            return [text]
        chunks = []
        step_size = self.chunk_size - self.overlap if self.overlap > 0 else self.chunk_size
        n_tokens = len(full_tokens)

        def _find_char_pos_for_token_count(target: int) -> int:
            """Binary search: smallest char pos where encode(text[:pos]) has >= target tokens."""
            if target <= 0:
                return 0
            if target >= n_tokens:
                return len(text)
            low, high = 0, len(text)
            for _ in range(25):
                mid = (low + high) // 2
                try:
                    cnt = len(tokenizer.encode(text[:mid], add_special_tokens=False))
                except Exception:
                    cnt = 0
                if cnt >= target:
                    high = mid
                else:
                    low = mid
                if high - low <= 1:
                    break
            return min(high, len(text))

        # When overlap=0: enforce strict boundary adjacency (prevents duplication for any text)
        prev_end_char = 0 if self.overlap == 0 else None
        for i in range(0, n_tokens, step_size):
            end_token = min(i + self.chunk_size, n_tokens)
            start_char = max(_find_char_pos_for_token_count(i), prev_end_char) if prev_end_char is not None else _find_char_pos_for_token_count(i)
            end_char = _find_char_pos_for_token_count(end_token)
            if start_char >= end_char:
                continue
            chunk_text = text[start_char:end_char]
            if chunk_text.strip():
                chunks.append(chunk_text.strip())
            if self.overlap == 0:
                prev_end_char = end_char
        return chunks if chunks else [text]

    def _split_text_by_tokens_decode_fallback(self, text, tokenizer):
        """Legacy decode-based fallback (may split mid-char; use only when char-based fails)."""
        try:
            tokens = tokenizer.encode(text, add_special_tokens=False)
        except Exception:
            return [text]
        try:
            tokens = tokenizer.encode(text, add_special_tokens=False)
        except Exception:
            return [text]
        
        chunks = []
        step_size = self.chunk_size - self.overlap if self.overlap > 0 else self.chunk_size
        
        for i in range(0, len(tokens), step_size):
            chunk_tokens = tokens[i:i + self.chunk_size]
            try:
                chunk_text = tokenizer.decode(
                    chunk_tokens,
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=True,
                )
            except Exception:
                continue
            if isinstance(chunk_text, bytes):
                chunk_text = chunk_text.decode('utf-8', errors='replace')
            else:
                chunk_text = chunk_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            # Trim trailing replacement chars from split multi-byte sequences
            while chunk_text and chunk_text[-1] == '\ufffd':
                chunk_text = chunk_text[:-1].rstrip()
            if chunk_text.strip():
                chunks.append(chunk_text.strip())
        return chunks if chunks else [text]

    def process(self, samples):
        """
        Process samples and split text by token count.

        :param samples: input samples (dict of lists)
        :return: output samples (dict of lists) with split chunks
        """
        tokenizer = get_model(self.model_key)
        
        # Reconstruct samples from "dict of lists" to "list of dicts"
        reconstructed_samples = []
        for i in range(len(samples[self.text_key])):
            reconstructed_samples.append(
                {key: samples[key][i] for key in samples.keys()})
        
        # Process each sample and split into chunks
        output_samples = []
        for sample in reconstructed_samples:
            text = sample.get(self.text_key, '')
            chunks = self._split_text_by_tokens(text, tokenizer)
            
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
        return """Mapper to split text samples into chunks by token count."""

    @classmethod
    @property
    def sample(cls):
        return Sample(
            'This is a long text that will be split into multiple chunks based on token count.',
            'This is a long text that will be split into multiple chunks based on token count.')

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("hf_tokenizer", DataType.STRING, {
                "EleutherAI/pythia-6.9b-deduped": "EleutherAI/pythia-6.9b-deduped",
                "hfl/chinese-bert-wwm-ext": "hfl/chinese-bert-wwm-ext"
            }, "EleutherAI/pythia-6.9b-deduped"),
            Param("chunk_size", DataType.PositiveFloat, None, 100),
            Param("overlap", DataType.PositiveFloat, None, 0),
        ]

