from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON

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
    data = Column(JSON)  # PostgreSQL JSONB
