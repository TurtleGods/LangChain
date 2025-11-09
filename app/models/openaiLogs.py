from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, Text, TIMESTAMP, func
from app.models.base import Base
class OpenaiLogs(Base):
    __tablename__ = "openai_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    user_id = Column(Text, nullable=True)          # 誰提出問題（可選）
    question = Column(Text, nullable=False)        # 前端傳入的問題
    answer = Column(Text, nullable=False)          # LLM 回覆內容
    intent = Column(Text, nullable=True)           # QueryIntent (detail, similarity...)
    issue_key = Column(Text, nullable=True)        # 從問題中解析出來的 Jira Key
    tokens_used = Column(Integer, nullable=True)   # 選填：統計 token 用量

    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now()                  # 自動填入時間
    )