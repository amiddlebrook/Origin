from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class Research(Base):
    __tablename__ = "research"
    
    # Basic info
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    name = Column(String(200), index=True, nullable=False)
    
    # Status and results
    status = Column(String(50), default="pending", nullable=False)  # pending, running, done, error
    result = Column(JSON, nullable=True)
    research_metadata = Column(JSON, nullable=False, server_default="{}")
    error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="research")
    stories = relationship("NameStory", back_populates="research", cascade="all, delete-orphan")
