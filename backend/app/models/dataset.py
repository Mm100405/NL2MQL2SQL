from sqlalchemy import Column, String, Text, JSON, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.database import Base


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    datasource_id = Column(String(36), ForeignKey("datasources.id"), nullable=False)
    name = Column(String(255), nullable=False)
    physical_name = Column(String(255), nullable=False)  # Actual table/view name
    schema_name = Column(String(255), nullable=True)
    columns = Column(JSON, nullable=True)  # [{name, type, nullable, comment}]
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "datasource_id": self.datasource_id,
            "name": self.name,
            "physical_name": self.physical_name,
            "schema_name": self.schema_name,
            "columns": self.columns or [],
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
