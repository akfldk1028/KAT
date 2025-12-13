"""
시크릿 메시지 API 라우터
- 생성, 조회, 만료 처리, 시간 연장
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid

from ..database import get_db
from ..models import SecretMessage

router = APIRouter()


# === Pydantic Schemas ===

class SecretMessageCreate(BaseModel):
    """시크릿 메시지 생성 요청"""
    room_id: int
    sender_id: int
    message: str
    message_type: str = "text"
    image_url: Optional[str] = None
    expiry_seconds: int = 60  # 기본 1분, 테스트용 10초 가능
    require_auth: bool = False
    prevent_capture: bool = True


class SecretMessageResponse(BaseModel):
    """시크릿 메시지 응답"""
    secret_id: str
    room_id: int
    sender_id: int
    message_type: str
    expiry_seconds: int
    require_auth: bool
    prevent_capture: bool
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


class SecretMessageContent(BaseModel):
    """시크릿 메시지 내용 (열람 시)"""
    secret_id: str
    message: str
    message_type: str
    image_url: Optional[str] = None
    is_expired: bool
    prevent_capture: bool
    remaining_seconds: int


# === API Endpoints ===

@router.post("/create", response_model=SecretMessageResponse)
def create_secret_message(
    request: SecretMessageCreate,
    db: Session = Depends(get_db)
):
    """
    시크릿 메시지 생성
    - UUID 기반 secret_id 생성
    - 만료 시각 계산
    """
    secret_id = str(uuid.uuid4())
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=request.expiry_seconds)

    secret_msg = SecretMessage(
        secret_id=secret_id,
        room_id=request.room_id,
        sender_id=request.sender_id,
        original_message=request.message,
        message_type=request.message_type,
        image_url=request.image_url,
        expiry_seconds=request.expiry_seconds,
        require_auth=request.require_auth,
        prevent_capture=request.prevent_capture,
        created_at=now,
        expires_at=expires_at
    )

    db.add(secret_msg)
    db.commit()
    db.refresh(secret_msg)

    return SecretMessageResponse(
        secret_id=secret_msg.secret_id,
        room_id=secret_msg.room_id,
        sender_id=secret_msg.sender_id,
        message_type=secret_msg.message_type,
        expiry_seconds=secret_msg.expiry_seconds,
        require_auth=secret_msg.require_auth,
        prevent_capture=secret_msg.prevent_capture,
        created_at=secret_msg.created_at,
        expires_at=secret_msg.expires_at
    )


@router.get("/view/{secret_id}", response_model=SecretMessageContent)
def view_secret_message(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """
    시크릿 메시지 열람
    - 만료 여부 확인
    - 첫 열람 시 viewed_at 기록
    """
    secret_msg = db.query(SecretMessage).filter(
        SecretMessage.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    now = datetime.utcnow()

    # 만료 체크
    if now > secret_msg.expires_at or secret_msg.is_expired:
        # 만료된 메시지
        if not secret_msg.is_expired:
            secret_msg.is_expired = True
            db.commit()

        return SecretMessageContent(
            secret_id=secret_id,
            message="[만료된 메시지입니다]",
            message_type="text",
            image_url=None,
            is_expired=True,
            prevent_capture=secret_msg.prevent_capture,
            remaining_seconds=0
        )

    # 첫 열람 기록
    if not secret_msg.is_viewed:
        secret_msg.is_viewed = True
        secret_msg.viewed_at = now
        db.commit()

    # 남은 시간 계산
    remaining = (secret_msg.expires_at - now).total_seconds()
    remaining_seconds = max(0, int(remaining))

    return SecretMessageContent(
        secret_id=secret_id,
        message=secret_msg.original_message,
        message_type=secret_msg.message_type,
        image_url=secret_msg.image_url,
        is_expired=False,
        prevent_capture=secret_msg.prevent_capture,
        remaining_seconds=remaining_seconds
    )


@router.delete("/expire/{secret_id}")
def expire_secret_message(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 수동 만료 (발신자가 직접 삭제)"""
    secret_msg = db.query(SecretMessage).filter(
        SecretMessage.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    secret_msg.is_expired = True
    secret_msg.original_message = "[삭제된 메시지]"
    db.commit()

    return {"status": "expired", "secret_id": secret_id}


class ExtendRequest(BaseModel):
    """시간 연장 요청"""
    additional_seconds: int  # 추가할 시간 (초)


@router.put("/extend/{secret_id}")
def extend_secret_message(
    secret_id: str,
    request: ExtendRequest,
    db: Session = Depends(get_db)
):
    """
    시크릿 메시지 시간 연장 (발신자용)
    - 만료 전에만 가능
    - 최대 1시간까지 연장 가능
    """
    secret_msg = db.query(SecretMessage).filter(
        SecretMessage.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    now = datetime.utcnow()

    # 이미 만료된 경우
    if now > secret_msg.expires_at or secret_msg.is_expired:
        raise HTTPException(status_code=400, detail="이미 만료된 메시지입니다")

    # 최대 1시간 제한
    max_additional = 3600  # 1시간
    additional = min(request.additional_seconds, max_additional)

    # 만료 시간 연장
    secret_msg.expires_at = secret_msg.expires_at + timedelta(seconds=additional)
    secret_msg.expiry_seconds = secret_msg.expiry_seconds + additional
    db.commit()

    remaining = (secret_msg.expires_at - now).total_seconds()

    return {
        "status": "extended",
        "secret_id": secret_id,
        "added_seconds": additional,
        "new_expires_at": secret_msg.expires_at,
        "remaining_seconds": int(remaining)
    }


@router.get("/status/{secret_id}")
def check_secret_status(
    secret_id: str,
    db: Session = Depends(get_db)
):
    """시크릿 메시지 상태 확인 (발신자용)"""
    secret_msg = db.query(SecretMessage).filter(
        SecretMessage.secret_id == secret_id
    ).first()

    if not secret_msg:
        raise HTTPException(status_code=404, detail="메시지를 찾을 수 없습니다")

    now = datetime.utcnow()
    is_expired = now > secret_msg.expires_at or secret_msg.is_expired
    remaining = max(0, (secret_msg.expires_at - now).total_seconds()) if not is_expired else 0

    return {
        "secret_id": secret_id,
        "is_viewed": secret_msg.is_viewed,
        "viewed_at": secret_msg.viewed_at,
        "is_expired": is_expired,
        "remaining_seconds": int(remaining),
        "created_at": secret_msg.created_at,
        "expires_at": secret_msg.expires_at,
        # 발신자가 자신의 메시지 내용 확인용
        "message": secret_msg.original_message,
        "message_type": secret_msg.message_type,
        "image_url": secret_msg.image_url
    }
