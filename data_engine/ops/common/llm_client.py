import requests
import json
from typing import List, Dict, Any, Optional


def create_headers(auth_token: str) -> Dict[str, str]:
    """
    Create request headers

    Args:
        auth_token (str): Authentication token

    Returns:
        Dict[str, str]: Request headers dictionary
    """
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }


def create_chat_data(model: str, messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Create chat request data

    Args:
        model (str): Model name
        messages (List[Dict[str, str]]): Messages list

    Returns:
        Dict[str, Any]: Chat request data
    """
    return {
        "model": model,
        "messages": messages,
        "stream": True,
        "temperature": 0.95,
        "max_tokens": 800,
        "top_k": 10,
        "top_p": 0.95,
        "repetition_penalty": 1.0,
    }


def parse_stream_response_line(line: bytes) -> Optional[str]:
    """
    Parse a line of streaming response data

    Args:
        line (bytes): Raw response line data

    Returns:
        Optional[str]: Parsed text content, None if parsing fails
    """
    try:
        decoded_line = line.decode('utf-8')
        # Remove "data:" prefix (Python 3.9+)
        json_str = decoded_line.removeprefix('data:')
        data = json.loads(json_str)

        if ("choices" in data and
                data['choices'][0]['delta'] and
                "content" in data['choices'][0]['delta']):
            return data['choices'][0]['delta']['content']
    except json.JSONDecodeError:
        # JSON parsing failed, return None
        pass
    except Exception:
        # Other exceptions, return None
        pass

    return None


def chat_with_model(url: str, auth_token: str, model: str, messages: List[Dict[str, str]]) -> str:
    """
    Chat with model

    Args:
        url (str): API address
        auth_token (str): Authentication token for API access
        model (str): Model name
        messages (List[Dict[str, str]]): Messages list

    Returns:
        str: Complete response returned by the model

    Raises:
        requests.RequestException: Request exception
    """
    headers = create_headers(auth_token)
    data = create_chat_data(model, messages)

    response = requests.post(url=url, json=data, headers=headers, stream=True)
    response.raise_for_status()

    contents = []
    for line in response.iter_lines():
        if line:
            content = parse_stream_response_line(line)
            if content:
                contents.append(content)

    return ''.join(contents)
