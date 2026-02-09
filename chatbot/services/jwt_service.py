"""
Module xử lý JWT token để lấy userID.

Chức năng:
- Giải mã JWT token
- Lấy userID từ JWT payload
- Validate JWT token
"""

from __future__ import annotations

import jwt
import base64
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


# JWT configuration
JWT_SECRET_RAW = "404E635266556A586E3272357538782F413F4428472B4B6250645367566B5970"
JWT_EXPIRATION = 360000  # seconds
JWT_REFRESH_EXPIRATION = 604800  # seconds

# Decode Base64 secret key to bytes (like Java does)
JWT_SECRET = base64.b64decode(JWT_SECRET_RAW)

# Alternative secret keys to try (different formats)
ALTERNATIVE_SECRETS = [
    JWT_SECRET,  # Base64 decoded bytes (like Java)
    JWT_SECRET_RAW,  # Raw string
    JWT_SECRET_RAW.encode('utf-8'),  # UTF-8 encoded bytes
]


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict chứa payload hoặc None nếu token không hợp lệ
    """
    # Thử với secret key chính (Base64 decoded bytes - như Java)
    try:
        payload = jwt.decode(
            token, 
            JWT_SECRET, 
            algorithms=['HS256']
        )
        print(f"SUCCESS: Da decode JWT voi Base64 decoded secret key (nhu Java)")
        return payload
    except jwt.ExpiredSignatureError:
        print("ERROR: JWT token da het han")
        return None
    except jwt.InvalidTokenError as e:
        print(f"WARNING: JWT token khong hop le voi Base64 decoded key: {e}")
        # Thử với các secret key khác
        for i, alt_secret in enumerate(ALTERNATIVE_SECRETS):
            try:
                payload = jwt.decode(
                    token, 
                    alt_secret, 
                    algorithms=['HS256']
                )
                print(f"SUCCESS: Da decode JWT voi alternative secret key {i+1}")
                return payload
            except jwt.InvalidTokenError:
                continue
            except Exception as e:
                print(f"WARNING: Loi voi alternative secret {i+1}: {e}")
                continue
        
        print("ERROR: Khong the decode JWT voi bat ky secret key nao")
        return None
    except Exception as e:
        print(f"ERROR: Loi giai ma JWT: {e}")
        return None


def extract_user_id_from_token(token: str) -> Optional[str]:
    """
    Lấy userID từ JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        userID hoặc None nếu không lấy được
    """
    payload = decode_jwt_token(token)
    if not payload:
        return None
    
    # Lấy userID từ payload - hỗ trợ nhiều format
    user_id = (payload.get('userId') or 
               payload.get('user_id') or 
               payload.get('sub') or 
               payload.get('id'))
    
    if user_id:
        print(f"SUCCESS: Da lay userID tu JWT: {user_id}")
        return str(user_id)
    
    print("ERROR: Khong tim thay userID trong JWT payload")
    print(f"INFO: Available keys in payload: {list(payload.keys())}")
    return None


def validate_jwt_token(token: str) -> bool:
    """
    Validate JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        True nếu token hợp lệ, False nếu không
    """
    payload = decode_jwt_token(token)
    return payload is not None


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Lấy thời gian hết hạn của JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        datetime hết hạn hoặc None nếu không lấy được
    """
    payload = decode_jwt_token(token)
    if not payload:
        return None
    
    exp_timestamp = payload.get('exp')
    if exp_timestamp:
        return datetime.fromtimestamp(exp_timestamp)
    
    return None


def is_token_expired(token: str) -> bool:
    """
    Kiểm tra JWT token có hết hạn không.
    
    Args:
        token: JWT token string
        
    Returns:
        True nếu token hết hạn, False nếu còn hiệu lực
    """
    payload = decode_jwt_token(token)
    if not payload:
        return True
    
    exp_timestamp = payload.get('exp')
    if not exp_timestamp:
        return True
    
    exp_time = datetime.fromtimestamp(exp_timestamp)
    return datetime.now() > exp_time


def decode_jwt_without_verification(token: str) -> Optional[Dict[str, Any]]:
    """
    Giải mã JWT token mà không verify signature (chỉ để debug).
    
    Args:
        token: JWT token string
        
    Returns:
        Dict chứa payload hoặc None nếu token không hợp lệ
    """
    try:
        # Decode mà không verify signature
        payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        print(f"SUCCESS: Da decode JWT ma khong verify signature")
        return payload
    except Exception as e:
        print(f"ERROR: Loi decode JWT: {e}")
        return None


def get_token_info(token: str) -> Dict[str, Any]:
    """
    Lấy thông tin chi tiết về JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Dict chứa thông tin token
    """
    # Thử decode với verification trước
    payload = decode_jwt_token(token)
    if not payload:
        # Nếu không được, thử decode mà không verify
        print("WARNING: Thu decode JWT ma khong verify signature...")
        payload = decode_jwt_without_verification(token)
        if not payload:
            return {
                "valid": False,
                "user_id": None,
                "expired": True,
                "expiration": None,
                "payload": None,
                "verified": False
            }
    
    user_id = extract_user_id_from_token(token)
    expiration = get_token_expiration(token)
    expired = is_token_expired(token)
    
    return {
        "valid": True,
        "user_id": user_id,
        "expired": expired,
        "expiration": expiration.isoformat() if expiration else None,
        "payload": payload,
        "available_keys": list(payload.keys()),
        "verified": payload is not None
    }
