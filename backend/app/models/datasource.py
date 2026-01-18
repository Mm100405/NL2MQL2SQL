from sqlalchemy import Column, String, Text, JSON, DateTime, Enum
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from datetime import datetime
import uuid
import enum

from app.database import Base


class DataSourceType(str, enum.Enum):
    postgresql = "postgresql"
    mysql = "mysql"
    sqlite = "sqlite"
    clickhouse = "clickhouse"


class DataSourceStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    error = "error"


class DataSource(Base):
    __tablename__ = "datasources"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    type = Column(String(50), nullable=False)
    connection_config = Column(JSON, nullable=False)  # host, port, database, username, password_encrypted
    status = Column(String(20), default=DataSourceStatus.inactive.value)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "connection_config": {
                k: v for k, v in self.connection_config.items() 
                if k != "password"  # Don't expose password
            },
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
