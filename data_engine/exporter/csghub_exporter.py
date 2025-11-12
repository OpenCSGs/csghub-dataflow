import traceback
from typing import List
import os
import re

from pycsghub.cmd.repo_types import RepoType
from pycsghub.upload_large_folder.main import upload_large_folder_internal

from data_engine.exporter.base_exporter import Exporter
from loguru import logger
from pycsghub.repository import Repository
from pycsghub.utils import (build_csg_headers,
                            model_id_to_group_owner_name,
                            get_endpoint,
                            REPO_TYPE_DATASET)
from data_engine.utils.env import GetHubEndpoint
import shutil
import requests
from pathlib import Path

DEFAULT_TARGET_PATH = "/tmp"


class ExporterCSGHUB(Exporter):
    def __init__(
            self,
            export_path,
            export_shard_size=0,
            export_in_parallel=True,
            num_proc=1,
            export_ds=True,
            keep_stats_in_res_ds=False,
            keep_hashes_in_res_ds=False,
            export_stats=True,
            repo_id: str = None,
            branch: str = None,
            user_name: str = None,
            user_token: str = None,
            work_dir: str = None,
            path_is_dir: bool = False,
            auto_version: bool = False,
    ):
        """
        Initialization method.
        :param export_path: the path to export datasets.
        :param export_shard_size: the size of each shard of exported
            dataset. In default, it's 0, which means export the dataset
            to a single file.
        :param num_proc: number of process to export the dataset.
        :param export_ds: whether to export the dataset contents.
        :param keep_stats_in_res_ds: whether to keep stats in the result
            dataset.
        :param keep_hashes_in_res_ds: whether to keep hashes in the result
            dataset.
        :param export_stats: whether to export the stats of dataset.
        """
        if Path(export_path).is_dir() and not path_is_dir:
            export_path = os.path.join(export_path, "x.jsonl")

        self.csghub_path = export_path
        # decide to use jsonl format, it's not required, candidates are ["jsonl", "json", "parquet"]
        # self.target_path = os.path.join(DEFAULT_TARGET_PATH, str(uuid.uuid4()) + '.jsonl')
        self.repo_id = repo_id
        self.branch = branch
        self.user_name = user_name
        self.user_token = user_token
        self.work_dir = work_dir
        self.auto_version = auto_version  # True for pipeline jobs, False for formatify tasks
        super().__init__(
            export_path=export_path,
            export_shard_size=export_shard_size,
            export_in_parallel=export_in_parallel,
            num_proc=num_proc,
            export_ds=export_ds,
            keep_stats_in_res_ds=keep_stats_in_res_ds,
            keep_hashes_in_res_ds=keep_hashes_in_res_ds,
            export_stats=export_stats,
            repo_id=repo_id,
            branch=branch,
            user_name=user_name,
            user_token=user_token,
            work_dir=work_dir,
            path_is_dir=path_is_dir
        )

    def export_from_files(self, upload_path: Path):
        """
        Export method for dir with files.

        :param upload_path: path with files need to upload.
        :return:
        """
        if not os.path.exists(upload_path) or len(os.listdir(upload_path)) == 0:
            logger.info(f'The target dir is empty, no need to upload anything, abort.')
            return None
        self.upload_path = str(upload_path)
        logger.info(f'Start to upload {upload_path} to repo: {self.repo_id} with branch: {self.branch}')
        self.repo_work_dir = os.path.join(self.work_dir, "_git")
        self._export_common()
        return self.output_branch_name

    def export_large_folder(self):
        try:
            if self.branch is None:
                self.branch = 'main'
                self.branch = self.get_avai_branch(self.branch)
            logger.info(f'Start to upload {self.export_path} to repo: {self.repo_id} with branch: {self.branch}')
            upload_large_folder_internal(
                repo_id=self.repo_id,
                local_path=self.export_path,
                repo_type=RepoType.DATASET,
                revision=self.branch,
                endpoint=get_endpoint(endpoint=GetHubEndpoint()),
                token=self.user_token,
                num_workers=1,
                print_report=False,
                print_report_every=1,
                allow_patterns=None,
                ignore_patterns=None
            )
        except Exception as e:
            traceback.print_exc()

    def export(self, dataset):
        """
        Export method for a dataset.

        :param dataset: the dataset to export.
        :return:
        """
        self._export_impl(dataset, self.export_path, self.suffix, self.export_stats)
        self.upload_path = os.path.join(self.work_dir, "_data")
        self.repo_work_dir = os.path.join(self.work_dir, "_git")
        self._export_common()
        return self.output_branch_name

    def _export_common(self):
        """
        Common export method for repo.
        :return:
        """
        if self.repo_id is not None and len(self.repo_id) > 0:
            # check available correct branch name
            self.output_branch_name = self.get_avai_branch(self.branch)
            # push to csghub with new branch, the files in self.csghub_path
            if not os.path.exists(self.upload_path):
                os.makedirs(self.upload_path, exist_ok=True)
            if not os.path.exists(self.repo_work_dir):
                os.makedirs(self.repo_work_dir, exist_ok=True)
            logger.info(
                f'Start to push {self.upload_path} to repo: {self.repo_id} with branch: {self.output_branch_name},user_name: {self.user_name}, token: {self.user_token}')
            r = Repository(
                repo_id=self.repo_id,
                upload_path=self.upload_path,
                branch_name=self.output_branch_name,
                user_name=self.user_name,
                token=self.user_token,
                repo_type=REPO_TYPE_DATASET,
                endpoint=get_endpoint(endpoint=GetHubEndpoint()),
                work_dir=self.work_dir
            )
            r.upload()
            logger.info(f'Done push {self.upload_path} to repo: {self.repo_id} with branch: {self.output_branch_name}')
            #insert_pipline_job_run_task_log_info(job_uid, f'Done push {self.upload_path} to repo: {self.repo_id} with branch: {self.output_branch_name}')
            if os.path.exists(self.repo_work_dir):
                logger.info(f'Remove {self.repo_work_dir}')
                shutil.rmtree(self.repo_work_dir)
            if os.path.exists(self.upload_path):
                logger.info(f'Remove {self.upload_path}')
                shutil.rmtree(self.upload_path)
        else:
            self.output_branch_name = 'N/A'

    def get_avai_branch(self, origin_branch: str) -> str:
        action_endpoint = get_endpoint(endpoint=GetHubEndpoint())
        url = f"{action_endpoint}/api/v1/datasets/{self.repo_id}/branches"
        headers = build_csg_headers(
            token=self.user_token,
            headers={"Content-Type": "application/json"}
        )
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError(f"cannot request repo {self.repo_id} branches")

        jsonRes = response.json()
        if jsonRes["msg"] != "OK":
            raise ValueError(f"cannot read repo {self.repo_id} branches")

        branches = jsonRes["data"]
        valid_branches = []
        for b in branches:
            valid_branches.append(b['name'])

        # valid_branches = ["main", "v3.1", "v1.11", "v1.5", "v2", "v1", "v1.2", "v1.11.2"]            
        valid_branches.sort()
        logger.info(f'repo {self.repo_id} all branches: {valid_branches}')
        result = self.find_next_version(origin_branch=origin_branch, valid_branches=valid_branches)
        return result

    def find_next_version(self, origin_branch: str, valid_branches: List):
        """
        根据任务类型选择版本生成逻辑：
        - auto_version=False (文件转换任务): 直接返回用户指定的分支名
        - auto_version=True (算子执行任务): 自动生成版本号 (v1, v2, ...)
        """
        if not self.auto_version:
            # 文件转换任务：直接返回用户指定的分支名
            if origin_branch in valid_branches:
                return origin_branch
            return origin_branch
        
        # 算子执行任务：自动生成版本号
        latestNum = 0
        
        for b in valid_branches:
            if origin_branch == "main" and re.match(r"^v\d+", b):
                # 处理 main 分支的情况，查找 v1, v2, v3 等
                numStr = b.split(".")[0][1:]
                if not numStr.isdigit():
                    continue
                num = int(numStr)
                latestNum = max(latestNum, num)
            elif b.startswith(origin_branch) and len(b) > len(origin_branch):
                # 处理其他分支的情况，查找 origin_branch.1, origin_branch.2 等
                numStr = b[len(origin_branch) + 1:]
                if not numStr.isdigit():
                    continue
                num = int(numStr)
                latestNum = max(latestNum, num)
            else:
                continue
        
        if origin_branch == "main":
            if latestNum > 0:
                return "v" + str(latestNum + 1)
            else:
                return "v1"
        else:
            if latestNum > 0:
                return origin_branch + "." + str(latestNum + 1)
            else:
                return origin_branch + ".1"
