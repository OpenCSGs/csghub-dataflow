import sys
import os
import numpy as np
from jsonargparse.typing import NonNegativeInt
from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import load_audio, load_data_with_context

from ..base_op import OPERATORS, Mapper, Sample, Param, DataType
from ..op_fusion import LOADED_AUDIOS
from loguru import logger

from data_engine.utils.availability_utils import AvailabilityChecking
import json

OP_NAME = 'annotate_edu_train_bert_scorer_mapper'

with AvailabilityChecking(['openai', 'scikit-learn'], OP_NAME):
    from openai import OpenAI
    from sklearn.metrics.pairwise import cosine_similarity

@OPERATORS.register_module(OP_NAME)
@LOADED_AUDIOS.register_module(OP_NAME)
class AnnotateEduTrainBertScorer(Mapper):
    def __init__(self,
         auth_token: str = "",
         model_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1",
         model_name: str = "text-embedding-v4",
         dimensions: int = 1024,
         query_text: str = "What is Deep Learning?",
         *args,
         **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token = auth_token
        self.model_url = model_url
        self.model_name = model_name
        self.dimensions = dimensions
        self.query_text = query_text
        self.client = None
        
        # Enable detailed logging
        self.enable_detailed_logging = True
        self.total_samples = 0
        self.scored_samples = 0
        self.failed_samples = 0

    def _get_client(self):
        if self.client is None:
            if not self.auth_token:
                raise ValueError("auth_token_cannot_be_empty")
            if not self.model_url:
                raise ValueError("model_url_cannot_be_empty")
            try:
                self.client = OpenAI(api_key=self.auth_token, base_url=self.model_url)
                logger.info("OpenAI client created successfully")
            except Exception as e:
                raise RuntimeError(f"the_creation_of_the_openai_client_failed: {str(e)}")
        return self.client

    def compute_stats(self, sample, context=False):
        score_field = f"{self.text_key}_score"
        content = sample[self.text_key]
        sample[score_field] = 0

        score = self.get_score_from_model(self.query_text, content)
        if score is not None:
            sample[score_field] = score
        return sample

    def get_score_from_model(self, query_text, content):
        client = self._get_client()
        
        try:
            query_response = client.embeddings.create(
                model=self.model_name,
                input=[query_text],
                dimensions=self.dimensions,
                encoding_format="float"
            )
            query_embedding = query_response.data[0].embedding

            content_response = client.embeddings.create(
                model=self.model_name,
                input=[content],
                dimensions=self.dimensions,
                encoding_format="float"
            )
            content_embedding = content_response.data[0].embedding

            similarity = cosine_similarity(
                [query_embedding], 
                [content_embedding]
            )[0][0]
            
            # The similarity range is usually between 0.1 and 0.9, remapped to 0 to 5 points
            if similarity < 0.3:  # lowCorrelation
                score = similarity * 10 / 3  # 0-1points
            elif similarity < 0.6:  # moderateCorrelation
                score = 1 + (similarity - 0.3) * 6.67  # 1-3points
            else:  # highCorrelation
                score = 3 + (similarity - 0.6) * 5  # 3-5points
            
            return float(max(0, min(5, score)))
            
        except Exception as e:
            logger.error(f"the_embedding_api_call_failed: {str(e)}")
            raise RuntimeError(f"failed_to_obtain_the_text_embedding_vector: {str(e)}")

    def process(self, sample):
        if getattr(self, 'enable_detailed_logging', False):
            self.total_samples += 1
        
        try:
            result = self.compute_stats(sample)
            if getattr(self, 'enable_detailed_logging', False):
                self.scored_samples += 1
            return result
        except Exception as e:
            if getattr(self, 'enable_detailed_logging', False):
                self.failed_samples += 1
            return sample

    @classmethod
    @property
    def sample(cls):
        return Sample('Here is a more concise translation of the provided sentence:"Score a field and add a _score field for the result."', "")

    @classmethod
    @property
    def description(cls):
        return """ Annotate Edu Train BERT Scorer"""

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("auth_token", DataType.STRING, {}, ""),
            Param("model_url", DataType.STRING, {}, "https://dashscope.aliyuncs.com/compatible-mode/v1"),
            Param("model_name", DataType.STRING, {}, "text-embedding-v4"),
            Param("dimensions", DataType.INTEGER, {}, 1024),
            Param("query_text", DataType.STRING, {}, "What is Deep Learning?"),
        ]