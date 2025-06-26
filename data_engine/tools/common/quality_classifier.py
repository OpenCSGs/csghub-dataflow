import data_engine.tools.legacies.quality_classifier.predict as legacy
from data_engine.ops.base_op import Param, DataType
from ..base_tool import TOOL, TOOLS
from data_server.logic.models import Tool as Tool_def, Recipe, ExecutedParams
from pathlib import Path

TOOL_NAME = "quality_classifier_common_internal"

@TOOLS.register_module(TOOL_NAME)
class QualityClassifier(TOOL):
    """
    Use specific quality classifier to predict document scores on dataset
    """
    def __init__(self, tool_defination: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param suffixes: files with suffixes to be loaded, default None
        """
        super().__init__(tool_defination, params)
        self.text_key = next((item.value for item in self.tool_def.params if item.name == "text_key"), None)

    def process(self):
        legacy.predict_score(
            dataset_path=self.tool_def.dataset_path,
            result_path=self.tool_def.export_path,
            text_key=self.text_key
        )
        return Path(self.tool_def.export_path)

    @classmethod
    @property
    def description(cls):
        return """
        This Quality Classifier class is used to predict document scores on dataset.

        It will compute scores for all rows, and give 2 columns score and should_keep for each row to help user decide which row should be removed. By default mark row as should_keep=1 if score is higher than 0.9.
        """

    @classmethod
    def init_params(cls, userid: str = None, isadmin: bool = False):    
        return [
            Param("text_key", DataType.STRING, None, None),
        ]
