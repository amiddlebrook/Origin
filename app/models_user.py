from sqlalchemy import Column, Integer, String, DateTime, func, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    # Basic info
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    name_stories = relationship("NameStory", back_populates="user", cascade="all, delete-orphan")
    oral_histories = relationship("OralHistory", back_populates="user", cascade="all, delete-orphan")
    research = relationship("Research", back_populates="user", cascade="all, delete-orphan")
