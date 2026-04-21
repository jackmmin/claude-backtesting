import jwt
import uuid
import hashlib


def get_auth_headers(access_key, secret_key, query_string=""):
    """업비트 인증 헤더 생성 (JWT)"""
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
    }
    if query_string:
        payload["query_hash"] = hashlib.sha512(query_string.encode()).hexdigest()
        payload["query_hash_alg"] = "SHA512"
    token = jwt.encode(payload, secret_key, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
