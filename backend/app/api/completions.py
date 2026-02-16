"""기사 완료/사진 업로드 - DRIVER는 배정된 스탑만 완료 가능"""
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.api.stops import add_arrears_for_completed_stop
from app.config import get_settings
from app.core.auth import require_user
from app.core.route_access import require_route_access
from app.database import get_db
from app.models import User, Stop, StopCompletion, Photo, Route, StopOrderItem
from app.schemas.completion import CompletionCreate, CompletionResponse, PhotoResponse

router = APIRouter(prefix="/api/completions", tags=["completions"])


def _get_stop_with_route(db: Session, stop_id: int) -> Stop | None:
    return db.get(
        Stop,
        stop_id,
        options=[
            joinedload(Stop.route).joinedload(Route.assignments),
            joinedload(Stop.order_items).joinedload(StopOrderItem.item),
            joinedload(Stop.customer),
            joinedload(Stop.completions).joinedload(StopCompletion.photos),
        ],
    )


@router.post("/stop/{stop_id}", response_model=CompletionResponse, status_code=status.HTTP_201_CREATED)
async def complete_stop(
    stop_id: int,
    memo: str | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """스탑 완료 처리 - 기사는 배정된 루트의 스탑만 완료 가능"""
    stop = _get_stop_with_route(db, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    require_route_access(current_user, stop.route)
    if stop.completions:
        raise HTTPException(status_code=400, detail="이미 완료된 스탑입니다")
    completion = StopCompletion(
        stop_id=stop_id,
        completed_by_user_id=current_user.id,
        memo=memo,
    )
    db.add(completion)
    add_arrears_for_completed_stop(db, stop)
    db.commit()
    db.refresh(completion)
    return completion


@router.post("/stop/{stop_id}/photos", response_model=list[PhotoResponse])
async def upload_photos(
    stop_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """완료 사진 업로드 - 먼저 complete_stop 호출 필요"""
    stop = _get_stop_with_route(db, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    require_route_access(current_user, stop.route)
    completion = stop.completions[0] if stop.completions else None
    if not completion:
        raise HTTPException(status_code=400, detail="먼저 스탑을 완료해 주세요")
    settings = get_settings()
    upload_path = Path(settings.upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)
    allowed = {"image/jpeg", "image/png", "image/webp"}
    photos = []
    for f in files:
        if f.content_type not in allowed:
            raise HTTPException(status_code=400, detail=f"{f.filename}: 이미지 파일만 업로드 가능합니다")
        ext = Path(f.filename or "img").suffix or ".jpg"
        name = f"{uuid.uuid4().hex}{ext}"
        rel = f"completion_{completion.id}"
        dest = upload_path / rel
        dest.mkdir(parents=True, exist_ok=True)
        filepath = dest / name
        content = await f.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"{f.filename}: 10MB 이하여야 합니다")
        filepath.write_bytes(content)
        stored = str(Path(rel) / name)
        photo = Photo(completion_id=completion.id, file_path=stored, filename=f.filename)
        db.add(photo)
        photos.append(photo)
    db.commit()
    for p in photos:
        db.refresh(p)
    return photos


@router.get("/stop/{stop_id}", response_model=CompletionResponse | None)
def get_completion(
    stop_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_user),
):
    stop = _get_stop_with_route(db, stop_id)
    if not stop:
        raise HTTPException(status_code=404, detail="스탑을 찾을 수 없습니다")
    require_route_access(current_user, stop.route)
    return stop.completions[0] if stop.completions else None
