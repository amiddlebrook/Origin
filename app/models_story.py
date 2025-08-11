from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class NameStory(Base):
    __tablename__ = "name_stories"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    research_id = Column(Integer, ForeignKey("research.id"), nullable=True, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    narrative = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    illustration_url = Column(String(512), nullable=True)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, done, error
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="name_stories")
    research = relationship("Research", back_populates="stories")
    oral_histories = relationship("OralHistory", back_populates="story")

class OralHistory(Base):
    __tablename__ = "oral_histories"
    
    # Basic info
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("name_stories.id"), nullable=True, index=True)
    
    # Content
    title = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    
    # Processing status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, processed, error
    error_message = Column(Text, nullable=True)
    
    # Audio metadata
    duration_seconds = Column(Integer, nullable=True)
    file_metadata = Column(JSON, nullable=True)  # Store format, codec, sample rate, etc.
    
    # Processing results
    transcript = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="oral_histories")
    story = relationship("NameStory", back_populates="oral_histories")
