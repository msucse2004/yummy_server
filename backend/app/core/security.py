"""비밀번호 해시 (plain 저장 금지)"""
import secrets
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


def hash_password(plain: str) -> str:
    """평문 비밀번호를 해시"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain, hashed)


def generate_session_id() -> str:
    """세션 ID 생성 (암호학적으로 안전)"""
    return secrets.token_urlsafe(32)
