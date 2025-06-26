import data_engine.tools.legacies.data_mixture as legacy

from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, ExecutedParams
from pathlib import Path

TOOL_NAME = 'data_mixture_postprocess_internal'


@TOOLS.register_module(TOOL_NAME)
class DataMixture(TOOL):
    """
    Mix multiple datasets into one dataset.
    Randomly select samples from every dataset and mix theses
    samples, then export to a new mixed dataset
    """

    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.weights = next(
            (item.value for item in self.tool_def.params if item.name == "weights"), None)
        self.max_samples = next(
            (item.value for item in self.tool_def.params if item.name == "max_samples"), None)

    def process(self):
        target_path = legacy.main(data_path=self.tool_def.dataset_path,
                                  export_path=self.tool_def.export_path,
                                  weights=self.weights,
                                  max_samples=self.max_samples,
                                  num_proc=self.tool_def.np)

        return Path(target_path) if target_path else Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        Mix multiple datasets into one dataset.
        Randomly select samples from every dataset and mix theses
        samples, then export to a new mixed dataset
        Supported suffixes include: ["jsonl", "json", "parquet"]
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):
        return [
            Param("weights", DataType.LIST, None, []),
            Param("max_samples", DataType.INTEGER, None, None),
        ]
