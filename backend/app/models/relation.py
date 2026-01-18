from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from datetime import datetime
import uuid

from app.database import Base


class DataRelation(Base):
    __tablename__ = "data_relations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    left_dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    right_dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)
    join_type = Column(String(20), nullable=False, default="INNER")  # INNER, LEFT, RIGHT, FULL
    join_conditions = Column(JSON, nullable=False)  # [{left_column, right_column, operator}]
    relationship_type = Column(String(10), nullable=True)  # 1:1, 1:N, N:M
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "left_dataset_id": self.left_dataset_id,
            "right_dataset_id": self.right_dataset_id,
            "join_type": self.join_type,
            "join_conditions": self.join_conditions or [],
            "relationship_type": self.relationship_type,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
