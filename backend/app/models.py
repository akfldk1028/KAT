from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    password = Column(String)
    name = Column(String)
    status_msg = Column(String, nullable=True)
    profile_img_url = Column(String, nullable=True)
    background_img_url = Column(String, nullable=True)


class SecretMessage(Base):
    """시크릿 메시지 모델 - 열람기한, 본인인증, 캡처방지 지원"""
    __tablename__ = "secret_messages"

    id = Column(Integer, primary_key=True, index=True)
    secret_id = Column(String, unique=True, index=True)  # UUID로 생성

    # 메시지 정보
    room_id = Column(Integer, index=True)
    sender_id = Column(Integer, index=True)
    original_message = Column(Text)  # 원본 메시지
    message_type = Column(String, default="text")  # text, image
    image_url = Column(String, nullable=True)

    # 시크릿 옵션
    expiry_seconds = Column(Integer, default=60)  # 만료 시간 (초)
    require_auth = Column(Boolean, default=False)  # 본인인증 필요 여부
    prevent_capture = Column(Boolean, default=True)  # 캡처방지 여부

    # 상태
    is_viewed = Column(Boolean, default=False)  # 열람 여부
    viewed_at = Column(DateTime, nullable=True)  # 열람 시각
    is_expired = Column(Boolean, default=False)  # 만료 여부

    # 타임스탬프
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # 만료 시각 (created_at + expiry_seconds)
