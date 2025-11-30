from typing import List
import requests
from loguru import logger
import re
from pycsghub.utils import build_csg_headers, get_endpoint
import os

class BranchTool:
    def __init__(self, repo_id: str, user_token: str):
        self.repo_id = repo_id
        self.user_token = user_token
        
    def get_avai_branch(self, origin_branch: str) -> str:
        try:
            action_endpoint = get_endpoint(os.getenv("CSGHUB_ENDPOINT"))
            url = f"{action_endpoint}/api/v1/datasets/{self.repo_id}/branches"
            headers = build_csg_headers(
                token=self.user_token,
                headers={"Content-Type": "application/json"}
            )
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            jsonRes = response.json()
            if jsonRes["msg"] != "OK":
                raise ValueError(f"cannot read repo {self.repo_id} branches")

            branches = jsonRes["data"]
            valid_branches = [b['name'] for b in branches]
            valid_branches.sort()
            
            logger.info(f'repo {self.repo_id} all branches: {valid_branches}')
            return self.find_next_version(origin_branch, valid_branches)
        except Exception as e:
            logger.error(f"Error getting branch name: {e}")
            raise

    def find_next_version(self, origin_branch: str, valid_branches: List) -> str:
        """
        算子执行任务的版本生成逻辑：自动生成 v1, v2 等版本号
        """
        latestNum = 0
        
        for b in valid_branches:
            if origin_branch == "main" and re.match(r"^v\d+", b):
                # Handle main branch case, find v1, v2, v3, etc.
                numStr = b.split(".")[0][1:]
                if not numStr.isdigit():
                    continue
                num = int(numStr)
                latestNum = max(latestNum, num)
            elif b.startswith(origin_branch) and len(b) > len(origin_branch):
                # Handle other branch cases, find origin_branch.1, origin_branch.2, etc.
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
        
