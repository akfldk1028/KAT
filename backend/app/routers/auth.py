from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from .. import models, schemas
from ..database import get_db
from ..core.security import verify_password, get_password_hash, create_access_token

router = APIRouter()

@router.post("/signup", response_model=schemas.AuthResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.user_id == user.user_id).first()
    if db_user:
        raise HTTPException(
            status_code=400,
            detail="이미 사용중이거나 탈퇴한 아이디입니다."
        )

    hashed_password = get_password_hash(user.password)
    db_user = models.User(
        user_id=user.user_id,
        password=hashed_password,
        name=user.name,
        profile_img_url="", # Default empty
        background_img_url="" # Default empty
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return schemas.AuthResponse(msg="회원가입 되었습니다.")

@router.post("/login", response_model=schemas.AuthResponse)
def login(user: schemas.UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.user_id == user.user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="계정 또는 비밀번호를 다시 확인해주세요.")
    
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=404, detail="계정 또는 비밀번호를 다시 확인해주세요.")
    
    access_token = create_access_token(
        data={"id": db_user.id, "user_id": db_user.user_id}
    )
    
    return schemas.AuthResponse(
        data=schemas.TokenData(token=access_token),
        msg="로그인 성공!"
    )
