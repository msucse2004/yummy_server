"""업로드 파일 서빙 - 완료 사진"""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse

from app.config import get_settings
from app.core.auth import require_user
from app.database import get_db
from app.models import User, Photo

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


@router.get("/photo/{photo_id}")
def get_photo(
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """완료 사진 다운로드 (인증 필요)"""
    photo = db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="사진을 찾을 수 없습니다")
    settings = get_settings()
    full_path = Path(settings.upload_dir) / photo.file_path
    if not full_path.exists():
        raise HTTPException(status_code=404, detail="파일이 존재하지 않습니다")
    return FileResponse(full_path, filename=photo.filename or "photo.jpg")
