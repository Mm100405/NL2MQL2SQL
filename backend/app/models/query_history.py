from sqlalchemy import Column, String, Text, JSON, DateTime, Integer
from datetime import datetime
import uuid

from app.database import Base


class QueryHistory(Base):
    __tablename__ = "query_history"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    natural_language = Column(Text, nullable=False)
    mql_query = Column(Text, nullable=True)
    sql_query = Column(Text, nullable=True)
    execution_time = Column(Integer, nullable=True)  # milliseconds
    result_count = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, default="success")  # success, failed, timeout
    error_message = Column(Text, nullable=True)
    chart_config = Column(JSON, nullable=True)  # {type, x_axis, y_axis, title}
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "natural_language": self.natural_language,
            "mql_query": self.mql_query,
            "sql_query": self.sql_query,
            "execution_time": self.execution_time,
            "result_count": self.result_count,
            "status": self.status,
            "error_message": self.error_message,
            "chart_config": self.chart_config,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
