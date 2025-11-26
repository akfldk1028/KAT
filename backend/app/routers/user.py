from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db

router = APIRouter()

@router.get("/{user_id}")
def get_user_by_user_id(user_id: str, db: Session = Depends(get_db)):
    """
    Check if user_id exists (used during signup to validate uniqueness).
    Returns user data if exists, null if available.
    """
    user = db.query(models.User).filter(models.User.user_id == user_id).first()
    
    if user:
        return {
            "data": {
                "id": user.id,
                "user_id": user.user_id,
                "name": user.name,
                "status_msg": user.status_msg,
                "profile_img_url": user.profile_img_url or "",
                "background_img_url": user.background_img_url or ""
            },
            "msg": "이미 사용중이거나 탈퇴한 아이디입니다."
        }
    
    return {
        "data": None,
        "msg": "사용 가능한 ID 입니다."
    }

@router.get("/find/{id}")
def get_user_by_id(id: int, db: Session = Depends(get_db)):
    """
    Find user by internal ID (used to get participant info in chat rooms).
    """
    user = db.query(models.User).filter(models.User.id == id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    return {
        "data": {
            "id": user.id,
            "user_id": user.user_id,
            "name": user.name,
            "status_msg": user.status_msg,
            "profile_img_url": user.profile_img_url or "",
            "background_img_url": user.background_img_url or ""
        },
        "msg": "사용자를 찾았습니다."
    }
