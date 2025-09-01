import sys

import librosa
import numpy as np
from jsonargparse.typing import NonNegativeInt
from data_engine.ops.base_op import OPERATORS, Filter, Sample
from data_engine.utils.constant import Fields, StatsKeys
from data_engine.utils.mm_utils import load_audio, load_data_with_context

from ..base_op import OPERATORS, Filter,Param,DataType
from ..op_fusion import LOADED_AUDIOS

import requests
import json
import re

OP_NAME = 'annotate_edu_train_bert_scorer'

@OPERATORS.register_module(OP_NAME)
@LOADED_AUDIOS.register_module(OP_NAME)
class AnnotateEduTrainBertScorer(Filter):
    def __init__(self,
         auth_token: DataType.STRING = "",
         model_url: DataType.STRING = "https://esupw2o6m6f4.space.opencsg.com/rerank",
         *args,
         **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_token = auth_token
        self.model_url = model_url

    def compute_stats(self, sample, context=False):
        score_field = f"{self.text_key}_score"
        content = sample[self.text_key]
        sample[score_field] = 0

        # auth_token = "9acc3ea387b5479607bdeb5386af6e3483fbf070"
        data = {
            "query": "What is Deep Learning?",
            "raw_scores": False,
            "return_text": False,
            "texts": [
                content
            ],
            "truncate": False,
            "truncation_direction": "right"
        }
        score = self.get_score_from_model(self.model_url,self.auth_token, data)
        if score is not None:
            sample[score_field] = score
        return sample

    def get_score_from_model(self,model_url, auth_token, data):

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {auth_token}'
        }

        response = requests.post(model_url, json=data, headers=headers)

        if response.status_code == 200:
            try:
                response_data = response.json()
                if len(response_data) > 0:
                    return response_data[0].get('score')
            except ValueError:
                return None
        else:
            print(f"请求失败: {response.status_code} - {response.reason}")
        return None
    def process(self, sample):
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
            Param("model_url", DataType.STRING, {}, "https://esupw2o6m6f4.space.opencsg.com/rerank"),
        ]