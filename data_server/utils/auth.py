from typing import Optional
import time
from datetime import datetime, timedelta


_user_tokens = {}
_token_expiry = {}

class TokenExpiredError(Exception):

    pass

class TokenNotFoundError(Exception):

    pass

def set_user_token(username: str, token: str, expiry_seconds: int = 3600) -> None:

    global _user_tokens, _token_expiry
    _user_tokens[username] = token
    _token_expiry[username] = datetime.now() + timedelta(seconds=expiry_seconds)

def get_user_token(username: str) -> str:

    if username not in _user_tokens:
        raise TokenNotFoundError(f"User {username} token not found")
        
    if datetime.now() > _token_expiry.get(username, datetime.min):

        del _user_tokens[username]
        del _token_expiry[username]
        raise TokenExpiredError(f"User {username} token has expired")
        
    return _user_tokens[username]

def clear_user_token(username: str) -> None:

    global _user_tokens, _token_expiry
    if username in _user_tokens:
        del _user_tokens[username]
    if username in _token_expiry:
        del _token_expiry[username]

def is_token_valid(username: str) -> bool:

    try:
        get_user_token(username)
        return True
    except (TokenNotFoundError, TokenExpiredError):
        return False



def intercept_web_token(username: str) -> Optional[str]:

    import requests
    from urllib.parse import urljoin
    
    try:

        target_url = "http://home.sxcfx.cn:18120/datasets/new"
        

        response = requests.get(target_url, timeout=10)
        response.raise_for_status()
        

        user_token = response.cookies.get('user_token')
        if not user_token:
            raise Exception("响应Cookie中未找到user_token")
        

        set_user_token(username=username, token=user_token, expiry_seconds=86400)
        return user_token
        
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {str(e)}")
    except Exception as e:
        print(f"提取user_token失败: {str(e)}")
    
    return None
    
