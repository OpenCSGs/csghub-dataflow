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
        latestNum = 0
        for b in valid_branches:
            if origin_branch == "main" and re.match(r"^v\d+", b):
                numStr = b.split(".")[0][1:]
                if numStr.isdigit():
                    num = int(numStr)
                    latestNum = max(latestNum, num)
            elif b.startswith(origin_branch) and len(b) > len(origin_branch):
                numStr = b[len(origin_branch)+1:]
                if numStr.isdigit():
                    num = int(numStr)
                    latestNum = max(latestNum, num)

        if origin_branch == "main":
            return f"v{latestNum + 1}" if latestNum > 0 else "v1"
        else:
            return f"{origin_branch}.{latestNum + 1}" if latestNum > 0 else f"{origin_branch}.1"
        
