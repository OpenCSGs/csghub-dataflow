from jsonargparse.typing import PositiveInt, NonNegativeInt
import regex as re

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


@OPERATORS.register_module(OP_NAME)
class MdToJsonlSentenceChunkMapper(Mapper):
    """Mapper to split text samples into chunks at sentence boundaries."""

    _batched_op = True

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
        # Ensure overlap is less than chunk_size
        if self.chunk_overlap >= self.chunk_size:
            self.chunk_overlap = 0
        self.min_sentences_per_chunk = min_sentences_per_chunk
        self.hf_tokenizer = hf_tokenizer
        
        # Prepare tokenizer model
        self.tokenizer_model_key = prepare_model(
            model_type='huggingface',
            pretrained_model_name_or_path=hf_tokenizer,
            return_model=False)

    def _split_text_by_sentences(self, text, tokenizer):
        """
        Split text into chunks at sentence boundaries, respecting token limits.
        Uses mixed Chinese-English sentence segmentation by default.

        :param text: input text to split
        :param tokenizer: tokenizer instance for counting tokens
        :return: list of text chunks
        """
        if not text or not text.strip():
            return []

        # First, split text into sentences using mixed Chinese-English segmentation
        sentences = split_sentence_mixed(text)
        
        if not sentences:
            return [text] if text.strip() else []

        # Calculate token count for each sentence
        sentence_tokens = []
        for sentence in sentences:
            tokens = tokenizer.encode(sentence, add_special_tokens=False)
            sentence_tokens.append({
                'text': sentence,
                'tokens': tokens,
                'token_count': len(tokens)
            })

        chunks = []
        current_chunk_sentences = []
        current_chunk_tokens = []
        current_chunk_token_count = 0
        
        def create_chunk():
            """Helper function to create a chunk from current sentences"""
            if len(current_chunk_sentences) >= self.min_sentences_per_chunk:
                # Use empty string join for better Chinese support
                chunk_text = ''.join(current_chunk_sentences)
                if chunk_text.strip():
                    chunks.append(chunk_text.strip())
                return True
            return False
        
        def reset_chunk_with_overlap():
            """Reset chunk while handling overlap"""
            if self.chunk_overlap > 0:
                # Calculate how many sentences to keep for overlap (from the end)
                overlap_tokens = 0
                overlap_sentences = []
                # Start from the last sentence and work backwards
                for j in range(len(current_chunk_sentences) - 1, -1, -1):
                    # Find the corresponding sentence token count
                    sent_text = current_chunk_sentences[j]
                    # Find matching sentence in sentence_tokens to get token count
                    sent_tokens = 0
                    for st in sentence_tokens:
                        if st['text'] == sent_text:
                            sent_tokens = st['token_count']
                            break
                    
                    if overlap_tokens + sent_tokens <= self.chunk_overlap:
                        overlap_sentences.insert(0, sent_text)
                        overlap_tokens += sent_tokens
                    else:
                        break
                
                current_chunk_sentences[:] = overlap_sentences
                if overlap_sentences:
                    overlap_text = ''.join(overlap_sentences)
                    current_chunk_tokens = tokenizer.encode(overlap_text, add_special_tokens=False)
                    current_chunk_token_count = len(current_chunk_tokens)
                else:
                    current_chunk_tokens = []
                    current_chunk_token_count = 0
            else:
                current_chunk_sentences.clear()
                current_chunk_tokens = []
                current_chunk_token_count = 0
        
        i = 0
        while i < len(sentence_tokens):
            sent_info = sentence_tokens[i]
            
            # Check if adding this sentence would exceed chunk_size
            if current_chunk_token_count + sent_info['token_count'] > self.chunk_size:
                # If we have at least min_sentences_per_chunk, create a chunk
                if len(current_chunk_sentences) >= self.min_sentences_per_chunk:
                    if create_chunk():
                        reset_chunk_with_overlap()
                        # Don't increment i, retry with current sentence
                        continue
                else:
                    # If we don't have enough sentences yet, force add this sentence
                    # (even if it exceeds chunk_size) to meet min_sentences_per_chunk requirement
                    current_chunk_sentences.append(sent_info['text'])
                    current_chunk_tokens.extend(sent_info['tokens'])
                    current_chunk_token_count += sent_info['token_count']
                    i += 1
                    continue
            
            # Add sentence to current chunk
            current_chunk_sentences.append(sent_info['text'])
            current_chunk_tokens.extend(sent_info['tokens'])
            current_chunk_token_count += sent_info['token_count']
            
            # Check if we should create a chunk now (if we have enough sentences and are close to chunk_size)
            # This ensures min_sentences_per_chunk is respected even when not exceeding chunk_size
            if len(current_chunk_sentences) >= self.min_sentences_per_chunk:
                # If adding next sentence would exceed chunk_size, create chunk now
                if i + 1 < len(sentence_tokens):
                    next_sent_info = sentence_tokens[i + 1]
                    if current_chunk_token_count + next_sent_info['token_count'] > self.chunk_size:
                        if create_chunk():
                            reset_chunk_with_overlap()
                            # Continue to process next sentence
                            i += 1
                            continue
            
            i += 1

        # Add remaining sentences as final chunk only if it meets min_sentences_per_chunk requirement
        if current_chunk_sentences:
            if len(current_chunk_sentences) >= self.min_sentences_per_chunk:
                chunk_text = ''.join(current_chunk_sentences)
                if chunk_text.strip():
                    chunks.append(chunk_text.strip())
            # If remaining sentences don't meet min requirement, they are discarded
            # (or could be merged with previous chunk if needed, but current logic discards them)

        return chunks if chunks else [text]  # Return original text if no chunks created

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

