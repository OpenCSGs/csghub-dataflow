import os
import time
from loguru import logger

from data_engine.tools.load import load_tool_cls
from data_server.logic.models import Tool as Tool_def, ExecutedParams

from data_engine.utils.logger_utils import setup_logger 
from data_engine.utils.env import GetRayAddress
from data_engine.tools.base_tool import TOOL
from data_engine.utils.availability_utils import AvailabilityChecking
with AvailabilityChecking(['ray'], requires_type='dist'):
    import ray

class ToolExecutorRay:
    """
    This ToolExecutor class is used to invoke a specific tool.
    it just invoke the tools with the required params from tool, tool will take care everything
    """

    def __init__(self, *, tool_def: Tool_def, params: ExecutedParams):
        """
        Initialization method.

        :param cfg: optional config dict.
        """
        self.tool_def = tool_def
        self.executed_params = params
        logger.info(f'Using user_id={self.executed_params.user_id}, '
                    f'user_name={self.executed_params.user_name}, '
                    f'user_token={"xxxxxx" if self.executed_params.user_token is not None and len(self.executed_params.user_token)>0 else None}')
        
        # setup logger
        log_dir = os.path.join(self.executed_params.work_dir, 'log')
        # log_dir = os.path.join("/Users/zhanglongbin/pythonWork/csghub-dataflow-main/demo/output", 'log')
        
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        timestamp = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
        logfile_name = f'tool_{self.tool_def.name}_time_{timestamp}.txt'
        setup_logger(save_dir=log_dir,
                    filename=logfile_name,
                    level='INFO',
                    redirect=self.tool_def.executor_type == 'default')
        
        ray.init(address=GetRayAddress(), ignore_reinit_error=True)

    def run(self):
        """
        Running the dataset process pipeline.

        :param load_data_np: number of workers when loading the dataset.
        :return: processed dataset.
        """
        # 1. setup tool
        logger.info('Preparing tool...')
        tool_cls_raw: TOOL = load_tool_cls(self.tool_def)
        remote_cls = ray.remote(tool_cls_raw).options(num_cpus=self.tool_def.np)
        remote_obj = remote_cls.remote(self.tool_def, self.executed_params)


        # 1. launch tool
        logger.info('Launching tool...')
        return ray.get(remote_obj.run.remote())

if __name__ == "__main__":
    from data_server.logic.models import Param
    params: list[Param] = []
    # params.append(
    #     Param(name="weights",
    #           value=['0.5', '0.5'])
    # )
    # params.append(
    #     Param(name="max_samples",
    #           value=10)
    # )
    # params.append(
    #     Param(name="template_path",
    #           value="process.yaml")
    # )
    

    tool = Tool_def(
        # name="serialize_meta_preprocess",
        # name="dataset_spliter_by_language_preprocess",
        # name="count_token_postprocess_internal",
        # name="deserialize_meta_postprocess_internal",
        name="prepare_dataset_from_repo_preprocess_internal",
        description="xxx",
        np=2,
        type="Internal",
        repo_id="depenglee/testdepeng",
        branch="main",
        # dataset_path="/Users/zhanglongbin/pythonWork/csghub-dataflow-main/demo/input",
        dataset_path="/home/yons/demo/input",
        # export_path="/Users/zhanglongbin/pythonWork/csghub-dataflow-main/demo/output",
        export_path="/home/yons/demo/output",
        params=params,
    )

    params = ExecutedParams(
        user_id="123",
        user_name="depenglee",
        user_token="ab0033c38611468f8807f2f26013d5d1",
        # work_dir="/Users/zhanglongbin/pythonWork/csghub-dataflow-main/demo/output",
        work_dir="/home/yons/demo/output",
    )

    excutor = ToolExecutorRay(tool_def=tool, params=params)
    print(excutor.run())
