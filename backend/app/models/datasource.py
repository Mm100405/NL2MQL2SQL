from sqlalchemy import Column, String, Text, JSON, DateTime, Enum
from datetime import datetime
from typing import Any, Dict
import uuid
import enum

from app.database import Base
from app.utils.encryption import decrypt_api_key, encrypt_api_key


class DataSourceType(str, enum.Enum):
    postgresql = "postgresql"
    mysql = "mysql"
    clickhouse = "clickhouse"
    highgo = "highgo"
    dameng = "dameng"


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

    @staticmethod
    def normalize_type(datasource_type: str) -> str:
        aliases = {
            "postgres": DataSourceType.postgresql.value,
            "pg": DataSourceType.postgresql.value,
            "dm": DataSourceType.dameng.value,
        }
        normalized = (datasource_type or "").strip().lower()
        return aliases.get(normalized, normalized)

    @property
    def normalized_type(self) -> str:
        return self.normalize_type(self.type)

    def get_connection_config(self, include_password: bool = False) -> Dict[str, Any]:
        config = dict(self.connection_config or {})
        password_encrypted = config.pop("password_encrypted", None)
        if include_password:
            password = config.get("password")
            if password_encrypted and not password:
                try:
                    password = decrypt_api_key(password_encrypted)
                except Exception:
                    password = None
            if password:
                config["password"] = password
        else:
            config.pop("password", None)
        return config

    def set_connection_config(self, connection_config: Dict[str, Any], preserve_existing_password: bool = False):
        config = dict(connection_config or {})
        existing_config = self.get_connection_config(include_password=True)
        password = config.pop("password", None)

        if preserve_existing_password and password in (None, "", "******"):
            password = existing_config.get("password")

        if password:
            config["password_encrypted"] = encrypt_api_key(password)
        elif preserve_existing_password and self.connection_config:
            existing_password_encrypted = self.connection_config.get("password_encrypted")
            if existing_password_encrypted:
                config["password_encrypted"] = existing_password_encrypted
            elif existing_config.get("password"):
                config["password_encrypted"] = encrypt_api_key(existing_config["password"])

        self.connection_config = config

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "type": self.normalized_type,
            "connection_config": self.get_connection_config(include_password=False),
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
