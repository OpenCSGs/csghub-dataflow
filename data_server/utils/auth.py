from typing import Optional
import time
from datetime import datetime, timedelta


_user_tokens = {}
_token_expiry = {}

class TokenExpiredError(Exception):
    """Token已过期异常"""
    pass

class TokenNotFoundError(Exception):
    """Token未找到异常"""
    pass

def set_user_token(username: str, token: str, expiry_seconds: int = 3600) -> None:
    """
    存储用户token并设置过期时间
    Args:
        username: 用户名
        token: 用户认证token
        expiry_seconds: 过期时间(秒)，默认1小时
    """
    global _user_tokens, _token_expiry
    _user_tokens[username] = token
    _token_expiry[username] = datetime.now() + timedelta(seconds=expiry_seconds)

def get_user_token(username: str) -> str:
    """
    获取用户token，如果过期则抛出异常
    Args:
        username: 用户名
    Returns:
        用户token
    Raises:
        TokenNotFoundError: 未找到用户token
        TokenExpiredError: token已过期
    """
    if username not in _user_tokens:
        raise TokenNotFoundError(f"User {username} token not found")
        
    if datetime.now() > _token_expiry.get(username, datetime.min):
        # 清除过期token
        del _user_tokens[username]
        del _token_expiry[username]
        raise TokenExpiredError(f"User {username} token has expired")
        
    return _user_tokens[username]

def clear_user_token(username: str) -> None:
    """清除用户token"""
    global _user_tokens, _token_expiry
    if username in _user_tokens:
        del _user_tokens[username]
    if username in _token_expiry:
        del _token_expiry[username]

def is_token_valid(username: str) -> bool:
    """检查token是否有效"""
    try:
        get_user_token(username)
        return True
    except (TokenNotFoundError, TokenExpiredError):
        return False

# 模拟网页拦截获取token的函数
# 在实际应用中，这部分应该由前端拦截器或后端中间件实现
def intercept_web_token(username: str) -> Optional[str]:
    """
    从指定URL的响应Cookie中提取user_token
    Args:
        username: 用户名
    Returns:
        提取到的user_token或None
    """
    import requests
    from urllib.parse import urljoin
    
    try:
        # 目标URL
        target_url = "http://home.sxcfx.cn:18120/datasets/new"
        
        # 发送GET请求
        response = requests.get(target_url, timeout=10)
        response.raise_for_status()  # 检查HTTP请求是否成功
        
        # 从响应Cookie中提取user_token
        user_token = response.cookies.get('user_token')
        if not user_token:
            raise Exception("响应Cookie中未找到user_token")
        
        # 设置token过期时间（假设24小时）
        set_user_token(username=username, token=user_token, expiry_seconds=86400)
        return user_token
        
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {str(e)}")
    except Exception as e:
        print(f"提取user_token失败: {str(e)}")
    
    return None
    
