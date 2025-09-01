from typing import List, Optional, Union, Dict, Any

import faiss
import numpy as np
from datasets import Dataset
from pydantic import Field
import requests

from ..base_op import OPERATORS, Sample, Selector,Param,DataType


OP_NAME = 'encode_and_get_nearest_mapper'
# 编码为嵌入向量
def get_embeddings(texts: List[str], model_url):
    """
    Call API service to get text embeddings

    Args:
        texts (List[str]): List of texts to encode
        model_url (str): API address, defaults to hardcoded address

    Returns:
        List[List[float]]: List of embedding vectors

    Raises:
        requests.RequestException: Raised when network request fails
    """

    # Send request to TEI server
    payload = {
        "inputs": texts,
        "normalize": True
    }
    try:
        response = requests.post(model_url, json=payload)
        response.raise_for_status()  # Raise exception for HTTP errors
        embeddings = response.json()  # List of embeddings
    except requests.RequestException as e:
        raise requests.RequestException(f"Error calling API: {e}")
    return embeddings

def encode_texts(texts: List[str], model_url) -> List[List[float]]:
    """
    Encode multiple texts into embedding vectors

    Args:
        texts (List[str]): List of texts to encode
        url (str): API address

    Returns:
        List[List[float]]: List of embedding vectors
    """
    return get_embeddings(texts, model_url=model_url)


class FaissNearestNeighbour:
    device: Optional[Union[int, List[int]]] = Field(
        default=None,
        description="The CUDA device ID or a list of IDs to be used. If negative integer,"
        " it will use all the available GPUs.",
    )
    string_factory: Optional[str] = Field(
        default=None,
        description="The name of the factory to be used to build the `faiss` index."
        "Available string factories can be checked here: https://github.com/facebookresearch/faiss/wiki/Faiss-indexes.",
    )
    metric_type: Optional[int] = Field(
        default=None,
        description="The metric to be used to measure the distance between the points. It's"
        " an integer and the recommend way to pass it is importing `faiss` and thenpassing"
        " one of `faiss.METRIC_x` variables.",
    )
    k: Optional[int] = Field(
        default=1,
        description="The number of nearest neighbours to search for each input row.",
    )
    search_batch_size: Optional[int] = Field(
        default=50,
        description="The number of rows to include in a search batch. The value can be adjusted"
        " to maximize the resources usage or to avoid OOM issues.",
    )
    train_size: Optional[int] = Field(
        default=None,
        description="If the index needs a training step, specifies how many vectors will be used to train the index.",
    )
    def _build_index(self, inputs: List[Dict[str, Any]]) -> Dataset:
        """Builds a `faiss` index using `datasets` integration.

        Args:
            inputs: a list of dictionaries.

        Returns:
            The build `datasets.Dataset` with its `faiss` index.
        """
        dataset = Dataset.from_pandas(inputs)

        dataset.add_faiss_index(
            column="embedding",
            device=self.device,  # type: ignore
            string_factory=self.string_factory,
            metric_type=self.metric_type,
            train_size=self.train_size,
        )
        return dataset

    def _save_index(self, dataset: Dataset) -> None:
        """Save the generated Faiss index as an artifact of the step.

        Args:
            dataset: the dataset with the `faiss` index built.
        """
        self.save_artifact(
            name="faiss_index",
            write_function=lambda path: dataset.save_faiss_index(
                index_name="embedding", file=path / "index.faiss"
            ),
            metadata={
                "num_rows": len(dataset),
                "embedding_dim": len(dataset[0]["embedding"]),
            },
        )

    def _search(self, dataset: Dataset) -> Dataset:
        """Search the top `k` nearest neighbours for each row in the dataset.

        Args:
            dataset: the dataset with the `faiss` index built.

        Returns:
            The updated dataset containing the top `k` nearest neighbours for each row,
            as well as the score or distance.
        """

        def add_search_results(examples: Dict[str, List[Any]]) -> Dict[str, List[Any]]:
            queries = np.array(examples["embedding"])
            results = dataset.search_batch(
                index_name="embedding",
                queries=queries,
                k=self.k + 1,  # type: ignore
            )
            examples["nn_indices"] = [indices[1:] for indices in results.total_indices]
            examples["nn_scores"] = [scores[1:] for scores in results.total_scores]
            return examples

        return dataset.map(
            add_search_results, batched=True, batch_size=self.search_batch_size,desc="Searching nearest neighbours"
        )

    def process(self, inputs) -> "StepOutput":  # type: ignore
        dataset = self._build_index(inputs)
        dataset_with_search_results = self._search(dataset)
        #self._save_index(dataset)
        return dataset_with_search_results


@OPERATORS.register_module(OP_NAME)
class EncodeAndGetNearestSelector(Selector):
    """Encode texts and find nearest neighbours using Faiss."""

    def __init__(self,
                 model_url: str = "https://ev19h0o3sv7k.space.opencsg.com/embed",
                 *args,
                 **kwargs):
        """
        Initialization method.

        :param args: extra args
        :param kwargs: extra args
        """
        super().__init__(*args, **kwargs)
        self.first_prompt = []
        self.model_url = model_url

    def process(self, dataset):
        if len(dataset) <= 0:
            return dataset
        dataset = dataset.to_pandas()

        first_prompt_list = dataset["first_prompt"].tolist()

        embeddings = encode_texts(first_prompt_list,self.model_url)
        dataset['embedding'] = embeddings

        nearest_neighbour = FaissNearestNeighbour()
        nearest_neighbour.device = None
        nearest_neighbour.metric_type = faiss.METRIC_INNER_PRODUCT
        nearest_neighbour.k = 5
        nearest_neighbour.string_factory = "Flat"
        nearest_neighbour.train_size = None
        nearest_neighbour.search_batch_size = 100

        return nearest_neighbour.process(dataset)

    @classmethod
    @property
    def description(cls):
        return "Encode texts and find nearest neighbours using Faiss."

    @classmethod
    @property
    def sample(cls):
        return Sample(
            before="数据集包含first_prompt字段的文本数据，"
                   "如['What is artificial intelligence?', 'How does machine learning work?']",
            after="数据集增加了embedding、nn_indices和nn_scores字段，包含文本的向量表示和最近邻信息"
        )

    @classmethod
    @property
    def init_params(cls):
        return [
            Param("model_url", DataType.STRING, {}, "https://ev19h0o3sv7k.space.opencsg.com/embed"),
        ]
