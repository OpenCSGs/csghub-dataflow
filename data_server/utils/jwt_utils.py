
from typing import Dict
import base64
import json
from datetime import datetime


class JWTDecodeError(Exception):

    pass


def parse_jwt_token(authorization: str) -> Dict:

    try:

        if not authorization:
            raise JWTDecodeError("Authorization header is missing")

        if not authorization.startswith("Bearer "):
            raise JWTDecodeError("Authorization header must start with 'Bearer '")


        token = authorization[7:].strip()
        if not token:
            raise JWTDecodeError("Token is empty after 'Bearer ' prefix")


        parts = token.split('.')
        if len(parts) != 3:
            raise JWTDecodeError("Invalid JWT format: token must have 3 parts separated by dots")


        header_part = parts[0]
        header_padding = 4 - len(header_part) % 4
        if header_padding != 4:
            header_part += '=' * header_padding
        header_bytes = base64.urlsafe_b64decode(header_part)
        header = json.loads(header_bytes.decode('utf-8'))


        payload_part = parts[1]
        payload_padding = 4 - len(payload_part) % 4
        if payload_padding != 4:
            payload_part += '=' * payload_padding
        payload_bytes = base64.urlsafe_b64decode(payload_part)
        payload = json.loads(payload_bytes.decode('utf-8'))


        signature = parts[2]


        exp_datetime = None
        is_expired = None
        if payload.get("exp"):
            try:
                exp_datetime = datetime.fromtimestamp(payload["exp"])
                is_expired = datetime.now() > exp_datetime
            except (ValueError, OSError):
                pass


        return {
            "header": header,
            "payload": payload,
            "signature": signature,
            "exp_datetime": exp_datetime,
            "is_expired": is_expired
        }

    except json.JSONDecodeError as e:
        raise JWTDecodeError(f"Failed to parse JWT as JSON: {str(e)}")
    except Exception as e:
        if isinstance(e, JWTDecodeError):
            raise
        raise JWTDecodeError(f"Failed to decode JWT token: {str(e)}")

if __name__ == "__main__":

    token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1dWlkIjoib05VOHA2aEMtZ3RxZGZjeTM1VUwtbW11djdRSSIsImN1cnJlbnRfdXNlciI6IkxCV2hpdGU1NSIsImlzcyI6Ik9wZW5DU0ciLCJleHAiOjE3NTM1ODQ0MzN9.9nTj0_YXfXD_5W7MBJvkzpNK4N5zEkodEhWZxsVfvUU"
    print(parse_jwt_token(token))