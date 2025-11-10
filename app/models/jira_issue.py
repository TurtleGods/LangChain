from app.models.base import Base
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime,JSON
from sqlalchemy.dialects.postgresql import JSONB


class JiraIssue(Base):
    __tablename__ = "jira_issues"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True,nullable=False)
    summary = Column(String)
    description = Column(String)
    status = Column(String)
    assignee = Column(String)
    created = Column(DateTime)
    updated = Column(DateTime)
    comment = Column(JSONB)
    data = Column(JSON) 
    last_jira_updated = Column(DateTime, index=True)   # Jira 的 updated 時間
    last_sync = Column(DateTime, index=True)           # 系統寫入 DB 的時間
