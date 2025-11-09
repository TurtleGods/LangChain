from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime,JSON
from sqlalchemy.dialects.postgresql import JSONB
Base = declarative_base()

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
    data = Column(JSON)  # PostgreSQL JSONB
