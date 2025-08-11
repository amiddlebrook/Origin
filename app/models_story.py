from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class NameStory(Base):
    __tablename__ = "name_stories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    research_id = Column(Integer, ForeignKey("research.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    narrative = Column(Text, nullable=True)
    sources = Column(JSON, nullable=True)
    illustration_url = Column(String(512), nullable=True)
    status = Column(String(50), default="draft", nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class OralHistory(Base):
    __tablename__ = "oral_histories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    story_id = Column(Integer, ForeignKey("name_stories.id"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    duration_seconds = Column(Integer, nullable=True)
    transcript = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
