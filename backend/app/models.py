from sqlalchemy import Column, Integer, String
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
