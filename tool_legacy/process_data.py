from loguru import logger

from data_engine.config import init_configs
from data_engine.core import Executor
from data_engine._telemetry import TRACE_HELPER

@logger.catch(reraise=True)
def main():
    cfg = init_configs()
    with TRACE_HELPER.trace_block(
        operation="start"
    ):
        if cfg.executor_type == 'default':
            executor = Executor(cfg)
        elif cfg.executor_type == 'ray':
            from data_engine.core.ray_executor import RayExecutor
            executor = RayExecutor(cfg)
        executor.run()


if __name__ == '__main__':
    main()
