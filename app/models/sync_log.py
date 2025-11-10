from app.models.base import Base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON


class SyncLog(Base):
    __tablename__ = "sync_log"
    
    id = Column(Integer, primary_key=True)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    status = Column(String)         # success / fail
    synced_count = Column(Integer)  # 本次同步 upsert 的 issue 數量
    error_message = Column(String, nullable=True)
    detail = Column(JSON)           # optional