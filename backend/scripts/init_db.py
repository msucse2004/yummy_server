"""초기 DB 설정 - admin 사용자 생성 (마이그레이션 후 실행)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import SessionLocal
from app.models import User
from app.models.user import Role
from app.core.security import hash_password


def main():
    db = SessionLocal()
    try:
        existing = db.execute(select(User).where(User.username == "admin")).scalar_one_or_none()
        if existing:
            print("admin 사용자가 이미 존재합니다.")
            return
        admin = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role=Role.ADMIN,
            display_name="관리자",
        )
        db.add(admin)
        db.commit()
        print("admin 사용자 생성 완료 (비밀번호: admin123)")
    finally:
        db.close()


if __name__ == "__main__":
    main()
