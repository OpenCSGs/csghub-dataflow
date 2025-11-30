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

        :param text: input text to split
        :param tokenizer: tokenizer instance
        :return: list of text chunks
        """
        if not text or not text.strip():
            return []

        # Ensure text is properly encoded as UTF-8 string (cross-platform compatible)
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        # Tokenize the entire text
        try:
            tokens = tokenizer.encode(text, add_special_tokens=False)
        except Exception as e:
            # If tokenization fails, return original text
            return [text]
        
        chunks = []
        # Calculate step size: if overlap > 0, each chunk moves forward by (chunk_size - overlap)
        # This creates overlapping regions between adjacent chunks
        step_size = self.chunk_size - self.overlap if self.overlap > 0 else self.chunk_size
        
        for i in range(0, len(tokens), step_size):
            chunk_tokens = tokens[i:i + self.chunk_size]
            # Decode tokens back to text with robust error handling for cross-platform compatibility
            try:
                chunk_text = tokenizer.decode(
                    chunk_tokens, 
                    skip_special_tokens=True,
                    clean_up_tokenization_spaces=False
                )
                # Ensure valid UTF-8 encoding (replace broken characters instead of ignoring)
                # This is critical for cross-platform compatibility (Windows/Linux)
                if isinstance(chunk_text, bytes):
                    chunk_text = chunk_text.decode('utf-8', errors='replace')
                else:
                    # Re-encode and decode to fix any encoding issues
                    chunk_text = chunk_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
            except Exception:
                # Fallback: if decode fails, try standard decode
                try:
                    chunk_text = tokenizer.decode(chunk_tokens, skip_special_tokens=True)
                    if isinstance(chunk_text, bytes):
                        chunk_text = chunk_text.decode('utf-8', errors='replace')
                    else:
                        chunk_text = chunk_text.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
                except Exception:
                    # If still fails, skip this chunk
                    continue
            
            if chunk_text.strip():  # Only add non-empty chunks
                chunks.append(chunk_text.strip())
        
        return chunks if chunks else [text]  # Return original text if no chunks created

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

